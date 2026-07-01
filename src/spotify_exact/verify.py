from __future__ import annotations

from collections.abc import Sequence

from .client import PlaylistClient, get_spotify_client
from .errors import PlaylistVerificationError
from .track_refs import normalize_track_ref


def get_playlist_track_uris(
    playlist_id: str,
    *,
    limit: int | None = None,
    client: PlaylistClient | None = None,
) -> list[str]:
    """Fetch track URIs from a Spotify playlist in playlist order."""
    sp = client or get_spotify_client()
    remaining = limit
    offset = 0
    uris: list[str] = []

    while remaining is None or remaining > 0:
        page_limit = min(100, remaining) if remaining is not None else 100
        response = sp.playlist_items(
            playlist_id,
            fields="items(track(uri)),next",
            limit=page_limit,
            offset=offset,
        )
        items = response.get("items", [])
        if not items:
            break
        for item in items:
            track = item.get("track") or {}
            uri = track.get("uri")
            if uri:
                uris.append(str(uri))
        if response.get("next") is None:
            break
        offset += len(items)
        if remaining is not None:
            remaining -= len(items)

    return uris


def verify_playlist_prefix(
    playlist_id: str,
    expected_uris: Sequence[str],
    *,
    client: PlaylistClient | None = None,
) -> bool:
    """Raise if the playlist prefix does not match the expected exact URI order."""
    expected = [normalize_track_ref(uri) for uri in expected_uris]
    actual = get_playlist_track_uris(playlist_id, limit=len(expected), client=client)

    for index, expected_uri in enumerate(expected):
        actual_uri = actual[index] if index < len(actual) else "<missing>"
        if actual_uri != expected_uri:
            raise PlaylistVerificationError(
                "Playlist verification failed at index "
                f"{index}. Expected {expected_uri}, actual {actual_uri}."
            )

    return True
