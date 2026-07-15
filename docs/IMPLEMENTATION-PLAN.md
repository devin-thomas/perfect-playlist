# Perfect Playlist Implementation Plan

**Status:** Parent 1 complete; Parent 2 is in progress through child [2.2].

This is the sole active engineering plan. It reconciles the original build plan, the empty private playlist proposal, the completed task notes, the live-test handoff, and the approved CLI contract.

## Linear Tracking

- [Parent 1 - Canonical core and CLI shell](https://linear.app/devin-main/issue/M-115/13-establish-the-canonical-core-and-cli-shell)
- [First child - Flatten the Python package](https://linear.app/devin-main/issue/M-135/10-flatten-the-python-package-to-the-repository-root)
- [Parent 2 - Safe deterministic workflows](https://linear.app/devin-main/issue/M-116/23-deliver-safe-deterministic-workflows)
- [Parent 3 - Read-only tools, agent interface, and QA](https://linear.app/devin-main/issue/M-117/33-complete-read-only-tools-agent-interface-and-qa)
- [Independent final release review](https://linear.app/devin-main/issue/M-27/final-release-review-and-docstutorialreadme-cleanup-pass)

The parent issues are ordered by numeric title and dependency: Parent 2 is blocked by Parent 1, Parent 3 is blocked by Parent 2, and the independent final review is blocked by Parent 3.

Children are also dependency-chained in coordinate order: `[1.0]` through `[1.6]`, then `[2.1]` through `[2.6]`, then `[3.1]` through `[3.6]`. Linear's visual issue order and numeric issue IDs do not define execution order. The canonical `.ralph/TASK-EXECUTION-PROMPT.md` selects and completes the single next executable child.

## Baseline

Parent 1 is complete. The repository contains a root-level Python 3.11 package, one URI-only TrackSequence, extension-driven and Spotify Source ingestion, interactive/non-interactive authentication, typed Spotify adapter boundaries, and the approved top-level command shell. Superseded grouped commands, repair, resolve, dry-run, position-based add, prefix verification, and metadata-rich manifest workflows have been removed.

Parent 2 is in progress. New-public Build, owned empty-target Build, append-only Add, and peer Source Verify implement their approved workflows; `export` remains fail closed with exit code `2` without Spotify or filesystem writes until its assigned task. Parent 3 `search` and `inspect` shells follow the same boundary. Existing lower-level playlist and lookup primitives are migration inputs for their assigned future tasks, not shipped implementations of those commands.

## Credential Decision

Use one repository-relative private file: `resources/spotify-secrets.env`.

- Runtime Spotify configuration loads that file directly through `python-dotenv`.
- Ralph reads `LINEAR_API_KEY` only in the host setup process to register Docker's domain-scoped Linear proxy secret; the agent receives only a placeholder.
- `resources/`, `spotify-secrets.env`, and legacy `.env` files are gitignored.
- `spotify-secrets.env.example` is the only committed credential-shape template.
- Agents must never read, display, log, modify, commit, paste into Linear, or duplicate the real file's contents.
- Credential values, OAuth codes, token caches, PEM/key material, and non-example environment files may not enter commits, issue descriptions, transcripts, or test output.

## Required Directive for Every Task

Every task owner must:

1. Log and report the start and end time in `America/Chicago` time.
2. Log and report the total whole minutes worked.
3. Mark the task complete only when its acceptance criteria are done and all applicable checks and tests pass.
4. If any test fails or is skipped, report that **boldly and clearly**, explain why, and do not represent the task as fully verified. Prefer resolving failures and eliminating unintended skips before handoff.
5. Credentials live only in gitignored `resources/spotify-secrets.env`. Approved runtime and test code may load it, but agents never directly open, print, inspect, modify, commit, paste into Linear, or duplicate its contents. Use `spotify-secrets.env.example` only to understand variable names.
6. Store every successfully verified task in a non-empty task-scoped commit before marking it Done or starting its successor. Linear commits use `<TASK_ID>: <issue title>`. Manual agents create the local commit. Ralph agents report Ready to Commit and leave Linear In Progress; the host runner commits, verifies, finalizes Linear, and pushes.

## Parent 1 of 3 - Establish the Canonical Core and CLI Shell (Complete)

Outcome: one TrackSequence model, one Source pipeline, predictable authentication, and only the approved action-based command surface.

Ordered child tasks:

1. Flatten the Python package from `src/perfect_playlist` to repository-root `perfect_playlist`, including packaging, tooling, and import validation.
2. Implement the URI-only `TrackSequence` value and strict validation while preserving order and duplicates.
3. Implement extension-driven YAML, JSON, and text Source parsing with ignored extra metadata and no silent skips.
4. Implement Spotify playlist and single-track URL/URI Sources; reject raw IDs, stdin, and arbitrary remote documents with actionable errors.
5. Implement interactive and non-interactive authentication behavior, cache refresh, and exit-code-safe error handling.
6. Replace grouped legacy commands with `build`, `add`, `verify`, `export`, `search`, and `inspect`; retain only the `auth` group.
7. Remove repair, resolve, dry-run, position insertion, legacy manifest models, aliases, compatibility shims, and unreachable tests/code.

Parent 1 blocks Parent 2.

## Parent 2 of 3 - Deliver Safe Deterministic Workflows (In Progress)

Outcome: Build, Add, Verify, and Export implement the complete approved contract with preflight safety and post-write verification.

Ordered child tasks:

1. Implement new-public Build with non-empty Source validation, exact description, owned-name scan, default collision suffixing, and explicit-name collision failure.
2. Implement target Build for owned empty public/private playlists, including interactive private prompting, ownership/privacy/emptiness preflight, and metadata preservation.
3. Implement append-only Add for explicit writable targets with before/after count and appended-segment verification, including concurrent-change failure handling.
4. Implement peer Source Verify with count-first and first-position-only diagnostics plus the reserved exit code `1` behavior.
5. Implement Export serialization, link rendering, terminal prompting, collision-free implicit names, exact explicit paths, and no-overwrite enforcement.
6. Align the importable Python API and typed exceptions with the same TrackSequence, Source, target, safety, and verification semantics.

Parent 2 blocks Parent 3.

## Parent 3 of 3 - Complete Read-Only Tools, Agent Interface, and QA (Not Started)

Outcome: discovery and inspection are agent-friendly, the new contract is comprehensively tested, and the credentialed release gate is honest and reproducible.

Ordered child tasks:

1. Implement top-level Search with track-only results, default limit `4`, allowed range `1..10`, authenticated-country behavior, and human/JSON output.
2. Implement top-level Inspect for one exact track URL/URI with human/JSON output and strict empty/raw-ID rejection.
3. Add contract-level CLI and library tests for Sources, exit codes, messages, target eligibility, collisions, empty handling, and removal of legacy commands.
4. Expand Spotify integration coverage for public creation, owned empty public/private target Build, owned/collaborative Add, Verify, Export, and fail-closed partial writes.
5. Create project `SKILL.md` and `AGENTS.md` guidance that teaches AI agents to search, inspect, construct durable TrackSequences, build deterministically, and report failures accurately.
6. Run the full offline and credentialed validation matrix and record reproducible evidence in `docs/LIVE-QA.md` without skipped live coverage in the credentialed run.

## Independent Final Review - Release Readiness and Documentation Cleanup

This task is outside the three parents and begins only after all three are complete.

- Review the whole change set against every line of the CLI contract.
- Run unit, integration, CLI smoke, Ruff, and Mypy checks in the correct environments.
- Perform a credentialed live Spotify QA pass using the private credential location described above.
- Complete a docs/tutorial/README/cleanup pass so every example uses only shipped behavior and all links resolve.
- Remove stale terminology, dead examples, obsolete files, temporary fixtures, and misleading status claims.
- Confirm secrets, `.env`, caches, authorization material, and private resources are untracked.
- Report Chicago start/end times, minutes worked, exact check results, and any **FAILED OR SKIPPED TESTS** before marking complete.

## Definition of Done

The plan is complete only when the action-based CLI and Python API satisfy `docs/CLI-CONTRACT.md`, no legacy public interface remains, offline checks pass, the required live matrix runs without unexplained skips, documentation matches the shipped package, and the final review task is complete.
