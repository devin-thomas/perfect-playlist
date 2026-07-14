# Perfect Playlist agent instructions

Read `docs/README.md` and `docs/GIT-WORKFLOW.md` before changing the repository. Linear implementation sessions must also follow the applicable task execution prompt.

## Completion contract

- A change task is not Complete until its acceptance criteria are satisfied, every applicable check passes without unintended skips, and its task-owned changes are stored in a non-empty commit.
- Never include a path that was dirty before the task, an unrelated user change, a secret, a cache, an unintended fixture mutation, or unrelated generated output in the task commit.
- Stage explicit paths with `git add -- <paths>`. Never use `git add .`, `git add -A`, or broad staging in a dirty worktree.
- Inspect `git diff --cached --check`, `git diff --cached --name-status`, and the staged diff before committing.
- Use `<TASK_ID>: <issue title>` for Linear work. Use a concise conventional commit subject for repository maintenance without a task ID.
- A staging, validation, or commit failure means the task remains In Progress or Incomplete. Do not begin its successor.

## Git ownership

- Codex Desktop and other manual task agents create the local task commit automatically after the completion gate passes and before marking Linear Done. They do not push unless the user or publishing instructions authorize it.
- Agents running inside Ralph never stage, commit, or push. A Ralph `Ready to Commit` result includes an explicit task-owned path manifest. The host PowerShell runner validates that manifest, commits and verifies the exact staged tree, finalizes and independently re-reads Linear, and pushes before another iteration may start.
- Never amend, rewrite history, force-push, modify remotes, or discard unrelated work unless the user explicitly authorizes that exact operation.
