from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import TypeVar

from .client import PlaylistClient, get_spotify_client
from .errors import PlaylistAddError, PlaylistCreateError
from .io import read_uri_lines
from .models import CreatedPlaylist, PlaylistCreateResult
from .track_refs import normalize_track_ref
from .verify import verify_playlist_prefix

T = TypeVar("T")
DEFAULT_DESCRIPTION = "Created with spotify-exact."


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
    user = sp.current_user()

    try:
        playlist = sp.user_playlist_create(
            user=user["id"],
            name=name,
            public=public,
            description=description,
            collaborative=collaborative,
        )
    except Exception as exc:  # pragma: no cover - exercised by mocked API tests later.
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
    start_position: int | None = None,
    client: PlaylistClient | None = None,
) -> str:
    """Add items in the exact order provided and return the final snapshot id."""
    normalized = [normalize_track_ref(uri) for uri in uris]
    sp = client or get_spotify_client()
    snapshot_id = ""

    for chunk_index, batch in enumerate(chunked(normalized, 100), start=1):
        try:
            if start_position is not None and chunk_index == 1:
                response = sp.playlist_add_items(
                    playlist_id=playlist_id,
                    items=batch,
                    position=start_position,
                )
            else:
                response = sp.playlist_add_items(playlist_id=playlist_id, items=batch)
        except Exception as exc:  # pragma: no cover - exercised by mocked API tests later.
            raise PlaylistAddError(
                f"Spotify rejected add-items request for chunk {chunk_index}."
            ) from exc
        snapshot_id = response.get("snapshot_id", snapshot_id)

    return snapshot_id


def create_playlist_from_uris(
    name: str,
    uris: Sequence[str],
    *,
    public: bool = False,
    description: str = DEFAULT_DESCRIPTION,
    dry_run: bool = False,
    verify: bool = True,
    client: PlaylistClient | None = None,
) -> PlaylistCreateResult:
    """Create a playlist from exact track references."""
    normalized = [normalize_track_ref(uri) for uri in uris]

    if dry_run:
        return PlaylistCreateResult(
            playlist=CreatedPlaylist(
                id="dry-run",
                uri="spotify:playlist:dry-run",
                url="",
                name=name,
            ),
            added_uris=normalized,
            verified=None,
        )

    sp = client or get_spotify_client()
    playlist = create_empty_playlist(name, public=public, description=description, client=sp)
    snapshot_id = add_items_in_order(playlist.id, normalized, client=sp)
    playlist.snapshot_id = snapshot_id
    verified = verify_playlist_prefix(playlist.id, normalized, client=sp) if verify else None

    return PlaylistCreateResult(
        playlist=playlist,
        added_uris=normalized,
        verified=verified,
    )


def create_playlist_from_file(
    name: str,
    path: str | Path,
    *,
    public: bool = False,
    description: str = DEFAULT_DESCRIPTION,
    dry_run: bool = False,
    verify: bool = True,
    client: PlaylistClient | None = None,
) -> PlaylistCreateResult:
    """Read exact track references from a file and create a playlist."""
    return create_playlist_from_uris(
        name=name,
        uris=read_uri_lines(path),
        public=public,
        description=description,
        dry_run=dry_run,
        verify=verify,
        client=client,
    )
