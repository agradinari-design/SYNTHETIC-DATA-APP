#!/usr/bin/env python3
"""AI reviewer for Grid University Gen AI capstone submissions.

Reads the rubric matching the PR's base branch, dumps the student's source
files (excluding `.github/` and common cache/binary paths), asks Gemini for a
structured review, and writes:

  - `review_comment.md`           Markdown body to post as a PR comment.
  - `$GITHUB_OUTPUT` entries      `grade` and `summary` for downstream steps.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Literal

from google import genai
from google.genai import types
from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[2]
RUBRIC_DIR = REPO_ROOT / ".github" / "rubrics"
COMMENT_PATH = Path(os.environ.get("REVIEW_COMMENT_PATH", "review_comment.md"))

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-pro-preview")
MAX_FILE_BYTES = 60_000
MAX_TOTAL_BYTES = 800_000

EXCLUDED_DIRS = {
    ".git", ".github", "resources", "node_modules", "__pycache__",
    ".venv", "venv", ".pytest_cache", ".ipynb_checkpoints", ".mypy_cache",
    ".ruff_cache", "dist", "build", ".next", ".cache", ".terraform",
    ".idea", ".vscode",
}
EXCLUDED_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".pdf", ".zip", ".tar", ".gz",
    ".whl", ".so", ".dll", ".pyc", ".bin", ".mp4", ".mov", ".webm", ".wav",
    ".mp3", ".ico", ".woff", ".woff2", ".ttf", ".eot", ".jar", ".class",
    ".pyd", ".npz", ".npy", ".pkl", ".pt", ".onnx", ".safetensors",
}


class PhaseAnalysis(BaseModel):
    phase: str
    status: Literal["delivered", "delivered_with_gaps", "missing"]
    evidence: str
    gaps: list[str]
    suggestions: list[str]


class RequirementAnalysis(BaseModel):
    requirement: str
    status: Literal["present", "substituted", "missing"]
    evidence: str
    note: str


class ReviewResult(BaseModel):
    grade: Literal["failed", "passed_with_notes", "passed"]
    overall_assessment: str
    technical_requirements: list[RequirementAnalysis]
    phase_analysis: list[PhaseAnalysis]
    action_items_for_student: list[str]
    instructor_summary: str


def collect_code(root: Path) -> tuple[str, list[str]]:
    chunks: list[str] = []
    included: list[str] = []
    total = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue
        if path.suffix.lower() in EXCLUDED_SUFFIXES:
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size == 0:
            continue
        if size > MAX_FILE_BYTES:
            chunks.append(
                f"\n=== FILE: {rel} (skipped — {size} bytes exceeds {MAX_FILE_BYTES}) ===\n"
            )
            included.append(f"{rel} (oversize, skipped)")
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if total + len(text) > MAX_TOTAL_BYTES:
            chunks.append("\n=== TOTAL CODE CAP REACHED — remaining files omitted ===\n")
            break
        chunks.append(f"\n=== FILE: {rel} ===\n{text}\n")
        included.append(str(rel))
        total += len(text)
    return "".join(chunks), included


def build_prompt(branch: str, rubric: str, code: str, files: list[str]) -> str:
    file_list = "\n".join(f"- {f}" for f in files) if files else "(no files)"
    return f"""You are a senior AI mentor reviewing a student's capstone project for Grid University's Gen AI training program. The submission targets the **{branch}** module.

Your role is NOT a checkbox grader. Your role is to give the student deep, pedagogical feedback that helps them understand what they delivered, what gaps remain, and how to close those gaps. Address the student directly ("Your `app.py` does X...").

# Evaluation philosophy

Follow the module rubric below. It contains the original task specification (the source of truth for what the student had to deliver) and the grading guidance you must apply.

The core principle is:

- **Substitution = OK.** If the spec named tool X but the student used an equivalent tool Y that fills the same role and actually works, mark it as `substituted` and note what they used. Do not penalize.
- **Omission = NOT OK.** If a non-optional capability is absent and nothing fills the role, mark it `missing`. This is a real gap.
- Items labeled `(Optional)`, `(optional for interns)`, `[Optional]`, or similar NEVER lower the grade. Do not flag them.

# Evidence standard

A package in `requirements.txt`, a filename that mentions a library, or a README claim is NOT evidence of implementation. Real evidence is:

1. an `import` statement in non-test source code, AND
2. a call site that actually runs as part of the application or phase deliverable.

If you can only find a stub, a placeholder, a `# TODO`, or an unused import, treat the capability as **missing**, not present. Always cite file paths (and line numbers when you can identify them) for both present and missing items. "No `from langchain` import anywhere in `app/`" is a real, useful absence note. "Looks like LangChain might be missing" is not.

# Verdict rules

- `failed` — the course's primary framework is absent (e.g., ADK for agentic, LangChain for rag, Vertex AI / Google GenAI SDK for prompt engineering), OR any mandatory Phase is entirely missing, OR two or more explicit singleton requirements are missing without substitution, OR the folder is empty.
- `passed_with_notes` — at least one substitution OR one isolated missing non-Phase singleton; everything else is delivered end-to-end.
- `passed` — every mandatory item is verified present. This is rare; when in doubt, downgrade to `passed_with_notes`.

# Feedback style

- Address the student directly. Be specific. Cite files (and line numbers if visible from the dump).
- Lead with what works in each phase. Then describe the gap. Then give a concrete next step.
- Avoid vague praise ("nice work", "looks good") and vague critique ("could be improved"). Every bullet must be actionable.
- Be terse. The student will use this list to fix the work — not to read prose.

---

# Module rubric

{rubric}

---

# Submission

Files included in this analysis ({len(files)} total):
{file_list}

Source code follows. Each file is delimited by a `=== FILE: <path> ===` marker.

{code}

---

Now produce the review as JSON conforming to the response schema.
"""


def format_comment(result: ReviewResult, branch: str) -> str:
    icon = {"passed": "✅", "passed_with_notes": "🟡", "failed": "❌"}[result.grade]
    label = result.grade.replace("_", " ").upper()
    lines = [
        f"# {icon} AI Review — `{branch}` module",
        "",
        f"**Verdict:** **{label}**",
        "",
        f"> {result.overall_assessment}",
        "",
    ]
    if result.technical_requirements:
        lines += [
            "## Technical requirements",
            "",
            "| Requirement | Status | Evidence |",
            "|---|---|---|",
        ]
        for r in result.technical_requirements:
            mark = {"present": "✓", "substituted": "~", "missing": "✗"}[r.status]
            note = f" — {r.note}" if r.note else ""
            evidence = r.evidence.replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {r.requirement} | {mark} {r.status}{note} | {evidence} |")
        lines.append("")
    if result.phase_analysis:
        lines += ["## Phase-by-phase analysis", ""]
        for p in result.phase_analysis:
            mark = {"delivered": "✓", "delivered_with_gaps": "~", "missing": "✗"}[p.status]
            lines += [
                f"### {mark} {p.phase}",
                "",
                f"**Status:** `{p.status}`",
                "",
                f"**What I found:** {p.evidence}",
                "",
            ]
            if p.gaps:
                lines += ["**Gaps:**", ""]
                lines += [f"- {g}" for g in p.gaps]
                lines.append("")
            if p.suggestions:
                lines += ["**Suggestions:**", ""]
                lines += [f"- {s}" for s in p.suggestions]
                lines.append("")
    if result.action_items_for_student:
        lines += ["## Action items", ""]
        lines += [f"- [ ] {a}" for a in result.action_items_for_student]
        lines.append("")
    lines += [
        "---",
        "",
        f"_Reviewed by `{MODEL}`. Push more commits to trigger another review._",
    ]
    return "\n".join(lines)


def emit_output(key: str, value: str) -> None:
    out = os.environ.get("GITHUB_OUTPUT")
    if not out:
        print(f"[output] {key}={value!r}")
        return
    delim = "EOF_AI_REVIEW"
    with open(out, "a", encoding="utf-8") as f:
        f.write(f"{key}<<{delim}\n{value}\n{delim}\n")


def fallback_empty_submission(branch: str) -> ReviewResult:
    return ReviewResult(
        grade="failed",
        overall_assessment=(
            "No reviewable source files were found in this submission. "
            "The orphan branch was merged but no code was added on top."
        ),
        technical_requirements=[],
        phase_analysis=[],
        action_items_for_student=[
            "Add your project's source files on top of this branch and push again.",
            f"Make sure your PR targets the `{branch}` branch.",
        ],
        instructor_summary="Empty submission — no reviewable source files.",
    )


def main() -> int:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY env var is not set.", file=sys.stderr)
        return 2

    branch = os.environ.get("TARGET_BRANCH") or os.environ.get("GITHUB_BASE_REF")
    if not branch:
        print("ERROR: TARGET_BRANCH / GITHUB_BASE_REF not set.", file=sys.stderr)
        return 2

    rubric_path = RUBRIC_DIR / f"{branch}.md"
    if not rubric_path.exists():
        print(f"ERROR: no rubric for branch '{branch}' at {rubric_path}", file=sys.stderr)
        return 2
    rubric = rubric_path.read_text(encoding="utf-8")

    code, files = collect_code(REPO_ROOT)
    print(f"Collected {len(files)} files, {len(code)} bytes total.")

    if not files:
        result = fallback_empty_submission(branch)
    else:
        client = genai.Client(api_key=api_key)
        prompt = build_prompt(branch, rubric, code, files)
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ReviewResult,
            temperature=0.2,
        )
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=config,
            )
        except Exception as e:
            print(f"ERROR: Gemini API call failed: {e}", file=sys.stderr)
            return 3
        try:
            result = ReviewResult.model_validate_json(response.text)
        except Exception as e:
            print(f"ERROR: response was not valid JSON: {e}", file=sys.stderr)
            preview = (response.text or "")[:2000]
            print(f"Raw response (first 2000 chars):\n{preview}", file=sys.stderr)
            return 4

    COMMENT_PATH.write_text(format_comment(result, branch), encoding="utf-8")
    print(f"Wrote review to {COMMENT_PATH}")

    emit_output("grade", result.grade)
    emit_output("summary", result.instructor_summary)

    print(f"\nGrade: {result.grade}")
    print(f"Summary: {result.instructor_summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
