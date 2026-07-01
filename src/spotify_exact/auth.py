from __future__ import annotations

import os

from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

from .config import default_token_cache_path
from .errors import AuthConfigError

DEFAULT_SCOPES = (
    "playlist-modify-private "
    "playlist-modify-public "
    "playlist-read-private"
)
REQUIRED_SPOTIFY_ENV_VARS = (
    "SPOTIPY_CLIENT_ID",
    "SPOTIPY_CLIENT_SECRET",
    "SPOTIPY_REDIRECT_URI",
)


def missing_spotify_auth_env() -> list[str]:
    """Return missing Spotify OAuth environment variable names."""
    return [name for name in REQUIRED_SPOTIFY_ENV_VARS if not os.getenv(name)]


def build_auth_manager(
    *,
    scope: str | None = None,
    cache_path: str | None = None,
    open_browser: bool = True,
) -> SpotifyOAuth:
    """Build the Spotipy OAuth manager for local CLI usage."""
    load_dotenv()
    missing = missing_spotify_auth_env()
    if missing:
        names = ", ".join(missing)
        raise AuthConfigError(f"Spotify auth configuration is missing: {names}.")

    return SpotifyOAuth(
        scope=scope or DEFAULT_SCOPES,
        cache_path=cache_path or str(default_token_cache_path()),
        open_browser=open_browser,
    )
