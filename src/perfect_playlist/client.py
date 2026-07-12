from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol, cast

import spotipy
from requests.exceptions import RequestException
from spotipy.exceptions import SpotifyException, SpotifyOauthError

from .auth import build_auth_manager

SPOTIFY_API_EXCEPTIONS = (SpotifyException, SpotifyOauthError, RequestException)


class PlaylistClient(Protocol):
    def current_user_playlist_create(
        self,
        name: str,
        public: bool,
        collaborative: bool = False,
        description: str = "",
    ) -> dict[str, Any]: ...

    def playlist(self, playlist_id: str, fields: str) -> dict[str, Any]: ...

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

    def playlist_replace_items(
        self,
        playlist_id: str,
        items: Sequence[str],
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
    def current_user(self) -> dict[str, Any]: ...


def get_spotify_client() -> SpotifyClient:
    """Create an authenticated Spotify Web API client."""
    return cast(SpotifyClient, spotipy.Spotify(auth_manager=build_auth_manager()))
