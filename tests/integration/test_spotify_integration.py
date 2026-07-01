import os
from datetime import UTC, datetime

import pytest

from spotify_exact import create_playlist_from_file

RUN_INTEGRATION = os.getenv("SPOTIFY_EXACT_RUN_INTEGRATION_TESTS") == "1"
REQUIRED_ENV = (
    "SPOTIPY_CLIENT_ID",
    "SPOTIPY_CLIENT_SECRET",
    "SPOTIPY_REDIRECT_URI",
)


@pytest.mark.skipif(
    not RUN_INTEGRATION,
    reason="Set SPOTIFY_EXACT_RUN_INTEGRATION_TESTS=1 to run Spotify integration tests.",
)
def test_create_private_playlist_from_example_and_verify_order() -> None:
    missing = [name for name in REQUIRED_ENV if not os.getenv(name)]
    if missing:
        pytest.fail(f"Missing Spotify integration environment variables: {', '.join(missing)}")

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    name = f"spotify-exact integration test - DELETE ME - {timestamp}"
    result = create_playlist_from_file(
        name,
        "examples/paradox-tiny-desk.txt",
        public=False,
        verify=True,
    )

    assert result.playlist.url.startswith("https://open.spotify.com/playlist/")
    assert result.verified is True
