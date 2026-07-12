# Perfect Playlist Implementation Plan

**Status:** Ready for execution.

This is the sole active engineering plan. It reconciles the original build plan, the empty private playlist proposal, the completed task notes, the live-test handoff, and the approved CLI contract.

## Linear Tracking

- [Parent 1 - Canonical core and CLI shell](https://linear.app/devin-main/issue/M-115/13-establish-the-canonical-core-and-cli-shell)
- [Parent 2 - Safe deterministic workflows](https://linear.app/devin-main/issue/M-116/23-deliver-safe-deterministic-workflows)
- [Parent 3 - Read-only tools, agent interface, and QA](https://linear.app/devin-main/issue/M-117/33-complete-read-only-tools-agent-interface-and-qa)
- [Independent final release review](https://linear.app/devin-main/issue/M-27/final-release-review-and-docstutorialreadme-cleanup-pass)

The parent issues are ordered by numeric title and dependency: Parent 2 is blocked by Parent 1, Parent 3 is blocked by Parent 2, and the independent final review is blocked by Parent 3.

Children are also dependency-chained in coordinate order: `[1.1]` through `[1.6]`, then `[2.1]` through `[2.6]`, then `[3.1]` through `[3.6]`. Linear's visual issue order and numeric issue IDs do not define execution order. Use `docs/TASK-EXECUTION-PROMPT.md` unchanged to select and complete the single next executable child.

## Baseline

The repository already contains a Python 3.11 package, Typer CLI, Spotipy OAuth, exact track normalization, ordered 100-item writes, search and inspection primitives, YAML models, export and verification code, unit tests, static checks, and an opt-in Spotify integration test.

The current implementation still exposes superseded grouped commands and concepts, including `playlist create`, prefix verification, repair, resolve, dry-run, position-based add, and metadata-rich manifests. These are migration inputs, not requirements. Reuse sound primitives where they satisfy the contract; remove incompatible public behavior and dead models completely.

## Credential Decision

Do not rename `resources/secrets.md` to `.env`.

- Runtime configuration already uses `python-dotenv` and the repository-root `.env`.
- `.env` and `resources/` are already gitignored; `.env.example` contains safe placeholders.
- `C:\dev\personal\spotify-playlist-modify\resources\secrets.md` remains the maintainer-only source note.
- Developers copy the three `SPOTIPY_*` values into local `.env`; production code must never parse Markdown credentials.
- No credential values, OAuth codes, token caches, or `.env` files may enter commits, issue descriptions, logs, or test output.

No code-conversion task is needed. Credential setup and documentation are covered by the final review.

## Required Directive for Every Task

Every task owner must:

1. Log and report the start and end time in `America/Chicago` time.
2. Log and report the total whole minutes worked.
3. Mark the task complete only when its acceptance criteria are done and all applicable checks and tests pass.
4. If any test fails or is skipped, report that **boldly and clearly**, explain why, and do not represent the task as fully verified. Prefer resolving failures and eliminating unintended skips before handoff.
5. For local Spotify credentials, use `C:\dev\personal\spotify-playlist-modify\resources\secrets.md` to populate the gitignored repository-root `.env`. Never commit or paste secrets.

## Parent 1 of 3 - Establish the Canonical Core and CLI Shell

Outcome: one TrackSequence model, one Source pipeline, predictable authentication, and only the approved action-based command surface.

Ordered child tasks:

1. Implement the URI-only `TrackSequence` value and strict validation while preserving order and duplicates.
2. Implement extension-driven YAML, JSON, and text Source parsing with ignored extra metadata and no silent skips.
3. Implement Spotify playlist and single-track URL/URI Sources; reject raw IDs, stdin, and arbitrary remote documents with actionable errors.
4. Implement interactive and non-interactive authentication behavior, cache refresh, and exit-code-safe error handling.
5. Replace grouped legacy commands with `build`, `add`, `verify`, `export`, `search`, and `inspect`; retain only the `auth` group.
6. Remove repair, resolve, dry-run, position insertion, legacy manifest models, aliases, compatibility shims, and unreachable tests/code.

Parent 1 blocks Parent 2.

## Parent 2 of 3 - Deliver Safe Deterministic Workflows

Outcome: Build, Add, Verify, and Export implement the complete approved contract with preflight safety and post-write verification.

Ordered child tasks:

1. Implement new-public Build with non-empty Source validation, exact description, owned-name scan, default collision suffixing, and explicit-name collision failure.
2. Implement target Build for owned empty public/private playlists, including interactive private prompting, ownership/privacy/emptiness preflight, and metadata preservation.
3. Implement append-only Add for explicit writable targets with before/after count and appended-segment verification, including concurrent-change failure handling.
4. Implement peer Source Verify with count-first and first-position-only diagnostics plus the reserved exit code `1` behavior.
5. Implement Export serialization, link rendering, terminal prompting, collision-free implicit names, exact explicit paths, and no-overwrite enforcement.
6. Align the importable Python API and typed exceptions with the same TrackSequence, Source, target, safety, and verification semantics.

Parent 2 blocks Parent 3.

## Parent 3 of 3 - Complete Read-Only Tools, Agent Interface, and QA

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
