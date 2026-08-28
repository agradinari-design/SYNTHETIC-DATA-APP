# Repo notes for Claude

## Module branches are orphan + workflow files are duplicated across them

This repo has four orphan module branches — `prompt`, `basic-prompt`, `rag`, `agentic` — plus `main`. Each module branch has its **own copy** of `.github/workflows/` (because `pull_request_target` resolves the workflow definition from the PR's base branch, not from `main`).

**Any CI/CD change — anything under `.github/workflows/` — MUST be propagated to all five branches: `main`, `prompt`, `basic-prompt`, `rag`, `agentic`.** Changing only `main` looks correct locally but has no effect on PRs targeting module branches.

The repeating commit pattern in `git log` (`(synced from main)` suffix) is the established convention. Workflow files are intentionally kept identical across branches.

### Propagation recipe

After landing the change on `main`, for each module branch:

```bash
git checkout <module-branch>
git pull --ff-only origin <module-branch>
git checkout main -- .github/workflows/<changed-file>.yml
git commit -m "<original subject> (synced from main)"
git push origin <module-branch>
```

Do this for ALL four module branches before considering the change complete.

## Prompt Engineering vs Prompt Engineering Basic

`prompt` and `basic-prompt` are **separate modules with different assignments**, not variants of each other. Never collapse them — different cohorts, different specs, different reviewer expectations. When the user mentions "prompt" they may mean either; if ambiguous, ask.
