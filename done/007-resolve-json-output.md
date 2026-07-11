# Task 007: Resolver JSON Output

Status: done

Added `--json` output to `resolve setlist`. The command continues to write the
reviewable YAML manifest and additionally prints its structured representation
for scripts and other non-Python tools.

Verification:

- CLI JSON output includes manifest metadata and review flags.
- Existing human-readable resolver output remains unchanged.
- Full test and lint suites pass.
