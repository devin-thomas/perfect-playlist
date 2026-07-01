from __future__ import annotations

from pathlib import Path

from .track_refs import normalize_track_ref


def read_uri_lines(path: str | Path) -> list[str]:
    """Read exact Spotify track references from a text file."""
    source = Path(path)
    uris: list[str] = []

    lines = source.read_text(encoding="utf-8").splitlines()
    for line_number, raw_line in enumerate(lines, start=1):
        value = raw_line.strip()
        if not value or value.startswith("#"):
            continue
        try:
            uris.append(normalize_track_ref(value))
        except Exception as exc:
            msg = f"Line {line_number} is not a Spotify track URI or URL: {value}"
            raise type(exc)(msg) from exc

    return uris


def read_manifest(path: str | Path) -> object:
    """Placeholder for YAML manifest support."""
    raise NotImplementedError(f"Manifest support is not implemented yet: {path}")
