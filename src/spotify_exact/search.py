from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .client import TrackLookupClient, get_spotify_client
from .models import TrackSummary
from .track_refs import normalize_track_ref


def _track_summary(track: dict[str, Any]) -> TrackSummary:
    external_urls = track.get("external_urls") or {}
    album = track.get("album") or {}
    return TrackSummary(
        uri=str(track["uri"]),
        url=str(external_urls.get("spotify", "")),
        title=str(track["name"]),
        artists=[str(artist["name"]) for artist in track.get("artists", [])],
        album=str(album.get("name")) if album else None,
        duration_ms=int(track["duration_ms"]) if track.get("duration_ms") is not None else None,
        explicit=bool(track["explicit"]) if track.get("explicit") is not None else None,
    )


def search_tracks(
    query: str,
    *,
    limit: int = 10,
    market: str | None = "US",
    client: TrackLookupClient | None = None,
) -> list[TrackSummary]:
    """Search Spotify track candidates without writing to Spotify."""
    sp = client or get_spotify_client()
    response = sp.search(q=query, type="track", limit=limit, market=market)
    items = response.get("tracks", {}).get("items", [])
    return [_track_summary(track) for track in items]


def get_tracks(
    uris: Sequence[str],
    *,
    market: str | None = "US",
    client: TrackLookupClient | None = None,
) -> list[TrackSummary]:
    """Fetch metadata for exact Spotify track references."""
    normalized = [normalize_track_ref(uri) for uri in uris]
    ids = [uri.rsplit(":", 1)[1] for uri in normalized]
    sp = client or get_spotify_client()
    response = sp.tracks(ids, market=market)
    return [_track_summary(track) for track in response.get("tracks", []) if track]
