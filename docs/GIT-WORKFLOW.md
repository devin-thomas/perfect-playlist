# Git completion workflow

Every successfully completed change task must produce one intentional, task-scoped commit. A passing test run without a commit is verified work in progress, not a completed task.

## Completion boundary

Commit only after all of these conditions are true:

1. Every acceptance criterion for the task is implemented.
2. Focused tests and every applicable repository check pass.
3. No required test is skipped.
4. Affected documentation is accurate.
5. The candidate diff contains no secret, cache, unintended fixture mutation, unrelated generated artifact, or unrelated change.
6. Every path that was already dirty at task start remains unchanged and unstaged.

If any condition fails, do not commit, do not mark the task Done, and do not start its successor.

## Manual and Codex Desktop tasks

The task agent owns the local commit:

1. Record the starting commit and `git status --short` before editing.
2. Complete the work and run the full completion gate.
3. Identify only the paths created or changed for the current task. A pre-existing dirty path is out of scope unless the user explicitly assigns it to the task.
4. Stage those exact paths with `git add -- <paths>`. Do not use `git add .` or `git add -A`.
5. Run `git diff --cached --check`, inspect `git diff --cached --name-status`, and review `git diff --cached`.
6. Create a non-empty commit. Linear tasks use `<TASK_ID>: <issue title>`; maintenance work without a task ID uses a concise conventional commit subject.
7. Verify the new `HEAD`, commit subject, staged state, and remaining worktree status.
8. Only then mark the Linear task and an eligible parent Done and report `Status: Complete`.

If staging or commit fails, fix the cause and rerun the checks. If it cannot be resolved, leave the task In Progress, report `Status: Incomplete`, and identify whether any task-owned paths remain staged. Do not use a broad reset to clean up a failure.

Manual task commits remain local unless the user or the repository publishing instructions also authorize a push.

## Ralph tasks

The sandbox agent never manipulates Git and never marks the task or parent Done. After it passes the readiness gate, it leaves Linear In Progress and reports `Ready to Commit` with an explicit JSON path manifest. The host runner then owns this sequence:

1. Confirm the branch, `HEAD`, origin, repository-local Git controls, and initially clean index are unchanged.
2. Confirm every pre-existing dirty path is byte-for-byte unchanged.
3. Compute the new dirty path set and require it to match the agent's manifest exactly. Any concurrent unreported path stops the run.
4. Reject an empty diff, non-regular entries, any staged blob that is not strict UTF-8 text, a sensitive filename, an active content filter, known secret values, or credential-shaped added content. Staged blobs are inspected directly, independent of Git diff attributes.
5. Disable repository hooks and filesystem monitors for every host Git command, then stage the exact manifest.
6. Require the staged path set to match exactly, run `git diff --cached --check`, reject remaining unstaged task changes, and record the staged tree object.
7. Create `<TASK_ID>: <issue title>` with signing disabled for the automated transaction.
8. Verify that `HEAD` advanced by one commit, its parent and subject match, its tree equals the staged tree, the index is clean, and only protected pre-existing dirt remains.
9. Record `COMMITTED_PENDING_LINEAR`, run a narrow idempotent Linear-only finalizer that records the commit SHA and marks the task and eligible parent Done, then use a fresh read-only pass to reconcile the task, exact commit comment, and parent state.
10. Push from the host. Bounded Ralph starts the next iteration only after the push succeeds.

`Incomplete`, `Blocked`, malformed, failed, and `Review Required` results never create a commit. A commit-transaction failure records `COMMIT_FAILED`; Linear remains In Progress. If reconciliation proves Linear is still In Progress, Ralph records `LINEAR_FINALIZE_FAILED`; if it cannot establish the authoritative state, it records `LINEAR_FINALIZE_UNKNOWN`. Both preserve the verified local commit and do not push. A permanent push failure records `PUSH_FAILED`, preserves the verified local commit after Linear is verified Done, and stops for manual recovery. No failure starts another task.

## Existing completed but uncommitted work

Ralph deliberately treats every path dirty at startup as protected user work. It will never sweep completed work from an earlier session into a later task commit. Reconcile and commit an existing completed batch intentionally before starting its successor.

## Sensitive and destructive operations

Never commit credential files, OAuth material, token caches, `.env` files other than examples, PEM files, or key files. Never amend, force-push, rewrite history, change remotes, or discard unrelated work as part of automatic completion.
