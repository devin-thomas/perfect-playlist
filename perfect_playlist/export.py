from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import yaml

from .errors import ExportError
from .models import TrackSequence

ExportFormat = Literal["yaml", "json", "txt"]
SUPPORTED_EXTENSIONS = ".yaml, .yml, .json, and .txt"


def track_links(sequence: TrackSequence) -> list[str]:
    """Render canonical track URIs as Spotify web links."""
    return [
        f"https://open.spotify.com/track/{uri.rsplit(':', 1)[1]}" for uri in sequence.uris
    ]


def output_format(path: Path, *, links: bool) -> ExportFormat:
    """Validate an output path and return the extension-selected format."""
    suffix = path.suffix.lower()
    if links and suffix not in {"", ".txt"}:
        raise ExportError("--links can only be saved to a .txt output.")
    if suffix in {".yaml", ".yml"}:
        if links:
            raise ExportError("--links can only be saved to a .txt output.")
        return "yaml"
    if suffix == ".json":
        if links:
            raise ExportError("--links can only be saved to a .txt output.")
        return "json"
    if suffix == ".txt":
        return "txt"
    raise ExportError(
        f"Output path {path} has no supported extension; supported extensions are "
        f"{SUPPORTED_EXTENSIONS}."
    )


def serialize(sequence: TrackSequence, format: ExportFormat, *, links: bool = False) -> str:
    """Serialize a non-empty TrackSequence in the selected output format."""
    if not sequence:
        raise ExportError("Cannot export an empty TrackSequence.")
    values = track_links(sequence) if links else list(sequence.uris)
    if format == "yaml":
        return yaml.safe_dump({"tracks": values}, sort_keys=False)
    if format == "json":
        return json.dumps({"tracks": values}, indent=2) + "\n"
    return "\n".join(values) + "\n"


def write_export(sequence: TrackSequence, path: Path, *, links: bool = False) -> None:
    """Write an export exactly once, refusing to replace an existing path."""
    format = output_format(path, links=links)
    content = serialize(sequence, format, links=links)
    try:
        with path.open("x", encoding="utf-8", newline="") as handle:
            handle.write(content)
    except FileExistsError as exc:
        raise ExportError(f"File already exists: {path}") from exc
    except OSError as exc:
        raise ExportError(f"Could not write export {path}: {exc}") from exc


def next_available_path(base: Path) -> Path:
    """Return the first collision-free path using playlist(N) naming."""
    if not base.exists():
        return base
    for index in range(1, 10000):
        candidate = base.with_name(f"{base.stem}({index}){base.suffix}")
        if not candidate.exists():
            return candidate
    raise ExportError(f"Could not find an available export path based on {base}.")
