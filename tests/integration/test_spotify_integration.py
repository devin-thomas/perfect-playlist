import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from dotenv import load_dotenv

from perfect_playlist import create_playlist_from_uris, read_source
from perfect_playlist.client import get_spotify_client

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=REPOSITORY_ROOT / "resources/spotify-secrets.env")
RUN_INTEGRATION = os.getenv("PERFECT_PLAYLIST_RUN_INTEGRATION_TESTS") == "1"


@pytest.mark.skipif(
    not RUN_INTEGRATION,
    reason="Set PERFECT_PLAYLIST_RUN_INTEGRATION_TESTS=1 to run Spotify integration tests.",
)
def test_create_public_playlist_from_example_and_verify_order() -> None:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    name = f"perfect-playlist integration test - DELETE ME - {timestamp}"
    result = None
    try:
        sequence = read_source("examples/paradox-tiny-desk.txt")
        result = create_playlist_from_uris(name, sequence.uris, public=True)

        assert result.playlist.url.startswith("https://open.spotify.com/playlist/")
        assert read_source(result.playlist.uri) == sequence
        persisted = get_spotify_client().playlist(result.playlist.id, fields="public")
        assert persisted["public"] is True
    finally:
        if result is not None:
            get_spotify_client().current_user_unfollow_playlist(result.playlist.id)
