# Grid University — Gen AI Training Program

Welcome! This repository is the submission hub for the **Generative AI** training program at Grid University.

Each course module has its own dedicated branch. You submit your capstone project by opening a **Pull Request** from your personal working branch into the matching module branch. An AI reviewer (Claude) runs on every PR and posts a detailed sticky comment with verdict, per-phase analysis, and concrete action items.

> ⚠️ **Pull Requests are evaluation-only.** The module branches (`prompt`, `rag`, `agentic`, `basic-prompt`) exist solely as targets for review. **They are never merged.** Your professor reads your code and the AI review on the PR thread, then closes the PR. No code from a submission ever lands on a module branch.

---

## Course modules

| Module | Target branch | What you build |
|---|---|---|
| **Prompt Engineering** | [`prompt`](https://github.com/griddynamics/gridu-genai/tree/prompt) | A conversational app with synthetic data generation + natural-language SQL querying. |
| **Prompt Engineering Basic** | [`basic-prompt`](https://github.com/griddynamics/gridu-genai/tree/basic-prompt) | A standalone *Prompt Engineering & AI Applications [Basic]* capstone. |
| **Retrieval-Augmented Generation** | [`rag`](https://github.com/griddynamics/gridu-genai/tree/rag) | A multimodal RAG system over the IFC Annual Report 2024 PDF (text, tables, images). |
| **Agentic Systems** | [`agentic`](https://github.com/griddynamics/gridu-genai/tree/agentic) | An autonomous research agent built with ADK — plan, execute, critique, refine. |

> ⚠️ **`prompt` and `basic-prompt` are SEPARATE modules — not variants of each other.** They run as distinct courses, with their own cohorts, their own assignment specifications, and their own reviewer expectations. Submit to the module branch that matches the course you are enrolled in, and read **only that branch's `README.md`** for your spec. Confusing the two is the most common source of mis-targeted submissions on this repo.

Each module branch contains a `README.md` with the assignment spec and a `resources/` directory with course-provided materials. The branch is otherwise empty — your PR adds your full project on top of that blank slate, so the reviewer sees exactly what you built and nothing else.

---

## How to submit

1. **Fork** this repository (or create a working branch directly if you have push access).
2. Create a branch off the module you are working on. For example, for the RAG capstone:
   ```bash
   git checkout rag
   git checkout -b <user-ldap-id>/rag-submission
   ```
3. Implement your solution on that branch. Commit and push as often as you like.
4. When you are ready for review, open a **Pull Request** targeting the module branch (`prompt`, `basic-prompt`, `rag`, or `agentic`).
   - **PR title must follow the convention `First Last - Module Name`** (e.g. `Jan Kowalski - Prompt Engineering`, `Maria Wojcik - Prompt Engineering Basic`, `Anna Nowak - RAG`, `Piotr Wisniewski - Agentic Systems`). This is how your professor identifies whose submission they are reading.
5. The AI reviewer (Claude, `claude-opus-4-8`) runs automatically and posts a sticky comment with:
   - an overall verdict (`failed` / `passed_with_notes` / `passed`),
   - a technical-requirements table,
   - a per-phase analysis with concrete file references,
   - a list of action items so you know exactly what to fix.
6. If the verdict is `failed`, push more commits — the bot re-runs on every push and updates its comment in place. Each update is tagged with a `Last updated …` timestamp at the top of the comment.
7. Once you reach `passed` or `passed_with_notes`, your professor is automatically assigned to the PR and notified. They review the PR and close it (without merging — see the warning at the top).

---

## What the AI reviewer checks

The reviewer reads:

- the **assignment specification** — the `README.md` of the module branch you are PR-ing into (it is exactly what you were given, no hidden requirements);
- your **code** — every file you contributed, except `.github/` and `resources/`.

It then walks through every mandatory phase of the spec and verifies, against the actual code:

- Are all explicitly required technologies actually imported and wired into the running app? (Not just listed in `requirements.txt`.)
- Are all mandatory phases delivered end-to-end? Can the capability be traced from an entrypoint?
- For each gap: does the student substitute an equivalent tool (acceptable, noted) or is the role omitted entirely (failure)?

The reviewer cites file paths and line numbers when calling something out. It will not penalize you for items the spec labels `(Optional)` or `(optional for interns)`.

---

## Repository layout

```text
main                              ← this branch: workflow + docs
├── README.md
└── .github/
    ├── workflows/
    │   ├── ai-review.yml         ← Claude reviewer
    │   ├── merge-block.yml       ← always-fail check that disables Merge
    │   └── cleanup-branch.yml    ← deletes head branch on PR close
    └── SETUP.md                  ← professor setup notes

prompt                            ← orphan branch: Module 1 spec + resources
basic-prompt                      ← orphan branch: Module 1 (Basic) spec + resources
rag                               ← orphan branch: Module 2 spec + resources
agentic                           ← orphan branch: Module 3 spec
```

---

## For professors

See [`.github/SETUP.md`](https://github.com/griddynamics/gridu-genai/blob/main/.github/SETUP.md) for setup steps, the no-merge policy, branch protection, and notes on reusing this infrastructure for other courses.
