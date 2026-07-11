from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from .client import TrackLookupClient
from .errors import ManifestError
from .models import PlaylistManifest, SetlistInput
from .search import search_tracks


def _fold(value: str) -> str:
    return " ".join(value.casefold().split())


def _artist_matches(requested: str, artists: list[str]) -> bool:
    requested_folded = _fold(requested)
    return any(requested_folded == _fold(artist) for artist in artists)


def resolve_setlist(
    source: str | Path,
    output: str | Path,
    *,
    market: str | None = "US",
    client: TrackLookupClient | None = None,
) -> PlaylistManifest:
    """Resolve a human-readable setlist into a reviewable YAML manifest."""
    source_path = Path(source)
    output_path = Path(output)
    try:
        data = yaml.safe_load(source_path.read_text(encoding="utf-8"))
        setlist = SetlistInput.model_validate(data)
    except yaml.YAMLError as exc:
        raise ManifestError(f"Could not parse setlist YAML {source_path}: {exc}") from exc
    except ValidationError as exc:
        detail = exc.errors()[0].get("msg", "invalid setlist")
        raise ManifestError(f"Invalid setlist {source_path}: {detail}") from exc

    resolved_tracks: list[dict[str, object]] = []
    for track in setlist.tracks:
        query = f'track:"{track.title}" artist:"{track.artist}"'
        candidates = search_tracks(query, limit=5, market=market, client=client)
        exact = [
            candidate
            for candidate in candidates
            if _fold(candidate.title) == _fold(track.title)
            and _artist_matches(track.artist, candidate.artists)
        ]
        selected = exact[0] if len(exact) == 1 else None
        resolved: dict[str, object] = {
            "title": track.title,
            "artist": track.artist,
            "needs_review": selected is None,
            "candidate_uris": [candidate.uri for candidate in (exact or candidates)],
        }
        if selected is not None:
            resolved["uri"] = selected.uri
        if track.note:
            resolved["note"] = track.note
        elif selected is None:
            resolved["note"] = "Review candidates before creating a playlist."
        resolved_tracks.append(resolved)

    output_data = {
        "name": setlist.name,
        "public": setlist.public,
        "description": setlist.description,
        "tracks": resolved_tracks,
    }
    output_path.write_text(
        yaml.safe_dump(output_data, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )
    return PlaylistManifest.model_validate(output_data)
