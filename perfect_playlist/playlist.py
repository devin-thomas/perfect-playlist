from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import TypeVar

from .client import SPOTIFY_API_EXCEPTIONS, PlaylistClient, get_spotify_client
from .errors import (
    InvalidTrackRefError,
    PlaylistAddError,
    PlaylistCreateError,
    PlaylistVerificationError,
)
from .models import CreatedPlaylist, PlaylistCreateResult, TrackSequence
from .track_refs import normalize_playlist_ref, normalize_track_ref

T = TypeVar("T")
DEFAULT_DESCRIPTION = "Created with perfect-playlist."
PUBLIC_BUILD_DESCRIPTION = "Built with Perfect Playlist"
DEFAULT_BUILD_NAME = "My Perfect Playlist"


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


def build_public_playlist(
    sequence: TrackSequence,
    *,
    name: str | None = None,
    client: PlaylistClient | None = None,
) -> PlaylistCreateResult:
    """Build and verify a new public playlist from an exact TrackSequence."""
    if not sequence.uris:
        raise PlaylistCreateError("Build requires a non-empty TrackSequence.")

    sp = client or get_spotify_client()
    owned_names = _owned_playlist_names(sp)
    playlist_name = _choose_build_name(name, owned_names)
    result = create_playlist_from_uris(
        playlist_name,
        sequence.uris,
        public=True,
        description=PUBLIC_BUILD_DESCRIPTION,
        client=sp,
    )

    try:
        stored = TrackSequence(uris=tuple(_read_playlist_uris(result.playlist.id, sp)))
    except SPOTIFY_API_EXCEPTIONS + (InvalidTrackRefError,) as exc:
        raise PlaylistVerificationError(
            f"Could not verify playlist contents after building {result.playlist.url}."
        ) from exc
    if stored != sequence:
        raise PlaylistVerificationError(
            f"Spotify stored different tracks or order for playlist {result.playlist.url}."
        )
    return result


def build_target_playlist(
    sequence: TrackSequence,
    target: str,
    *,
    private: bool = False,
    client: PlaylistClient | None = None,
) -> PlaylistCreateResult:
    """Fill an owned, empty playlist target and verify the exact contents."""
    if not sequence.uris:
        raise PlaylistCreateError("Build requires a non-empty TrackSequence.")

    try:
        playlist_uri = normalize_playlist_ref(target)
    except InvalidTrackRefError as exc:
        raise PlaylistCreateError(str(exc)) from exc

    playlist_id = playlist_uri.rsplit(":", 1)[-1]
    sp = client or get_spotify_client()
    playlist = _read_build_target(playlist_id, sp)

    try:
        user = sp.current_user()
    except SPOTIFY_API_EXCEPTIONS as exc:
        raise PlaylistCreateError("Could not identify the signed-in Spotify user.") from exc
    user_id = user.get("id")
    owner = playlist.get("owner")
    owner_id = owner.get("id") if isinstance(owner, dict) else None
    if not isinstance(user_id, str) or not user_id:
        raise PlaylistCreateError("Spotify did not identify the signed-in user.")
    if owner_id != user_id:
        raise PlaylistCreateError("Build target must be owned by the signed-in user.")
    if playlist.get("collaborative") is True:
        raise PlaylistCreateError("Collaborative playlists cannot be Build targets.")
    tracks = playlist.get("tracks")
    if not isinstance(tracks, dict) or tracks.get("total") != 0:
        raise PlaylistCreateError("Build target must be empty.")
    if private and playlist.get("public") is not False:
        raise PlaylistCreateError("--private requires Spotify to report a private target.")

    name = playlist.get("name")
    external_urls = playlist.get("external_urls")
    url = external_urls.get("spotify") if isinstance(external_urls, dict) else None
    if not isinstance(name, str) or not isinstance(url, str):
        raise PlaylistCreateError("Spotify returned an invalid Build target.")

    snapshot_id = add_items_in_order(playlist_id, sequence.uris, playlist_url=url, client=sp)
    try:
        stored = TrackSequence(uris=tuple(_read_playlist_uris(playlist_id, sp)))
    except SPOTIFY_API_EXCEPTIONS + (InvalidTrackRefError,) as exc:
        raise PlaylistVerificationError(
            f"Could not verify playlist contents after building {url}."
        ) from exc
    if stored != sequence:
        raise PlaylistVerificationError(
            f"Spotify stored different tracks or order for playlist {url}."
        )

    return PlaylistCreateResult(
        playlist=CreatedPlaylist(
            id=playlist_id,
            uri=playlist_uri,
            url=url,
            name=name,
            snapshot_id=snapshot_id,
        ),
        added_uris=list(sequence.uris),
    )


def _read_build_target(playlist_id: str, client: PlaylistClient) -> dict[str, object]:
    try:
        playlist = client.playlist(
            playlist_id,
            fields="id,uri,name,description,public,collaborative,owner(id),tracks(total),external_urls(spotify)",
        )
    except SPOTIFY_API_EXCEPTIONS as exc:
        raise PlaylistCreateError(f"Could not read Spotify playlist target {playlist_id}.") from exc
    if not isinstance(playlist, dict):
        raise PlaylistCreateError("Spotify returned an invalid Build target.")
    return playlist


def _owned_playlist_names(client: PlaylistClient) -> set[str]:
    try:
        user = client.current_user()
        user_id = user.get("id")
        if not isinstance(user_id, str) or not user_id:
            raise PlaylistCreateError("Spotify did not identify the signed-in user.")

        names: set[str] = set()
        offset = 0
        while True:
            page = client.current_user_playlists(limit=50, offset=offset)
            if not isinstance(page, dict):
                raise PlaylistCreateError("Spotify returned an invalid owned-playlist page.")
            items = page.get("items")
            if not isinstance(items, list):
                raise PlaylistCreateError("Spotify returned an invalid owned-playlist page.")
            for item in items:
                if not isinstance(item, dict):
                    raise PlaylistCreateError("Spotify returned an invalid owned-playlist entry.")
                owner = item.get("owner")
                playlist_name = item.get("name")
                if isinstance(owner, dict) and owner.get("id") == user_id:
                    if not isinstance(playlist_name, str):
                        raise PlaylistCreateError(
                            "Spotify returned an owned playlist without a name."
                        )
                    names.add(playlist_name)
            if "next" not in page:
                raise PlaylistCreateError("Spotify returned an incomplete owned-playlist scan.")
            if page["next"] is None:
                return names
            if not items:
                raise PlaylistCreateError("Spotify returned an incomplete owned-playlist scan.")
            offset += len(items)
    except PlaylistCreateError:
        raise
    except SPOTIFY_API_EXCEPTIONS as exc:
        raise PlaylistCreateError(
            "Spotify rejected the owned-playlist scan; no playlist was created."
        ) from exc


def _choose_build_name(name: str | None, owned_names: set[str]) -> str:
    if name is not None:
        if name in owned_names:
            raise PlaylistCreateError(f"You already own a playlist named {name!r}.")
        return name

    candidate = DEFAULT_BUILD_NAME
    suffix = 0
    while candidate in owned_names:
        suffix += 1
        candidate = f"{DEFAULT_BUILD_NAME} ({suffix})"
    return candidate


def _read_playlist_uris(playlist_id: str, client: PlaylistClient) -> list[str]:
    uris: list[str] = []
    offset = 0
    while True:
        response = client.playlist_items(
            playlist_id,
            fields="items(track(uri)),next",
            limit=100,
            offset=offset,
        )
        if not isinstance(response, dict):
            raise PlaylistVerificationError("Spotify returned invalid playlist contents.")
        items = response.get("items")
        if not isinstance(items, list):
            raise PlaylistVerificationError("Spotify returned invalid playlist contents.")
        for item in items:
            if not isinstance(item, dict):
                raise PlaylistVerificationError("Spotify returned invalid playlist contents.")
            track = item.get("track")
            if not isinstance(track, dict) or not isinstance(track.get("uri"), str):
                raise PlaylistVerificationError("Spotify returned an inaccessible playlist track.")
            uris.append(normalize_track_ref(track["uri"]))
        if response.get("next") is None:
            return uris
        if not items:
            raise PlaylistVerificationError("Spotify returned an incomplete playlist page.")
        offset += len(items)
