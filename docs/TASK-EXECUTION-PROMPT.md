## Prompt

```text
Complete exactly one next task from the Perfect Playlist implementation plan.

Repository: current repository root (expected local path: C:\dev\personal\spotify-playlist-modify)
Spotify secrets file: resources/spotify-secrets.env
Linear project: Perfect Playlist CLI
Linear access: use the configured OAuth server named `linear`; do not require or retrieve `LINEAR_API_KEY` in Codex Desktop.
Ordered parent issues: M-115, M-116, M-117
Independent final review: M-27

Do not ask me for a task ID. Determine the one next executable implementation child from Linear as described below, complete only that task, report it, and stop.

M-27 is never selectable in this implementation workflow. If every implementation child under M-115, M-116, and M-117 is Done and M-27 is the only remaining work, make no repository or Linear changes, report `Status: Review Required`, and stop.

Before changing anything:

1. Record your start time in the America/Chicago time zone.
2. Read the repository's applicable AGENTS.md instructions.
3. Read these files in order:
   - README.md
   - docs/README.md
   - docs/PRODUCT-AND-LANGUAGE.md
   - docs/CLI-CONTRACT.md
   - docs/IMPLEMENTATION-PLAN.md
   - docs/GIT-WORKFLOW.md
   - docs/LIVE-QA.md
4. Record the starting commit and `git status --short`. The worktree may contain intentional changes from earlier tasks. Treat every path already dirty as protected: preserve it, do not stage it, do not revert it, and do not overwrite it.
5. Use Linear to read M-115, M-116, M-117, M-27, and all children of the three parent issues, including each issue's status and blockers.
6. Retry a transient Linear read or write failure up to three total attempts with a short delay. If Linear remains unavailable, do not guess or claim completion.
7. If the OAuth Linear server requires authentication or cannot initialize, report that exact connection problem. Do not read the private secrets file or attempt API-key authentication from this manual Desktop workflow.

Select the task mechanically:

1. M-115, M-116, and M-117 are organizational parent containers, not implementation tasks. Never select a parent as the task to implement.
2. Child-title coordinates define plan order: [1.0] through [1.6], then [2.1] through [2.6], then [3.1] through [3.6].
3. If exactly one child is already In Progress, resume that child if its blockers are complete. If more than one child is In Progress, stop and report the inconsistent Linear state instead of guessing.
4. Otherwise, select the lowest-coordinate incomplete child whose blockers are all Done.
5. Never select M-27. When every implementation child is Done, report `Status: Review Required` as described above.
6. Because child issues are dependency-chained, there should be exactly one executable implementation child until implementation is finished. If there are zero or multiple executable children before implementation is finished, stop and report the Linear inconsistency or blocker; do not choose based on visual position, creation date, numeric issue ID, or list sorting.
7. Read the selected issue, its parent, blockers, description, and acceptance criteria in full. That selected issue is TASK_ID for the rest of this session.

You are responsible for completing only TASK_ID. Do not begin its siblings, successor, final review, or adjacent cleanup unless TASK_ID explicitly requires that work for its own acceptance criteria.

Authority order:

1. TASK_ID defines this session's scope and acceptance criteria.
2. docs/CLI-CONTRACT.md defines user-visible behavior.
3. docs/PRODUCT-AND-LANGUAGE.md defines product intent and canonical terminology.
4. docs/IMPLEMENTATION-PLAN.md defines sequencing and boundaries.
5. AGENTS.md and docs/GIT-WORKFLOW.md define commit ownership and completion.
6. docs/LIVE-QA.md provides historical evidence and safety constraints.
7. Existing code is the implementation baseline, not authority for superseded behavior.

Execution rules:

- Move TASK_ID to In Progress only when work actually begins.
- If TASK_ID is the first active child of a Todo parent, move that parent to In Progress for tracking only.
- Implement the smallest complete change that satisfies every acceptance criterion for TASK_ID.
- Reuse sound existing primitives, but remove or alter legacy behavior when the contract explicitly supersedes it.
- Do not add compatibility aliases, transitional commands, speculative features, unrelated refactors, or work assigned to later issues.
- Add or update focused tests for behavior changed by this task.
- Run task-specific tests first, then every applicable repository check.
- Keep offline tests and other local checks in the default sandbox. For a command known in advance to require external HTTPS - including a credentialed Spotify integration test, Spotify OAuth token exchange, dependency download, or an authorized Git/GitHub/Linear CLI or API operation - request network-enabled execution on the first attempt. In Codex Desktop, set `sandbox_permissions: "require_escalated"` on that first shell call, include a concise approval justification, and use a narrowly scoped reusable `prefix_rule` when appropriate. Do not run a predictably blocked restricted-network probe first. Invoke configured MCP or app tools directly; retry only after an unexpected failure and only when permissions or external state will materially differ.
- Use a fresh pytest temporary directory outside the repository for isolated or retried tests when the repository `.pytest-tmp` directory is locked or permission-denied. Do not delete or modify repository fixtures, caches, or secrets to work around the lock.
- Runtime and tests may load repository-relative `resources/spotify-secrets.env` through approved code paths. Never directly open, print, inspect, modify, commit, paste into Linear, or duplicate its contents. Use `spotify-secrets.env.example` only to understand variable names.
- `LINEAR_API_KEY` is reserved for the separate Ralph host/proxy path and is not used by this OAuth Desktop workflow. Never attempt to retrieve or expose it.
- Do not claim completion if an applicable check fails or an expected test is skipped.
- A manual/Desktop task is not Complete until its task-owned changes are committed. After every non-Git completion condition passes, stage only the exact paths changed for TASK_ID, run `git diff --cached --check`, inspect the staged name-status and diff, verify no secret, generated, unrelated, or pre-existing dirty path is included, and create a non-empty commit named `<TASK_ID>: <issue title>`. Do not use `git add .`, `git add -A`, amend, or broad cleanup commands. If staging, validation, or commit fails, leave TASK_ID In Progress, report `Status: Incomplete`, and do not mark its parent Done. Do not push unless the user or repository publishing instructions authorize it.

Completion gate:

Mark TASK_ID Done only when:

- every acceptance criterion is implemented;
- relevant tests pass;
- all applicable full checks pass;
- no unintended test is skipped;
- documentation directly affected by this task is accurate; and
- git status contains no accidental secret, cache, fixture, or unrelated generated file; and
- a verified non-empty task commit exists at HEAD with the required subject and exact task-owned path set.

If a test fails or is skipped, report that **BOLDLY AND CLEARLY**, explain the reason, try to resolve it, and leave TASK_ID incomplete if full verification is still missing.

Parent bookkeeping:

- After marking TASK_ID Done, check its parent.
- If every child of that parent is Done and the parent's acceptance criteria are satisfied, mark the parent Done.
- Otherwise leave the parent In Progress.
- This bookkeeping does not authorize implementation of another child.
- Never modify or mark M-27 Done.

At the end:

1. Record your end time in America/Chicago.
2. Calculate and report total whole minutes worked.
3. If every non-Git completion condition passes, stage, inspect, commit, and verify the exact task-owned diff as required above. Do this before marking TASK_ID Done. If any non-Git condition fails, do not create a completion commit.
4. Update TASK_ID in Linear with:
   - start time;
   - end time;
   - minutes worked;
   - concise implementation summary;
   - files materially changed;
   - exact tests/checks run and results;
   - commit SHA and subject when Complete;
   - any failures, skips, residual risks, or blockers.
5. Apply the completion gate and parent bookkeeping above. Never set TASK_ID or its parent to Done before the commit succeeds.
6. Report back using this structure:

Task: TASK_ID — <title>
Status: Complete | Incomplete | Blocked

For the no-task final boundary only, use:
Task: None — M-27 requires independent review
Status: Review Required
Start: <America/Chicago timestamp>
End: <America/Chicago timestamp>
Minutes worked: <whole number>
Commit: <SHA and subject, or "Not created - status is Incomplete/Blocked/Review Required">

Implemented:
- <concise outcomes>

Validation:
- <exact command>: <result>

Linear:
- <task state and issue URL, or "M-27 remains untouched" for Review Required>
- <parent state and issue URL, or "All implementation parents/children are Done" for Review Required>

Changed files:
- <paths>

Failures, skipped tests, or residual risks:
- None
  OR
- **FAILED/SKIPPED/BLOCKED:** <clear explanation>

Do not start another task after reporting.
```

## Selection invariant

No current child is hard-coded in this prompt. Resolve the next task from authoritative Linear state on every run. Keep completed issues Done, do not infer that a successor is In Progress from repository dirt, and stop with `Review Required` rather than starting M-27.
