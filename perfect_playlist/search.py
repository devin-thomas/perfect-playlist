from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .client import SPOTIFY_API_EXCEPTIONS, TrackLookupClient, get_spotify_client
from .errors import TrackLookupError
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
    limit: int = 4,
    market: str | None = None,
    client: TrackLookupClient | None = None,
) -> list[TrackSummary]:
    """Search Spotify track candidates without writing to Spotify."""
    sp = client or get_spotify_client()
    try:
        response = sp.search(q=query, type="track", limit=limit, market=market)
    except SPOTIFY_API_EXCEPTIONS as exc:
        raise TrackLookupError(f"Spotify track search failed for query: {query}") from exc
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
    try:
        response = sp.tracks(ids, market=market)
    except SPOTIFY_API_EXCEPTIONS as exc:
        raise TrackLookupError("Spotify track metadata lookup failed.") from exc
    return [_track_summary(track) for track in response.get("tracks", []) if track]
