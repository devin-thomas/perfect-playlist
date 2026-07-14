from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Protocol, TypeAlias

import typer
from dotenv import load_dotenv
from requests.exceptions import RequestException
from spotipy.cache_handler import CacheFileHandler
from spotipy.exceptions import SpotifyOauthError
from spotipy.oauth2 import SpotifyOAuth

from .config import default_token_cache_path
from .errors import AuthConfigError, SpotifyAuthenticationRequiredError

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
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SPOTIFY_SECRETS_FILE = REPOSITORY_ROOT / "resources/spotify-secrets.env"
AUTH_REQUIRED_MESSAGE = (
    "Spotify authorization required. Run perfect-playlist auth login, then retry."
)

# Spotipy owns this dynamic payload; keep it inside the OAuth adapter boundary.
SpotifyTokenInfo: TypeAlias = dict[str, Any]


class OAuthCache(Protocol):
    def get_cached_token(self) -> SpotifyTokenInfo | None: ...


class OAuthManager(Protocol):
    @property
    def cache_handler(self) -> OAuthCache: ...

    def validate_token(self, token_info: SpotifyTokenInfo | None) -> SpotifyTokenInfo | None: ...

    def get_access_token(self, *, check_cache: bool) -> object: ...


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
    try:
        load_dotenv(dotenv_path=SPOTIFY_SECRETS_FILE)
    except OSError as exc:
        raise AuthConfigError("Could not read the repository Spotify auth configuration.") from exc

    missing = missing_spotify_auth_env()
    if missing:
        names = ", ".join(missing)
        raise AuthConfigError(f"Spotify auth configuration is missing: {names}.")

    token_cache_path = Path(cache_path).expanduser() if cache_path else default_token_cache_path()
    try:
        token_cache_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise AuthConfigError("Could not prepare the Spotify token cache directory.") from exc

    return SpotifyOAuth(
        scope=scope or DEFAULT_SCOPES,
        cache_handler=CacheFileHandler(cache_path=str(token_cache_path)),
        open_browser=open_browser,
    )


def command_is_interactive() -> bool:
    """Return whether the current command can safely prompt and open a browser."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def authenticate(
    manager: OAuthManager,
    *,
    interactive: bool,
) -> None:
    """Ensure a cached token is usable, or obtain one with the allowed UX."""
    try:
        token_info = manager.validate_token(manager.cache_handler.get_cached_token())
    except (RequestException, SpotifyOauthError):
        token_info = None

    if token_info is not None:
        return

    if not interactive:
        raise SpotifyAuthenticationRequiredError(AUTH_REQUIRED_MESSAGE)

    if not typer.confirm("Spotify authorization required. Log in now?", default=True):
        raise SpotifyAuthenticationRequiredError(AUTH_REQUIRED_MESSAGE)

    manager.get_access_token(check_cache=False)
