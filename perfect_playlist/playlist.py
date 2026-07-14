from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import TypeVar

from .client import SPOTIFY_API_EXCEPTIONS, PlaylistClient, get_spotify_client
from .errors import PlaylistAddError, PlaylistCreateError
from .models import CreatedPlaylist, PlaylistCreateResult
from .track_refs import normalize_track_ref

T = TypeVar("T")
DEFAULT_DESCRIPTION = "Created with perfect-playlist."


def chunked(items: Sequence[T], size: int = 100) -> Iterable[list[T]]:
    """Yield fixed-size chunks while preserving order."""
    if size < 1:
        raise ValueError("Chunk size must be at least 1.")
    for index in range(0, len(items), size):
        yield list(items[index : index + size])


def create_empty_playlist(
    name: str,
    *,
    public: bool = False,
    description: str = DEFAULT_DESCRIPTION,
    collaborative: bool = False,
    client: PlaylistClient | None = None,
) -> CreatedPlaylist:
    """Create an empty Spotify playlist for the current user."""
    sp = client or get_spotify_client()

    try:
        playlist = sp.current_user_playlist_create(
            name=name,
            public=public,
            collaborative=collaborative,
            description=description,
        )
        if not public:
            persisted = sp.playlist(playlist["id"], fields="public")
            if persisted.get("public") is not False:
                raise PlaylistCreateError(
                    "Spotify stored playlist as public after private creation was requested. "
                    "No tracks were added. Make the empty playlist private in a Spotify "
                    "client before adding tracks: "
                    f"{playlist['external_urls']['spotify']}"
                )
    except SPOTIFY_API_EXCEPTIONS as exc:
        raise PlaylistCreateError(f"Spotify rejected playlist creation for {name!r}.") from exc

    return CreatedPlaylist(
        id=playlist["id"],
        uri=playlist["uri"],
        url=playlist["external_urls"]["spotify"],
        name=playlist["name"],
    )


def add_items_in_order(
    playlist_id: str,
    uris: Sequence[str],
    *,
    playlist_url: str | None = None,
    client: PlaylistClient | None = None,
) -> str:
    """Add items in the exact order provided and return the final snapshot id."""
    normalized = [normalize_track_ref(uri) for uri in uris]
    sp = client or get_spotify_client()
    snapshot_id = ""

    for chunk_index, batch in enumerate(chunked(normalized, 100), start=1):
        try:
            response = sp.playlist_add_items(playlist_id=playlist_id, items=batch)
        except SPOTIFY_API_EXCEPTIONS as exc:
            partial_state = f" Playlist may be incomplete: {playlist_url}" if playlist_url else ""
            raise PlaylistAddError(
                f"Spotify rejected add-items request for chunk {chunk_index}.{partial_state}"
            ) from exc
        snapshot_id = response.get("snapshot_id", snapshot_id)

    return snapshot_id


def create_playlist_from_uris(
    name: str,
    uris: Sequence[str],
    *,
    public: bool = False,
    description: str = DEFAULT_DESCRIPTION,
    client: PlaylistClient | None = None,
) -> PlaylistCreateResult:
    """Create a playlist from exact track references."""
    normalized = [normalize_track_ref(uri) for uri in uris]

    sp = client or get_spotify_client()
    playlist = create_empty_playlist(name, public=public, description=description, client=sp)
    snapshot_id = add_items_in_order(playlist.id, normalized, playlist_url=playlist.url, client=sp)
    playlist.snapshot_id = snapshot_id
    return PlaylistCreateResult(
        playlist=playlist,
        added_uris=normalized,
    )
