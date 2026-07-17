import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from dotenv import load_dotenv

from perfect_playlist import (
    add_to_playlist,
    build_public_playlist,
    build_target_playlist,
    create_playlist_from_uris,
    read_source,
)
from perfect_playlist.client import get_spotify_client
from perfect_playlist.export import write_export
from perfect_playlist.models import TrackSequence
from perfect_playlist.playlist import create_empty_playlist
from perfect_playlist.verify import compare_track_sequences

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


@pytest.mark.skipif(
    not RUN_INTEGRATION,
    reason="Set PERFECT_PLAYLIST_RUN_INTEGRATION_TESTS=1 to run Spotify integration tests.",
)
def test_live_workflows_use_reversible_public_fixtures(tmp_path: Path) -> None:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    source = read_source("examples/paradox-tiny-desk.txt")
    public_name = f"perfect-playlist build - DELETE ME - {timestamp}"
    target_name = f"perfect-playlist target - DELETE ME - {timestamp}"
    built = None
    target = None
    try:
        built = build_public_playlist(source, name=public_name)
        assert read_source(built.playlist.uri) == source

        target = create_empty_playlist(target_name, public=True)
        target_result = build_target_playlist(source, target.uri)
        target_source = read_source(target_result.playlist.uri)
        assert compare_track_sequences(source, target_source).matches

        appended = TrackSequence(uris=(source.uris[0],))
        added = add_to_playlist(appended, target.uri)
        assert added.added_uris == list(appended.uris)
        assert read_source(target.uri).uris[-1:] == appended.uris

        export_path = tmp_path / "live-target.yaml"
        write_export(target_source, export_path)
        assert read_source(export_path) == source
    finally:
        client = get_spotify_client()
        if built is not None:
            client.current_user_unfollow_playlist(built.playlist.id)
        if target is not None:
            client.current_user_unfollow_playlist(target.id)
