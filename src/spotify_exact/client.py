from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol, cast

import spotipy

from .auth import build_auth_manager


class PlaylistClient(Protocol):
    def current_user(self) -> dict[str, Any]: ...

    def user_playlist_create(
        self,
        user: str,
        name: str,
        public: bool,
        description: str,
        collaborative: bool = False,
    ) -> dict[str, Any]: ...

    def playlist_add_items(
        self,
        playlist_id: str,
        items: Sequence[str],
        position: int | None = None,
    ) -> dict[str, Any]: ...

    def playlist_items(
        self,
        playlist_id: str,
        fields: str,
        limit: int,
        offset: int,
    ) -> dict[str, Any]: ...


class TrackLookupClient(Protocol):
    def search(
        self,
        q: str,
        type: str,
        limit: int,
        market: str | None = None,
    ) -> dict[str, Any]: ...

    def tracks(
        self,
        tracks: Sequence[str],
        market: str | None = None,
    ) -> dict[str, Any]: ...


class SpotifyClient(PlaylistClient, TrackLookupClient, Protocol):
    pass


def get_spotify_client() -> SpotifyClient:
    """Create an authenticated Spotify Web API client."""
    return cast(SpotifyClient, spotipy.Spotify(auth_manager=build_auth_manager()))
