# Task 006: Manifest Review Gate

Status: done

Closed the resolver-to-creation safety gap. `playlist create --manifest` now
rejects any entry marked `needs_review: true`, including dry runs, before
playlist processing begins. Approved exact URIs and explicit `missing: true`
entries remain supported.

Verification:

- A manifest needing review fails with a clear count of pending entries.
- A reviewed manifest still supports dry-run creation.
- The full test suite remains green.
