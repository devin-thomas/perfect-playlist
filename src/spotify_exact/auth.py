from __future__ import annotations

from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

from .config import default_token_cache_path

DEFAULT_SCOPES = (
    "playlist-modify-private "
    "playlist-modify-public "
    "playlist-read-private"
)


def build_auth_manager(
    *,
    scope: str | None = None,
    cache_path: str | None = None,
    open_browser: bool = True,
) -> SpotifyOAuth:
    """Build the Spotipy OAuth manager for local CLI usage."""
    load_dotenv()
    return SpotifyOAuth(
        scope=scope or DEFAULT_SCOPES,
        cache_path=cache_path or str(default_token_cache_path()),
        open_browser=open_browser,
    )

