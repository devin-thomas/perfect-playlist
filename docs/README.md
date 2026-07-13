# Perfect Playlist Documentation

This directory is the single documentation home for product decisions, implementation work, and QA evidence.

Read in this order:

1. [Product and Language](PRODUCT-AND-LANGUAGE.md) - vision, mission, origin, principles, and canonical terms.
2. [CLI Contract](CLI-CONTRACT.md) - authoritative user-visible behavior and exact command semantics.
3. [Implementation Plan](IMPLEMENTATION-PLAN.md) - ordered engineering work derived from the contract.
4. [Live QA](LIVE-QA.md) - credentialed Spotify evidence, unresolved external behavior, and safety notes.

Use the canonical [Automatic Next-Task Prompt](../.ralph/TASK-EXECUTION-PROMPT.md) unchanged for each implementation session. Linear blockers identify the one next child, so the user never has to supply or infer an issue ID.

Ralph operators should also read:

- [Ralph Setup Decisions](RALPH-SETUP-DECISIONS.md) - the complete automation and safety decision record.
- [Ralph Setup Guide](README-RALPH.md) - setup, one-shot, bounded-loop, recovery, logging, and troubleshooting instructions.

## Authority

When documents or existing code disagree, use this order:

1. `docs/CLI-CONTRACT.md` for CLI and behavioral decisions.
2. `docs/PRODUCT-AND-LANGUAGE.md` for product intent and terminology.
3. `docs/IMPLEMENTATION-PLAN.md` for sequencing and acceptance criteria.
4. `docs/LIVE-QA.md` for historical test evidence and external Spotify observations.
5. `.ralph/TASK-EXECUTION-PROMPT.md` for automated task selection, execution gates, and M-27 prohibition.
6. `docs/RALPH-SETUP-DECISIONS.md` for runner behavior and security decisions.
7. Existing code only as the implementation baseline, not as authority for superseded behavior.

Git history is the archive for the former root plans and individual completed-task notes. Do not recreate parallel planning documents; update the authoritative document that owns the decision.
