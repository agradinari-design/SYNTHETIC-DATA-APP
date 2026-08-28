# Professor setup guide

This guide walks you through everything needed to operate the AI review pipeline. Order matters — the workflow is inert until step 1 is complete.

---

## 0. Operating principle — branches never merge

The module branches (`prompt`, `rag`, `agentic`) are **evaluation targets only**. Pull Requests opened against them must **never be merged**. Treat each PR as a per-student review thread:

1. Student opens the PR. Two AI reviewers run in parallel and post sticky comments.
2. Student iterates by pushing more commits. The bots re-run and update their comments in place.
3. Once both reviewers reach `passed` or `passed_with_notes`, you read the code + reviews on the PR thread.
4. **You close the PR without merging.** No code from any submission ever lands on a module branch.

This keeps each module branch a clean, empty target forever. It also means you can ignore the **Merge pull request** button entirely — step 4 in branch-protection setup (below) blocks it for safety.

---

## 1. Required secrets

Go to **Settings → Secrets and variables → Actions** in the repository and add the following.

| Secret | How to obtain |
|---|---|
| `ANTHROPIC_API_KEY` | <https://console.anthropic.com/settings/keys> → **Create Key**. If the org already provides an `ANTHROPIC_API_KEY` at the organization level, you do not need to add it here. |
| `GCP_SA_KEY` | JSON key of a service account in your GCP project with the `roles/aiplatform.user` role. Generate via `gcloud iam service-accounts keys create key.json --iam-account=<SA email>`, then upload with `gh secret set GCP_SA_KEY < key.json`. |
| `GCP_PROJECT_ID` | The GCP project ID that hosts the service account (used as the Vertex AI billing target). |

`GITHUB_TOKEN` is provided automatically by GitHub Actions — no setup needed.

> **Why Vertex AI, not the AI Studio API key.** Gemini preview models (e.g. `gemini-3.1-pro-preview`) are paid-only on AI Studio and not reachable from a free-tier `GEMINI_API_KEY`. Vertex AI bills against the GCP project instead, so preview models work as soon as the service account has `roles/aiplatform.user` on the project. To roll back to an AI Studio API key (only for non-preview models), swap the `Authenticate to Google Cloud` step + `use_vertex_ai: true` block in `.github/workflows/ai-review.yml` back to a single `gemini_api_key: ${{ secrets.GEMINI_API_KEY }}` input.

---

## 2. Confirm the workflow runs

Smoke-test the pipeline:

1. Clone the repo locally.
2. `git checkout prompt && git checkout -b smoke-test`.
3. Add a tiny placeholder file (anything will do), commit, push.
4. Open a PR `smoke-test → prompt`.
5. Watch **Actions → AI Review**. You should see two jobs running in parallel — `Review (Claude)` and `Review (Gemini)`. Each finishes by posting a sticky comment on the PR.
6. Verdicts will be `failed` because there is no real submission — that is expected.
7. **Close the PR without merging** and delete the throwaway branch.

If a job fails before reaching the model call, the most likely cause is a missing or typo'd API-key secret.

---

## 3. Course delivery — student instructions

Students should be added as **Triage** or **Write** collaborators on this repo so they can push branches directly (the workflow runs cleanly on internal-branch PRs). Avoid the fork-PR flow — it requires a `pull_request_target` setup that we deliberately did not enable.

Share the top-level [`README.md`](https://github.com/griddynamics/gridu-genai/blob/main/README.md) with them — it covers the submission flow and includes the no-merge warning at the top.

---

## 4. Branch protection (already applied)

All four real branches in this repo — `main`, `prompt`, `rag`, `agentic` — are protected so that **course participants cannot push directly and cannot merge their own PRs**. The settings are uniform:

- **Direct push restricted to `drMacq`** — every other Write-access collaborator must go through a PR.
- **Required approving reviews: 1** — a PR cannot be merged until someone (in practice: you, the admin) clicks **Approve**. Click-Comment / Click-Request-Changes does not count.
- **Dismiss stale approvals on new commits** — if a student pushes after you approved, your approval is auto-dismissed and they need a fresh approve. Stops "approve once, sneak in code later" attacks.
- **Block force pushes** — history is append-only.
- **Block branch deletions** — module branches stay alive as reference targets forever.
- **`enforce_admins: false`** — you (as repo admin) keep the bypass for rubric/spec edits.

On top of that, the three module branches (`prompt`, `rag`, `agentic`) require two status checks:

- `Review (Claude)` — green when the AI verdict is `passed` or `passed_with_notes`, red when it's `failed`. Provides verdict signal on the PR.
- `Merge blocked (no-merge policy)` — **always red.** Comes from `.github/workflows/merge-block.yml`, whose only job is to refuse the merge. Because this check can never go green, the **Merge pull request** button on every module-branch PR is permanently disabled regardless of approvals.

`.github/workflows/cleanup-branch.yml` automatically deletes the head branch on PR close so the branch list stays tidy.

### Updating the spec / workflows on a module branch

As admin (drMacq) you bypass the push restriction, so directly pushing rubric/spec/workflow updates to a module branch is fine:

```bash
git checkout rag
# edit README.md (the assignment spec) or any .github/ file
git commit -am "Tighten Phase 3 wording"
git push origin rag
```

The push is not subject to status checks (those only run on `pull_request`).

### Recreating the protection rule

If you ever need to rebuild the rules (e.g. after a branch deletion), run:

```bash
# main — no status checks, just require PR + approval + push restriction
gh api -X PUT "repos/griddynamics/gridu-genai/branches/main/protection" \
  -H "Accept: application/vnd.github+json" \
  --input - <<'JSON'
{
  "required_status_checks": null,
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false
  },
  "restrictions": {"users": ["drMacq"], "teams": [], "apps": []},
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": false
}
JSON

# module branches — same plus the two required checks
for br in prompt rag agentic; do
  gh api -X PUT "repos/griddynamics/gridu-genai/branches/$br/protection" \
    -H "Accept: application/vnd.github+json" \
    --input - <<'JSON'
{
  "required_status_checks": {
    "strict": false,
    "checks": [
      {"context": "Review (Claude)"},
      {"context": "Merge blocked (no-merge policy)"}
    ]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false
  },
  "restrictions": {"users": ["drMacq"], "teams": [], "apps": []},
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": false
}
JSON
done
```

---

## 5. (Future) Upgrade Gemini auth from JSON key to Workload Identity Federation

The Gemini job currently authenticates via a long-lived JSON key (`GCP_SA_KEY` secret). This is the simplest setup but the key never rotates. A better posture is **Workload Identity Federation** — GitHub Actions exchanges its short-lived OIDC token for a GCP access token, with no secret in the repo.

To upgrade:

1. Have a GCP-project admin create a WIF pool + provider that trusts this repository's OIDC issuer. Bind the existing `gridu-genai-reviewer@gd-gcp-techlead-experiments.iam.gserviceaccount.com` to the pool via `roles/iam.workloadIdentityUser`.
2. Replace the `Authenticate to Google Cloud` step in `.github/workflows/ai-review.yml`:
   ```yaml
   - uses: google-github-actions/auth@v2
     with:
       workload_identity_provider: projects/<PROJECT_NUMBER>/locations/global/workloadIdentityPools/<POOL>/providers/<PROVIDER>
       service_account: gridu-genai-reviewer@gd-gcp-techlead-experiments.iam.gserviceaccount.com
   ```
3. Delete the `GCP_SA_KEY` secret from the repo. Keep `GCP_PROJECT_ID`.

Until then, rotate the JSON key periodically with `gcloud iam service-accounts keys create / delete`.

---

## 6. Notifications (GitHub-native)

Every Claude run does two things in addition to posting the sticky review comment:

- **Applies a verdict label** to the PR — `ai-verdict/failed` (red), `ai-verdict/passed-with-notes` (yellow), or `ai-verdict/passed` (green). The label is created on first use and replaces any prior verdict label, so the PR list always shows the current state at a glance.
- **Assigns the configured professors** when the verdict is `passed` or `passed_with_notes`. The assignee list is set via the `PROFESSORS` env var in `.github/workflows/ai-review.yml` (comma-separated) and is base-branch-aware: PRs into `prompt` are assigned to `drMacq,nleushGd`; PRs into `rag` or `agentic` are assigned to `drMacq` only. Each assignee receives a standard GitHub notification — email (if their account settings allow it), web notification badge, and entries in the **Assigned to you** filter.

No external integration is involved, so no security review is required.

> **Tip — silence the noise.** GitHub does not re-notify on assignee re-application. The first time a PR enters `passed_with_notes`/`passed` the assignee receives one notification; subsequent re-runs that keep the same verdict do not re-notify.

When security review eventually clears an external messaging integration, the same step can additionally push to Slack / email / Jira / Linear — add a conditional `curl` or action call inside the existing **Apply verdict label, notify professor, gate the check** step, gated on `$VERDICT`.

---

## 7. Re-running a review

A review re-runs automatically on every `synchronize` event (i.e., every new push to the PR head branch). The bot updates its **existing** sticky comment in place rather than creating a new one — the header of the comment carries a `Last updated <UTC timestamp> · workflow run #N` line so each re-run is visible without spamming the PR.

If you want to force a re-review without a code change, push an empty commit:

```bash
git commit --allow-empty -m "Trigger AI re-review"
git push
```

---

## 8. Cost monitoring

> **Note (2026-08):** the reviewer was migrated from Claude Sonnet 5
> (`anthropics/claude-code-action`) to **GPT-5.6 Luna via opencode**,
> routed through the Bifrost gateway (`BIFROST_API_KEY`/`BIFROST_URL`
> secrets/vars) — Claude Sonnet 5 was retired from Bifrost and every recent
> run was failing instantly. See `.github/workflows/ai-review.yml`'s `env`
> block header comment for the full rationale. The rest of this section
> predates that migration; update it if/when cost-monitoring access for
> the new model is set up.

The reviewer analyses the full submission on every PR push. Per-review cost previously tracked via Anthropic Console usage; for the current GPT-5.6 Luna / Bifrost setup, check usage through whatever dashboard the Bifrost gateway exposes.

The model is set via the single `REVIEW_MODEL` env var in `.github/workflows/ai-review.yml` — change it there if a cheaper/faster model becomes preferable. Same prompt, same output format.

(Gemini was previously a parallel reviewer but is disabled until `roles/aiplatform.user` is granted on the service account — see the comment block in `ai-review.yml`. Re-enabling it is one revert + the IAM grant.)

---

## 9. Reusing this infrastructure for another course

The pipeline is course-agnostic by design. To stand up a copy for a different course:

1. **Fork or clone** this repo into a new repository for the course (e.g. `gridu-mlops`, `gridu-sre`).
2. **Replace the module branches.** Create one orphan branch per course module — the branch name becomes the URL path students PR into. For each branch:
   - The `README.md` is the **assignment specification** as it would be shared with students. The AI reviewer reads only this file to decide what is mandatory. There is no separate rubric and no hidden requirements list — the spec text is the source of truth.
   - Add a `resources/` directory if the course ships datasets / templates / starter files; the reviewer skips that path.
   - Keep `.github/workflows/` synchronised with `main`.
3. **Edit `.github/workflows/ai-review.yml`** on `main` (then propagate):
   - In the `on.pull_request.branches:` list — replace `[prompt, rag, agentic]` with your course's module branch names.
   - In `merge-block.yml` and `cleanup-branch.yml` — same edit.
   - In the `PROFESSORS` env var on the verdict step — set the comma-separated list of GitHub logins to auto-assign on `passed*`.
4. **Re-apply branch protection** for the new module branches using the JSON in section 4 (swap the branch names in the loop).
5. **Re-apply secrets** (`ANTHROPIC_API_KEY`, optionally `GCP_SA_KEY`+`GCP_PROJECT_ID` for Gemini).
6. **Update this README + this SETUP guide** to reference the new course context, then point students at the new repo's main README.

Nothing in the workflow, the verdict logic, the merge block, or the cleanup is hardcoded to any specific tech stack — Claude infers what's mandatory from the language in the branch's README each run.
