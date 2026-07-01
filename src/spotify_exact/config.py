from __future__ import annotations

import os
from pathlib import Path

from platformdirs import user_cache_dir


def default_token_cache_path() -> Path:
    """Return the configured or platform-default OAuth token cache path."""
    configured = os.getenv("SPOTIFY_EXACT_TOKEN_CACHE")
    if configured:
        return Path(configured).expanduser()
    return Path(user_cache_dir("spotify-exact", "spotify-exact")) / "token-cache.json"

