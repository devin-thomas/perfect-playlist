# Task 001: YAML Manifest Support

Status: done

Implemented strict YAML playlist manifests at the `read_manifest(path)` seam.
URI and URL references are normalized, missing entries are excluded from the
resolved URI list, and malformed or contradictory entries raise `ManifestError`.
The CLI now supports `playlist create --manifest FILE`, while the existing
`NAME --from FILE` flow remains available.

Verification:

- `python -m pytest tests/test_manifest.py tests/test_cli_smoke.py tests/test_io.py`
- `python -m ruff check --no-cache src tests`
