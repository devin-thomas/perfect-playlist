import os
from datetime import UTC, datetime

import pytest

from perfect_playlist import create_playlist_from_file
from perfect_playlist.client import get_spotify_client

RUN_INTEGRATION = os.getenv("PERFECT_PLAYLIST_RUN_INTEGRATION_TESTS") == "1"
@pytest.mark.skipif(
    not RUN_INTEGRATION,
    reason="Set PERFECT_PLAYLIST_RUN_INTEGRATION_TESTS=1 to run Spotify integration tests.",
)
def test_create_private_playlist_from_example_and_verify_order() -> None:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    name = f"perfect-playlist integration test - DELETE ME - {timestamp}"
    result = create_playlist_from_file(
        name,
        "examples/paradox-tiny-desk.txt",
        public=False,
        verify=True,
    )

    assert result.playlist.url.startswith("https://open.spotify.com/playlist/")
    assert result.verified is True
    persisted = get_spotify_client().playlist(result.playlist.id, fields="public")
    assert persisted["public"] is False
