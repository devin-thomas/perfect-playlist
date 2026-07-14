# Repeatable Automatic Next-Task Prompt

This is the canonical prompt for both `RalphOnce.ps1` and bounded `Ralph.ps1` runs. The bounded runner appends only its machine-readable status-marker requirement.

## Prompt

```text
Implement and fully verify exactly one next task from the Perfect Playlist implementation plan, then prepare it for the host-owned commit transaction.

Repository: current repository root (expected local path: C:\dev\personal\spotify-playlist-modify)
Spotify secrets file: resources/spotify-secrets.env
Linear project: Perfect Playlist CLI
Ordered parent issues: M-115, M-116, M-117
Independent final review: M-27

Do not ask me for a task ID. Determine the one next executable implementation child from Linear as described below, complete only that task, report it, and stop.

M-27 is never selectable in this workflow. Ralph is not authorized to perform, modify, or complete the independent final review. If every implementation child under M-115, M-116, and M-117 is Done and M-27 is the only remaining work, make no repository or Linear changes, report `Status: Review Required`, and stop.

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
4. Inspect git status. The worktree may contain intentional changes from earlier tasks. Preserve them, do not revert them, and do not overwrite unrelated work.
5. Use Linear to read M-115, M-116, M-117, M-27, and all children of the three parent issues, including each issue's status and blockers.
6. Retry a transient Linear read or write failure up to three total attempts with a short delay. If Linear remains unavailable, do not guess or claim completion.

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
- Keep offline tests and other local checks in the normal Ralph sandbox. Treat commands known in advance to require live HTTPS - including credentialed Spotify tests and Spotify OAuth token exchange - as network-dependent before invocation and use the sandbox's configured network path on the first attempt; do not run a predictably blocked policy probe first. Use the configured Linear MCP server directly, and leave GitHub pushes to the host-side runner as required below. If Docker policy denies a required domain, report that domain for host allowlisting instead of repeating the unchanged command.
- Use a fresh pytest temporary directory outside the repository for isolated or retried tests when the repository `.pytest-tmp` directory is locked or permission-denied. Do not delete or modify repository fixtures, caches, or secrets to work around the lock.
- Runtime and tests may load repository-relative `resources/spotify-secrets.env` through approved code paths. Never directly open, print, inspect, modify, commit, paste into Linear, or duplicate its contents. Use `spotify-secrets.env.example` only to understand variable names.
- `LINEAR_API_KEY` is host/proxy-only. The agent receives a placeholder and must never attempt to retrieve or expose the real key.
- Do not claim completion if an applicable check fails or an expected test is skipped.
- Do not create a Git commit, push a branch, open a pull request, rewrite history, modify remotes, or stage files. The host-side Ralph runner exclusively owns Git. In Ralph, `Status: Ready to Commit` asks the host to validate the reported task-owned path manifest, stage the exact diff, create `<TASK_ID>: <issue title>`, verify the commit, finalize Linear, and push. Emit Ready to Commit only after the readiness gate passes and a non-empty task-owned diff exists. The next task must not start unless that host transaction succeeds.

Ready-to-commit gate:

Report TASK_ID Ready to Commit only when:

- every acceptance criterion is implemented;
- relevant tests pass;
- all applicable full checks pass;
- no unintended test is skipped;
- documentation directly affected by this task is accurate; and
- git status contains no accidental secret, cache, fixture, or unrelated generated file; and
- the task produced a non-empty committable diff for the host runner.

If a test fails or is skipped, report that **BOLDLY AND CLEARLY**, explain the reason, try to resolve it, and leave TASK_ID In Progress if full verification is still missing.

Linear finalization boundary:

- During this implementation pass, add the required timing, implementation, file, and validation details to TASK_ID but leave TASK_ID In Progress.
- Do not mark TASK_ID or its parent Done. After the host creates and verifies the commit, a separate Linear-only finalizer records the commit SHA, marks TASK_ID Done, and marks the parent Done only when every child and the parent's acceptance criteria are complete.
- This boundary does not authorize implementation of another child.
- Never modify or mark M-27 Done.

At the end:

1. Record your end time in America/Chicago.
2. Calculate and report total whole minutes worked.
3. Update TASK_ID in Linear while leaving it In Progress with:
   - start time;
   - end time;
   - minutes worked;
   - concise implementation summary;
   - files materially changed;
   - exact tests/checks run and results;
   - any failures, skips, residual risks, or blockers.
4. Apply the readiness gate and Linear finalization boundary above.
5. Report back using this structure:

Task: TASK_ID — <title>
Status: Ready to Commit | Incomplete | Blocked

For the no-task final boundary only, use:
Task: None — M-27 requires independent review
Status: Review Required
Start: <America/Chicago timestamp>
End: <America/Chicago timestamp>
Minutes worked: <whole number>
Commit: Pending host commit for Ready to Commit; otherwise Not created

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

After the human-readable report, output exactly one additional line in this form:
<RALPH_CHANGED_PATHS>["repository/relative/path", "another/path"]</RALPH_CHANGED_PATHS>

For Ready to Commit, the JSON array must contain every path intentionally changed for TASK_ID and no path that was already dirty before this task. Use forward slashes, no absolute paths, and no `..` segments. For Incomplete, Blocked, or Review Required, output an empty JSON array. Do not output more than one RALPH_CHANGED_PATHS marker.

Do not start another task after reporting.
```

## Selection invariant

No current child is hard-coded in this prompt. Resolve the next task from authoritative Linear state on every run. Keep completed issues Done, do not infer that a successor is In Progress from repository dirt, and stop with `Review Required` rather than starting M-27.
