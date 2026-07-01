from __future__ import annotations

import spotipy

from .auth import build_auth_manager


def get_spotify_client() -> spotipy.Spotify:
    """Create an authenticated Spotify Web API client."""
    return spotipy.Spotify(auth_manager=build_auth_manager())

