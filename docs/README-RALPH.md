# Perfect Playlist Ralph setup

This package implements a bounded Ralph Wiggum loop around Codex in Docker Sandboxes while preserving the project-specific Linear workflow in `.ralph/TASK-EXECUTION-PROMPT.md`.

## Final behavior

- `.ralph/scripts/RalphOnce.ps1` runs one fresh implementation session against the currently checked-out branch, starts the host transaction only after `Status: Ready to Commit`, and always stops after that transaction succeeds or fails.
- `.ralph/scripts/Ralph.ps1` defaults to five iterations on the permanent `implementation` branch.
- Bounded Ralph enters the host transaction only after `<RALPH_STATUS>READY_TO_COMMIT</RALPH_STATUS>` and starts another iteration only after commit, Linear finalization, and push all succeed.
- A legitimate Incomplete or Blocked result stops immediately.
- A malformed, nonzero, or timed-out attempt gets one retry only when the repository is unchanged. The retry keeps the selected model and raises reasoning to High.
- Medium attempts have a 20-minute timeout; High recovery attempts have a 40-minute timeout.
- M-27 is never run. When only M-27 remains, bounded Ralph exits successfully with Review Required.
- Codex never stages, commits, pushes, opens a PR, or merges. The host PowerShell runner owns staging, commits, and pushes.
- Successful commits use `<TASK_ID>: <issue title>` formatting.
- `Ready to Commit` is a transaction trigger, not a completion claim: the task remains In Progress until the host verifies the commit and the Linear-only finalizer marks it Done.
- Ralph permits pre-existing dirty files but stops if Codex touches one of those paths.
- Existing staged changes are not allowed.
- Logs and state are written under gitignored `.ralph/logs/` and `.ralph/state/`.

## Files

```text
AGENTS.md
.ralph/scripts/Ralph.ps1
.ralph/scripts/RalphOnce.ps1
.ralph/scripts/Setup-Ralph.ps1
README-RALPH.md
RALPH-SETUP-DECISIONS.md
docs/GIT-WORKFLOW.md
.ralph/.gitignore
.ralph/config.json
.ralph/Ralph.Core.ps1
.ralph/TASK-EXECUTION-PROMPT.md
```

## 1. Place the files

Copy the package contents into:

```text
C:\dev\personal\spotify-playlist-modify
```

Keep the real Spotify file at:

```text
resources/spotify-secrets.env
```

The prompt refers to it repository-relatively, so the Docker-mounted workspace and the Windows checkout resolve the same file.

The real file must be ignored by Git. The example may be committed:

```text
resources/spotify-secrets.env
spotify-secrets.env.example
```

Environment names must not contain Markdown escape backslashes. Use `SPOTIPY_CLIENT_ID`, not `SPOTIPY\_CLIENT\_ID`.

The private file contains the names shown in repository-root `spotify-secrets.env.example`. Perfect Playlist reads the Spotify values directly. Setting `PERFECT_PLAYLIST_RUN_INTEGRATION_TESTS=1` makes every full pytest run include the temporary public Spotify create/verify/unfollow test. `.ralph/scripts/Setup-Ralph.ps1` alone reads `LINEAR_API_KEY` to register Docker's domain-scoped proxy secret; task agents must never directly inspect the file.

## 2. Install Docker Sandboxes

In elevated PowerShell once:

```powershell
Enable-WindowsOptionalFeature -Online -FeatureName HypervisorPlatform -All
```

Restart if requested. Then:

```powershell
winget install -h Docker.sbx
sbx login
```

Choose the Balanced network policy.

Before a Ralph run that can reach credentialed Spotify QA, allow the known
service domains from the host so the first live attempt uses the intended
network path instead of probing a blocked policy first:

```powershell
sbx policy allow network mcp.linear.app
sbx policy allow network accounts.spotify.com
sbx policy allow network api.spotify.com
```

Ralph already bypasses Codex's inner command sandbox; Docker's outer network
policy remains authoritative. Keep unrelated domains blocked and add another
domain only when a task demonstrates that it is required.

## 3. Run setup

From the repository root in PowerShell 7:

```powershell
pwsh .\.ralph\scripts\Setup-Ralph.ps1
```

The setup command:

1. starts Docker's host-side OpenAI OAuth flow for your Codex subscription;
2. reads `LINEAR_API_KEY` from the gitignored Spotify secrets file without printing it;
3. registers it with Docker's currently documented `sbx secret set-custom -g` flow, domain-scoped to `mcp.linear.app`, using the placeholder environment variable `LINEAR_API_KEY`;
4. creates or reuses `perfect-playlist-ralph`;
5. verifies Codex, Python project dependencies, and read-only Linear MCP access.

The actual Linear key exists only in the gitignored private file and Docker's secret store; it is not committed. Ralph injects its bearer-token MCP configuration into each sandbox Codex invocation, while Codex Desktop continues using the user's global OAuth Linear connection. Docker exposes only a generated placeholder and substitutes the real value for requests to `mcp.linear.app`. Docker currently documents custom secrets as an experimental, global registration; the credential is host-held and domain-scoped, but it is not limited to only the named sandbox.

Docker's current custom-secret interface passes the value to the short-lived `sbx` process during registration, which means another process running as your Windows user could theoretically inspect it. Run setup only on your trusted PC and close unrelated processes first if you want the narrowest exposure window.

To repeat only the bootstrap check later:

```powershell
pwsh .\.ralph\scripts\Setup-Ralph.ps1 -SkipOpenAIOAuth -SkipLinearSecret -ForceBootstrap
```

## 4. Commit the runner

Review the files, then commit them before asking Ralph to modify the project:

```powershell
git add -- AGENTS.md .ralph/scripts/Ralph.ps1 .ralph/scripts/RalphOnce.ps1 .ralph/scripts/Setup-Ralph.ps1 README.md docs/GIT-WORKFLOW.md docs/README.md docs/README-RALPH.md docs/RALPH-SETUP-DECISIONS.md docs/TASK-EXECUTION-PROMPT.md docs/IMPLEMENTATION-PLAN.md .ralph/.gitignore .ralph/config.json .ralph/Ralph.Core.ps1 .ralph/TASK-EXECUTION-PROMPT.md tests/Ralph.Core.Smoke.ps1
git commit -m "chore: add bounded Ralph Codex runner"
git push
```

## 5. Human-in-the-loop run

```powershell
pwsh .\.ralph\scripts\RalphOnce.ps1
```

This uses Luna Medium by default, allows a dirty worktree, protects every path that was already dirty, and pushes to the current branch only after a successful task.

Completed but uncommitted work from an earlier session must be reconciled before its successor runs. Ralph treats every path dirty at startup as protected user work and will not roll that backlog into a later task's commit.

A single optional recovery attempt:

```powershell
pwsh .\.ralph\scripts\RalphOnce.ps1 -Retry
```

Override the model or effort for a particular task:

```powershell
pwsh .\.ralph\scripts\RalphOnce.ps1 -Model gpt-5.6-luna -ReasoningEffort high
```

## 6. Bounded loop

```powershell
pwsh .\.ralph\scripts\Ralph.ps1
```

That means five maximum successful iterations. Another maximum:

```powershell
pwsh .\.ralph\scripts\Ralph.ps1 -Iterations 3
```

Bounded Ralph uses `implementation`:

- If absent, it creates it from the currently checked-out clean branch.
- If present, it switches to it only with a clean worktree.
- Once already on `implementation`, pre-existing unstaged or untracked work is allowed and protected from overlap.
- It fetches before every iteration and stops if the remote moves unexpectedly.

## Model control

The default CLI values are:

```text
Model: gpt-5.6-luna
Reasoning effort: medium
```

Each entry point accepts `-Model` and `-ReasoningEffort`. Reasoning values are `minimal`, `low`, `medium`, `high`, and `xhigh` when the selected model supports them.

The automatic recovery attempt changes only reasoning effort to High; it keeps whichever model you selected.

If your installed Codex catalog uses a different CLI identifier for the UI label “5.6 Luna,” pass the exact identifier shown by your Codex installation with `-Model`. The setup bootstrap deliberately fails early when the configured identifier is unavailable. The runner keeps model selection explicit instead of modifying your global Codex configuration.

## Commit transaction

After the sandbox agent passes every required check, leaves Linear In Progress, and reports `Ready to Commit`, the host runner:

1. verifies branch, `HEAD`, origin, repository-local Git controls, the clean starting index, and every pre-existing dirty path;
2. requires the new dirty path set to match the agent's explicit JSON path manifest;
3. blocks active content filters, reads staged blobs directly to reject non-regular or non-UTF-8 content independent of Git diff attributes, and scans for sensitive paths, known secret values, and credential-shaped additions;
4. disables hooks and filesystem monitors, stages the exact manifest, runs `git diff --cached --check`, and records the staged tree;
5. creates `<TASK_ID>: <issue title>` automatically and verifies the commit's parent, subject, tree, path set, clean index, and remaining protected dirt;
6. records `COMMITTED_PENDING_LINEAR`, runs a narrow idempotent Linear-only finalizer that records the commit SHA and marks the task and eligible parent Done, and confirms the result with a separate read-only reconciliation pass; and
7. pushes from the host before bounded Ralph may start another task.

An `Incomplete`, `Blocked`, malformed, failed, or `Review Required` result never enters this transaction. A staging, commit, or post-commit verification error records `COMMIT_FAILED` while Linear remains In Progress. If reconciliation proves Linear is still In Progress, Ralph records `LINEAR_FINALIZE_FAILED`; if an authoritative read cannot be obtained or finds inconsistent state, it records `LINEAR_FINALIZE_UNKNOWN`. Both preserve the local commit and do not push. A permanent push error records `PUSH_FAILED`, preserves the verified local commit after Linear is verified Done, and stops for manual recovery.

## Safety behavior

Ralph refuses automatic commits when:

- the index was already staged;
- Codex created a commit or changed HEAD;
- Codex touched a path that was dirty before the iteration;
- the result says Ready to Commit but no safe Git changes exist;
- the reported path manifest differs from the actual new dirty path set;
- repository-local Git configuration, attributes, or hooks changed;
- any candidate path contains a non-regular entry or staged blob that is not strict UTF-8 text;
- a sensitive path reaches staging;
- an active Git content filter applies to a candidate path;
- the staged diff contains a known secret or credential-shaped addition;
- the staged path set differs from the computed iteration path set;
- `git diff --cached --check` fails;
- the created commit or post-commit worktree does not exactly match the validated candidate;
- another Ralph process holds the local lock.

Hard-blocked commit paths include:

```text
.env
.env.* (except committed examples)
resources/spotify-secrets.env
*token-cache*
*.pem
*.key
```

The real Spotify secret file is byte-snapshotted before each attempt. If Codex changes or deletes it, the runner restores the original bytes and stops.

If push fails after three attempts, Ralph leaves the verified local commit and completed Linear state intact, then stops for manual push recovery.

If Linear finalization fails or cannot be reconciled, inspect `.ralph/state/latest-run.json` and the referenced finalizer or verification log before taking another task. Do not push the local commit until an authoritative Linear read confirms that the task is Done, its exact `Ralph commit: <SHA>` comment exists, and its parent has the expected state. For `LINEAR_FINALIZE_FAILED`, repeat only the narrow idempotent finalization; for `LINEAR_FINALIZE_UNKNOWN`, establish the authoritative state first and then perform only the missing reconciliation step.

## Local runner validation

Run the non-mutating parser and guardrail smoke test after changing Ralph:

```powershell
pwsh -NoProfile -File .\tests\Ralph.Core.Smoke.ps1
```

## Logs and state

```text
.ralph/logs/<timestamp>-<attempt>.log
.ralph/state/latest-run.json
```

The runner redacts values found in `resources/spotify-secrets.env` and `.env` before writing captured output. Although the private file stores `LINEAR_API_KEY`, the key is registered host-side and remains proxy-managed; it is not available to the agent as plaintext.

## No pull requests

Ralph pushes branches only. It never opens, edits, merges, or closes a pull request. M-27 and final integration remain independent manual work.

## Troubleshooting

```powershell
sbx ls
sbx policy ls
sbx policy log
sbx diagnose
```

If Linear is blocked by the Balanced policy:

```powershell
sbx policy allow network mcp.linear.app
```

To rebuild the sandbox:

```powershell
sbx stop perfect-playlist-ralph
sbx rm perfect-playlist-ralph
pwsh .\.ralph\scripts\Setup-Ralph.ps1 -SkipOpenAIOAuth -SkipLinearSecret -ForceBootstrap
```

Do not delete the sandbox unless you are comfortable reinstalling its cached dependencies.

## Primary references

- Docker Sandboxes Codex guide: https://docs.docker.com/ai/sandboxes/agents/codex/
- Docker Sandboxes credentials: https://docs.docker.com/ai/sandboxes/security/credentials/
- Codex non-interactive CLI reference: https://developers.openai.com/codex/cli/reference/
- Codex MCP configuration: https://developers.openai.com/codex/mcp/
- Linear MCP documentation: https://linear.app/docs/mcp
