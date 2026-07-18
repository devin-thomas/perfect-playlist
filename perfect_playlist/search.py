from __future__ import annotations

from collections.abc import Mapping, Sequence

from .client import SPOTIFY_API_EXCEPTIONS, TrackLookupClient, get_spotify_client
from .errors import InvalidTrackRefError, TrackLookupError
from .models import TrackSummary
from .track_refs import normalize_track_ref


def _track_summary(track: object) -> TrackSummary:
    if not isinstance(track, Mapping):
        raise TrackLookupError("Spotify returned invalid track metadata.")

    uri = track.get("uri")
    title = track.get("name")
    artists = track.get("artists")
    external_urls = track.get("external_urls")
    duration_ms = track.get("duration_ms")
    explicit = track.get("explicit")
    if (
        not isinstance(uri, str)
        or not isinstance(title, str)
        or not isinstance(artists, list)
        or not isinstance(external_urls, Mapping)
        or not isinstance(external_urls.get("spotify"), str)
        or not isinstance(duration_ms, int)
        or duration_ms < 0
        or not isinstance(explicit, bool)
    ):
        raise TrackLookupError("Spotify returned invalid track metadata.")

    artist_names: list[str] = []
    for artist in artists:
        if not isinstance(artist, Mapping) or not isinstance(artist.get("name"), str):
            raise TrackLookupError("Spotify returned invalid track metadata.")
        artist_names.append(artist["name"])

    album = track.get("album")
    album_name = album.get("name") if isinstance(album, Mapping) else None
    if album_name is not None and not isinstance(album_name, str):
        raise TrackLookupError("Spotify returned invalid track metadata.")

    try:
        canonical_uri = normalize_track_ref(uri)
    except InvalidTrackRefError as exc:
        raise TrackLookupError("Spotify returned invalid track metadata.") from exc

    return TrackSummary(
        uri=canonical_uri,
        url=external_urls["spotify"],
        title=title,
        artists=artist_names,
        album=album_name,
        duration_ms=duration_ms,
        explicit=explicit,
    )


def search_tracks(
    query: str,
    *,
    limit: int = 4,
    client: TrackLookupClient | None = None,
) -> list[TrackSummary]:
    """Search Spotify track candidates without writing to Spotify."""
    if not query.strip():
        raise TrackLookupError("Query must not be empty.")
    if not 1 <= limit <= 10:
        raise TrackLookupError("Search limit must be between 1 and 10.")

    sp = client or get_spotify_client()
    try:
        response = sp.search(q=query, type="track", limit=limit, market=None)
    except SPOTIFY_API_EXCEPTIONS as exc:
        raise TrackLookupError(f"Spotify track search failed for query: {query}") from exc
    tracks = response.get("tracks")
    items = tracks.get("items") if isinstance(tracks, Mapping) else None
    if not isinstance(items, list):
        raise TrackLookupError("Spotify returned invalid search results.")
    return [_track_summary(track) for track in items]


def get_tracks(
    uris: Sequence[str],
    *,
    client: TrackLookupClient | None = None,
) -> list[TrackSummary]:
    """Fetch metadata for exact Spotify track references."""
    normalized = [normalize_track_ref(uri) for uri in uris]
    ids = [uri.rsplit(":", 1)[1] for uri in normalized]
    sp = client or get_spotify_client()
    try:
        response = sp.tracks(ids, market=None)
    except SPOTIFY_API_EXCEPTIONS as exc:
        raise TrackLookupError("Spotify track metadata lookup failed.") from exc
    tracks = response.get("tracks")
    if not isinstance(tracks, list):
        raise TrackLookupError("Spotify returned invalid track metadata.")
    return [_track_summary(track) for track in tracks if track is not None]


def inspect_track(
    track_reference: str,
    *,
    client: TrackLookupClient | None = None,
) -> TrackSummary:
    """Return metadata for exactly one typed Spotify track reference."""
    if not track_reference.strip():
        raise TrackLookupError("Track reference must not be empty.")
    tracks = get_tracks([track_reference], client=client)
    if not tracks:
        raise TrackLookupError("Spotify returned no accessible track for this reference.")
    return tracks[0]
