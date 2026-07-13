# Perfect Playlist Ralph setup

This package implements a bounded Ralph Wiggum loop around Codex in Docker Sandboxes while preserving the project-specific Linear workflow in `.ralph/TASK-EXECUTION-PROMPT.md`.

## Final behavior

- `RalphOnce.ps1` runs one fresh Codex session against the currently checked-out branch, commits and pushes only after `Status: Complete`, and always stops.
- `Ralph.ps1` defaults to five iterations on the permanent `implementation` branch.
- Bounded Ralph starts another iteration only after `<RALPH_STATUS>COMPLETE</RALPH_STATUS>`.
- A legitimate Incomplete or Blocked result stops immediately.
- A malformed, nonzero, or timed-out attempt gets one retry only when the repository is unchanged. The retry keeps the selected model and raises reasoning to High.
- Medium attempts have a 20-minute timeout; High recovery attempts have a 40-minute timeout.
- M-27 is never run. When only M-27 remains, bounded Ralph exits successfully with Review Required.
- Codex never stages, commits, pushes, opens a PR, or merges. The host PowerShell runner owns staging, commits, and pushes.
- Successful commits use `M-118: <issue title>` formatting.
- Ralph permits pre-existing dirty files but stops if Codex touches one of those paths.
- Existing staged changes are not allowed.
- Logs and state are written under gitignored `.ralph/logs/` and `.ralph/state/`.

## Files

```text
Ralph.ps1
RalphOnce.ps1
Setup-Ralph.ps1
README-RALPH.md
RALPH-SETUP-DECISIONS.md
.codex/config.toml
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
resources/spotify-secrets.env.example
```

Environment names must not contain Markdown escape backslashes. Use `SPOTIPY_CLIENT_ID`, not `SPOTIPY\_CLIENT\_ID`.

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

## 3. Run setup

From the repository root in PowerShell 7:

```powershell
pwsh .\Setup-Ralph.ps1
```

The setup command:

1. starts Docker's host-side OpenAI OAuth flow for your Codex subscription;
2. prompts securely for the scoped Linear API key;
3. registers it with Docker's currently documented `sbx secret set-custom -g` flow, domain-scoped to `mcp.linear.app`, using the placeholder environment variable `LINEAR_API_KEY`;
4. creates or reuses `perfect-playlist-ralph`;
5. verifies Codex, Python project dependencies, and read-only Linear MCP access.

The actual Linear key is not written into the repository. Docker exposes only a generated placeholder and substitutes the real value for requests to `mcp.linear.app`. Docker currently documents custom secrets as an experimental, global registration; the credential is still host-held and domain-scoped, but it is not limited to only the named sandbox.

`Setup-Ralph.ps1` reads the key through a secure prompt, so it is not pasted into your PowerShell command history. Docker’s current custom-secret interface still passes the value to the short-lived `sbx` process, which means another process running as your Windows user could theoretically inspect it during registration. Run setup only on your trusted PC and close unrelated processes first if you want the narrowest exposure window.

To repeat only the bootstrap check later:

```powershell
pwsh .\Setup-Ralph.ps1 -SkipOpenAIOAuth -SkipLinearSecret -ForceBootstrap
```

## 4. Commit the runner

Review the files, then commit them before asking Ralph to modify the project:

```powershell
git add Ralph.ps1 RalphOnce.ps1 Setup-Ralph.ps1 README-RALPH.md RALPH-SETUP-DECISIONS.md .codex .ralph
git commit -m "chore: add bounded Ralph Codex runner"
git push
```

## 5. Human-in-the-loop run

```powershell
pwsh .\RalphOnce.ps1
```

This uses Luna Medium by default, allows a dirty worktree, protects every path that was already dirty, and pushes to the current branch only after a successful task.

A single optional recovery attempt:

```powershell
pwsh .\RalphOnce.ps1 -Retry
```

Override the model or effort for a particular task:

```powershell
pwsh .\RalphOnce.ps1 -Model gpt-5.6-luna -ReasoningEffort high
```

## 6. Bounded loop

```powershell
pwsh .\Ralph.ps1
```

That means five maximum successful iterations. Another maximum:

```powershell
pwsh .\Ralph.ps1 -Iterations 3
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

## Safety behavior

Ralph refuses automatic commits when:

- the index was already staged;
- Codex created a commit or changed HEAD;
- Codex touched a path that was dirty before the iteration;
- the result says Complete but no safe Git changes exist;
- a sensitive path reaches staging;
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

## Logs and state

```text
.ralph/logs/<timestamp>-<attempt>.log
.ralph/state/latest-run.json
```

The runner redacts values found in `resources/spotify-secrets.env` and `.env` before writing captured output. The Linear key is proxy-managed and is not available to the agent as plaintext.

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
pwsh .\Setup-Ralph.ps1 -SkipOpenAIOAuth -SkipLinearSecret -ForceBootstrap
```

Do not delete the sandbox unless you are comfortable reinstalling its cached dependencies.

## Primary references

- Docker Sandboxes Codex guide: https://docs.docker.com/ai/sandboxes/agents/codex/
- Docker Sandboxes credentials: https://docs.docker.com/ai/sandboxes/security/credentials/
- Codex non-interactive CLI reference: https://developers.openai.com/codex/cli/reference/
- Codex MCP configuration: https://developers.openai.com/codex/mcp/
- Linear MCP documentation: https://linear.app/docs/mcp
