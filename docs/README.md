# Perfect Playlist Documentation

This directory is the single documentation home for product decisions, implementation work, and QA evidence.

Read in this order:

1. [Product and Language](PRODUCT-AND-LANGUAGE.md) - vision, mission, origin, principles, and canonical terms.
2. [CLI Contract](CLI-CONTRACT.md) - authoritative user-visible behavior and exact command semantics.
3. [Implementation Plan](IMPLEMENTATION-PLAN.md) - ordered engineering work derived from the contract.
4. [Git Completion Workflow](GIT-WORKFLOW.md) - mandatory commit-on-pass rules for manual agents and Ralph.
5. [Live QA](LIVE-QA.md) - credentialed Spotify evidence, unresolved external behavior, and safety notes.

Use [the Ralph task prompt](../.ralph/TASK-EXECUTION-PROMPT.md) unchanged only inside Ralph, where the host runner owns Git. Use [the Desktop task prompt](TASK-EXECUTION-PROMPT.md) for manual Codex sessions, where the task agent owns the local completion commit. Linear blockers identify the one next child, so the user never has to supply or infer an issue ID.

Ralph operators should also read:

- [Ralph Setup Decisions](RALPH-SETUP-DECISIONS.md) - the complete automation and safety decision record.
- [Ralph Setup Guide](README-RALPH.md) - setup, one-shot, bounded-loop, recovery, logging, and troubleshooting instructions.

## Authority

When documents or existing code disagree, use this order:

1. `docs/CLI-CONTRACT.md` for CLI and behavioral decisions.
2. `docs/PRODUCT-AND-LANGUAGE.md` for product intent and terminology.
3. `docs/IMPLEMENTATION-PLAN.md` for sequencing and acceptance criteria.
4. `AGENTS.md` and `docs/GIT-WORKFLOW.md` for commit ownership and completion rules.
5. `docs/LIVE-QA.md` for historical test evidence and external Spotify observations.
6. The applicable task prompt for task selection, execution gates, and M-27 prohibition.
7. `docs/RALPH-SETUP-DECISIONS.md` for runner behavior and security decisions.
8. Existing code only as the implementation baseline, not as authority for superseded behavior.

Git history is the archive for the former root plans and individual completed-task notes. A task is not Complete until its validated, task-owned diff is committed according to `AGENTS.md` and [the Git completion workflow](GIT-WORKFLOW.md). Manual agents own their local commit; Ralph sandbox agents leave Git to the host runner. Do not recreate parallel planning documents; update the authoritative document that owns the decision.
