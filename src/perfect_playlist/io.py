from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from .errors import ManifestError
from .models import PlaylistManifest
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


def read_manifest(path: str | Path) -> PlaylistManifest:
    """Read and strictly validate a YAML playlist manifest."""
    source = Path(path)
    try:
        data = yaml.safe_load(source.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ManifestError(f"Could not parse YAML manifest {source}: {exc}") from exc

    try:
        return PlaylistManifest.model_validate(data)
    except ValidationError as exc:
        detail = exc.errors()[0].get("msg", "invalid manifest")
        raise ManifestError(f"Invalid playlist manifest {source}: {detail}") from exc
