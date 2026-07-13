# Ralph setup decisions: all 59 questions and final answers

This document records the interview that defined the Perfect Playlist Ralph runner. Later answers supersede earlier provisional details where noted.

## Prompt and loop behavior

1. **Should every iteration run the existing prompt unchanged?**  
   **Answer: A.** The canonical task prompt is self-contained. Bounded mode appends only the machine-readable `RALPH_STATUS` requirement; RalphOnce uses the canonical prompt without that addition.

2. **After one task finishes, should the next iteration begin automatically?**  
   **Answer: B.** Bounded Ralph continues only after a complete result. RalphOnce always stops after one task session.

3. **Where should Codex edit the repository?**  
   **Answer: A.** Directly in the local working tree, not in clone mode.

4. **Should dirty-worktree behavior from the prompt be preserved?**  
   **Answer: A.** Pre-existing intentional changes are allowed and must be preserved.

5. **How much independence should Codex have with Linear?**  
   **Answer: D.** Follow the exact prompt safeguards: select mechanically, update only the authorized task and parent bookkeeping, and obey the completion gate.

6. **What should happen with Git after a successful task?**  
   **Answer: B.** Commit and push every successfully completed task.

7. **Should Ralph automatically stage pre-existing changes?**  
   **Answer: A with overlap detection.** Stage only changes created by this iteration. Protect all paths that were already dirty; stop if Codex touches one.

8. **What if implementation succeeds but a Linear update temporarily fails?**  
   **Answer: C.** Retry transient Linear operations a limited number of times, then stop incomplete if synchronization is still missing.

9. **What if Codex reports Complete but exits nonzero or produces malformed output?**  
   **Answer: C.** Retry the same iteration once only when repository state is unchanged, then stop if recovery fails.

10. **What should the default maximum iteration count be?**  
    **Answer: B.** Five.

## Branches, retries, and final review

11. **Where should each completed task be pushed?**  
    **Answer: D initially, later refined by 18 and 19.** RalphOnce pushes the current branch. Bounded Ralph ultimately uses the permanent `implementation` branch rather than task-named bounded branches.

12. **What if `git push` fails after the task, tests, commit, and Linear update succeed?**  
    **Answer: A.** Retry the push, then stop if it still fails.

13. **How many retries should temporary failures receive?**  
    **Answer: C.** One full Codex recovery attempt; three attempts for transient Linear writes and host Git pushes.

14. **Should each iteration receive a fresh Codex context?**  
    **Answer: A.** Yes. Every iteration re-reads the repository and Linear from scratch.

15. **Should M-27 run automatically?**  
    **Answer: C.** No. Ralph must not perform M-27.

16. **How should automatic model escalation work?**  
    **Answer: C, with Luna High only.** Escalate only malformed, nonzero, or timed-out attempts—not legitimate Incomplete or Blocked results—and raise Luna from Medium to High.

17. **Should M-27 be forbidden in bounded Ralph and RalphOnce?**  
    **Answer: A.** Both modes are forbidden from running M-27.

18. **What bounded branch strategy should be used?**  
    **Answer: C.** One permanent implementation branch.

19. **What is the exact permanent bounded branch name?**  
    **Answer: C.** `implementation`.

20. **Who performs the commit and push?**  
    **Answer: B.** The host PowerShell runner, after validating the agent result.

## MCP, secrets, and branch initialization

21. **How does Codex currently access Linear?**  
    **Answer: D.** The screenshots showed the Linear App plus a directly configured Linear MCP connection. Docker receives an explicit project-scoped MCP configuration.

22. **How should Git pushes authenticate?**  
    **Answer: A/D.** Prefer the host's SSH setup; use the existing host credential mechanism if SSH is not practical. Git push happens outside Docker.

23. **How should the M-27 prohibition be enforced?**  
    **Answer: A.** Update the canonical prompt so M-27 is never selectable and implementation completion becomes Review Required.

24. **How should Docker authenticate to Linear?**  
    **Answer: A, storage path later consolidated.** The scoped Linear key is stored in gitignored `resources/spotify-secrets.env`. Host setup registers it as a Docker custom proxy secret exposed only through the MCP authorization path.

25. **How should `implementation` start?**  
    **Answer: A.** If absent, create it from the currently checked-out branch; if it exists, resume and synchronize it safely.

26. **Should bounded Ralph automatically switch to `implementation` from another branch?**  
    **Answer: C.** Only with a clean worktree.

27. **What is the Docker sandbox name?**  
    **Answer:** `perfect-playlist-ralph`.

28. **What permissions does the scoped Linear key have?**  
    **Answer:** Full access.

29. **How should the Spotify secret file be named?**  
    **Answer: C, example location refined.** Use `resources/spotify-secrets.env`, with repository-root `spotify-secrets.env.example` as the safe committed example.

30. **What happens after a successful RalphOnce?**  
    **Answer: A.** Commit and push on the currently checked-out branch, then stop.

## Prompt location and Git ownership

31. **Where should the canonical prompt live?**  
    **Answer: B.** `.ralph/TASK-EXECUTION-PROMPT.md`.

32. **Should repository and secret references be absolute or relative?**  
    **Answer: B.** Use repository-relative behavior, while documenting the expected local checkout `C:\dev\personal\spotify-playlist-modify`; the secret path is `resources/spotify-secrets.env`.

33. **Should the agent see the raw Linear key as a normal environment variable?**  
    **Answer: A.** No. Only the MCP proxy path receives it; the agent sees a placeholder, not the real secret.

34. **What commit message format should be used?**  
    **Answer: A, generalized.** `<TASK_ID>: <title>` (for example, `M-135: Flatten the Python package to the repository root`).

35. **What if a task reports Complete but creates no Git changes?**  
    **Answer: A.** Treat it as incomplete/suspicious and stop; do not create an empty commit.

36. **Should the prompt explicitly forbid Codex from committing or pushing?**  
    **Answer: A.** Yes. Git publication is exclusively host-runner behavior.

37. **What if Codex creates a commit anyway?**  
    **Answer: A.** Stop immediately and do not push it automatically.

38. **What about pre-existing staged changes?**  
    **Answer: A.** Refuse to start while anything is already staged.

39. **When is a failed Medium attempt eligible for High retry?**  
    **Answer: C.** Only when HEAD, index/status, and workspace files are unchanged. Otherwise stop for manual review.

40. **How should the bounded branch synchronize at startup?**  
    **Answer: A.** Fetch, create `implementation` from the current branch if absent, otherwise switch and fast-forward safely; stop on divergence.

## Timeouts, logs, and completion

41. **What is the per-iteration timeout?**  
    **Answer: custom split.** Medium: 20 minutes. High recovery: 40 minutes.

42. **Should automatic High recovery apply to RalphOnce?**  
    **Answer: C.** Only when `RalphOnce.ps1 -Retry` is explicitly supplied.

43. **How does RalphOnce decide whether to commit without a machine marker?**  
    **Answer: A.** Parse exactly one `Status: Complete` line. Any other status means no commit or push.

44. **Should complete Codex output be saved?**  
    **Answer: A.** Save gitignored transcripts under `.ralph/logs/`.

45. **Should the runner write machine-readable state?**  
    **Answer: A.** Write `.ralph/state/latest-run.json`.

46. **What happens when all implementation children are done and M-27 remains?**  
    **Answer: A.** Exit successfully with a clear Review Required result.

## Additional safety

47. **What if bounded Ralph starts on another branch with a dirty worktree?**  
    **Answer: A.** Stop and require manual branch switching.

48. **Do pre-existing untracked files count as protected dirty overlap?**  
    **Answer: A.** Yes.

49. **What if Linear is Done and the host push then fails permanently?**  
    **Answer: A.** Leave the verified local commit and Linear state intact, stop, and require manual push recovery.

50. **Should sensitive paths be hard-blocked from commits?**  
    **Answer: A.** Yes: `.env`, non-example `.env.*`, `resources/spotify-secrets.env`, token caches, PEM files, and key files.

51. **Should the named Docker sandbox be reused?**  
    **Answer: A.** Yes, so installed dependencies and sandbox state persist while each Codex conversation remains fresh.

52. **Should concurrent Ralph runs be prevented?**  
    **Answer: A.** Yes, with a local lock.

53. **What PowerShell version is supported?**  
    **Answer: A.** Require PowerShell 7 (`pwsh`).

54. **Where should the user-facing commands live?**  
    **Answer: A.** `Ralph.ps1` and `RalphOnce.ps1` at the repository root; internals under `.ralph/`.

55. **Should sandbox bootstrap be automatic?**  
    **Answer: A.** Yes. Check/create/reuse the sandbox and verify Codex, dependencies, and Linear MCP access before task execution.

56. **How should the real Spotify secret file be protected?**  
    **Answer: A.** Snapshot its exact bytes before each attempt; if altered or deleted, restore the original bytes and stop.

57. **What Docker network policy should be used initially?**  
    **Answer: A.** Balanced.

58. **What if `origin/implementation` moves between iterations?**  
    **Answer: A.** Fetch before every iteration and stop if the remote advanced or diverged unexpectedly.

59. **Should Ralph create or manage pull requests?**  
    **Final answer: A.** No. Ralph pushes branches only and never opens, edits, merges, or closes a PR. The brief later PR discussion was explicitly scrapped.


## Current Docker custom-secret implementation note

The intended security property from questions 24 and 33 is preserved: the Linear API key remains host-held, the sandbox receives only a placeholder, and substitution is limited to requests sent to `mcp.linear.app`. Docker's current documented `set-custom` syntax uses global registration (`-g`) rather than a named-sandbox scope. Therefore, the setup uses the currently supported domain-scoped global form while keeping the task sandbox itself named `perfect-playlist-ralph`.

## Final command summary

```powershell
# Configure OAuth, Linear secret, sandbox, dependencies, and MCP smoke test
pwsh .\Setup-Ralph.ps1

# One fresh session; no automatic retry
pwsh .\RalphOnce.ps1

# One fresh session with one clean-state High recovery attempt
pwsh .\RalphOnce.ps1 -Retry

# Five maximum successful iterations on implementation
pwsh .\Ralph.ps1

# Explicit maximum and model controls
pwsh .\Ralph.ps1 -Iterations 3 -Model gpt-5.6-luna -ReasoningEffort medium
```
