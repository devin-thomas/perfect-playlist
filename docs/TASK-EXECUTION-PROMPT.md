# Repeatable Automatic Next-Task Prompt

Paste this prompt unchanged for every implementation session. The agent selects the next executable child from Linear's dependency graph; you do not provide or look up an issue ID.

## Prompt

```text
Complete exactly one next task from the Perfect Playlist implementation plan.

Repository: C:\dev\personal\spotify-playlist-modify
Linear project: Perfect Playlist CLI
Ordered parent issues: M-115, M-116, M-117
Independent final review: M-27

Do not ask me for a task ID. Determine the one next executable task from Linear as described below, complete only that task, report it, and stop.

Before changing anything:

1. Record your start time in the America/Chicago time zone.
2. Read the repository's applicable AGENTS.md instructions.
3. Read these files in order:
   - README.md
   - docs/README.md
   - docs/PRODUCT-AND-LANGUAGE.md
   - docs/CLI-CONTRACT.md
   - docs/IMPLEMENTATION-PLAN.md
   - docs/LIVE-QA.md
4. Inspect git status. The worktree may contain intentional changes from earlier tasks. Preserve them, do not revert them, and do not overwrite unrelated work.
5. Use Linear to read M-115, M-116, M-117, M-27, and all children of the three parent issues, including each issue's status and blockers.

Select the task mechanically:

1. M-115, M-116, and M-117 are organizational parent containers, not implementation tasks. Never select a parent as the task to implement.
2. Child-title coordinates define plan order: [1.1] through [1.6], then [2.1] through [2.6], then [3.1] through [3.6].
3. If exactly one child is already In Progress, resume that child if its blockers are complete. If more than one child is In Progress, stop and report the inconsistent Linear state instead of guessing.
4. Otherwise, select the lowest-coordinate incomplete child whose blockers are all Done.
5. M-27 becomes selectable only after M-117 is Done and every child under all three parents is Done.
6. Because child issues are dependency-chained, there should be exactly one executable issue. If there are zero or multiple executable issues, stop and report the Linear inconsistency or blocker; do not choose based on visual position, creation date, numeric issue ID, or list sorting.
7. Read the selected issue, its parent, blockers, description, and acceptance criteria in full. That selected issue is TASK_ID for the rest of this session.

You are responsible for completing only TASK_ID. Do not begin its siblings, successor, final review, or adjacent cleanup unless TASK_ID explicitly requires that work for its own acceptance criteria.

Authority order:

1. TASK_ID defines this session's scope and acceptance criteria.
2. docs/CLI-CONTRACT.md defines user-visible behavior.
3. docs/PRODUCT-AND-LANGUAGE.md defines product intent and canonical terminology.
4. docs/IMPLEMENTATION-PLAN.md defines sequencing and boundaries.
5. docs/LIVE-QA.md provides historical evidence and safety constraints.
6. Existing code is the implementation baseline, not authority for superseded behavior.

Execution rules:

- Move TASK_ID to In Progress only when work actually begins.
- If TASK_ID is the first active child of a Todo parent, move that parent to In Progress for tracking only.
- Implement the smallest complete change that satisfies every acceptance criterion for TASK_ID.
- Reuse sound existing primitives, but remove or alter legacy behavior when the contract explicitly supersedes it.
- Do not add compatibility aliases, transitional commands, speculative features, unrelated refactors, or work assigned to later issues.
- Add or update focused tests for behavior changed by this task.
- Run task-specific tests first, then every applicable repository check.
- For local Spotify credentials, use C:\dev\personal\spotify-playlist-modify\resources\secrets.md to populate the gitignored repository-root .env. Never display, log, commit, paste into Linear, or otherwise expose secret values, OAuth codes, access tokens, refresh tokens, token caches, or .env contents.
- Do not claim completion if an applicable check fails or an expected test is skipped.

Completion gate:

Mark TASK_ID Done only when:

- every acceptance criterion is implemented;
- relevant tests pass;
- all applicable full checks pass;
- no unintended test is skipped;
- documentation directly affected by this task is accurate; and
- git status contains no accidental secret, cache, fixture, or unrelated generated file.

If a test fails or is skipped, report that **BOLDLY AND CLEARLY**, explain the reason, try to resolve it, and leave TASK_ID incomplete if full verification is still missing.

Parent bookkeeping:

- After marking TASK_ID Done, check its parent.
- If every child of that parent is Done and the parent's acceptance criteria are satisfied, mark the parent Done.
- Otherwise leave the parent In Progress.
- This bookkeeping does not authorize implementation of another child.
- Never mark M-27 Done unless its own independent final-review acceptance criteria are complete.

At the end:

1. Record your end time in America/Chicago.
2. Calculate and report total whole minutes worked.
3. Update TASK_ID in Linear with:
   - start time;
   - end time;
   - minutes worked;
   - concise implementation summary;
   - files materially changed;
   - exact tests/checks run and results;
   - any failures, skips, residual risks, or blockers.
4. Apply the completion gate and parent bookkeeping above.
5. Report back using this structure:

Task: TASK_ID — <title>
Status: Complete | Incomplete | Blocked
Start: <America/Chicago timestamp>
End: <America/Chicago timestamp>
Minutes worked: <whole number>

Implemented:
- <concise outcomes>

Validation:
- <exact command>: <result>

Linear:
- <task state and issue URL>
- <parent state and issue URL>

Changed files:
- <paths>

Failures, skipped tests, or residual risks:
- None
  OR
- **FAILED/SKIPPED/BLOCKED:** <clear explanation>

Do not start another task after reporting.
```

## Current First Selection

With the initial Linear state, the algorithm selects `[1.1] M-118`. After it is completed, the dependency chain makes `[1.2] M-119` the only next executable child. The same unchanged prompt continues through `[3.6]` and then the independent final review.
