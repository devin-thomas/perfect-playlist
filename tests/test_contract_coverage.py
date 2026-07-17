from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from perfect_playlist.cli import app
from perfect_playlist.io import read_source
from perfect_playlist.models import (
    CreatedPlaylist,
    PlaylistAddResult,
    PlaylistCreateResult,
    TrackSequence,
)
from perfect_playlist.playlist import build_public_playlist


def track_uri(index: int) -> str:
    return f"spotify:track:{index:022d}"


class PagedPlaylistClient:
    """Typed offline fake that exposes both Spotify pagination boundaries."""

    def __init__(self, pages: list[list[dict[str, object]]]) -> None:
        self.pages = pages
        self.playlist_offsets: list[int] = []
        self.created: list[dict[str, object]] = []
        self.added: list[list[str]] = []

    def current_user(self) -> dict[str, object]:
        return {"id": "user-123"}

    def current_user_playlists(self, limit: int, offset: int) -> dict[str, object]:
        assert limit == 50
        page_index = offset // limit
        self.playlist_offsets.append(offset)
        return {
            "items": self.pages[page_index],
            "next": "next" if page_index + 1 < len(self.pages) else None,
        }

    def current_user_playlist_create(
        self,
        name: str,
        public: bool,
        collaborative: bool = False,
        description: str = "",
    ) -> dict[str, object]:
        self.created.append(
            {
                "name": name,
                "public": public,
                "collaborative": collaborative,
                "description": description,
            }
        )
        return {
            "id": "playlist-123",
            "uri": "spotify:playlist:playlist-123",
            "name": name,
            "external_urls": {"spotify": "https://open.spotify.com/playlist/playlist-123"},
        }

    def playlist(self, playlist_id: str, fields: str) -> dict[str, object]:
        return {"id": playlist_id, "public": True}

    def playlist_add_items(self, playlist_id: str, items: Sequence[str]) -> dict[str, Any]:
        self.added.append(list(items))
        return {"snapshot_id": "snapshot-1"}

    def playlist_items(
        self, playlist_id: str, fields: str, limit: int, offset: int
    ) -> dict[str, object]:
        return {"items": [{"track": {"uri": track_uri(1)}}], "next": None}


def test_source_playlist_reads_exact_100_item_page_boundary() -> None:
    class SourceClient:
        def __init__(self) -> None:
            self.calls: list[int] = []

        def playlist_items(
            self, playlist_id: str, fields: str, limit: int, offset: int
        ) -> dict[str, object]:
            self.calls.append(offset)
            if offset == 0:
                return {
                    "items": [{"track": {"uri": track_uri(i)}} for i in range(100)],
                    "next": "next",
                }
            return {"items": [{"track": {"uri": track_uri(100)}}], "next": None}

        def track(self, track_id: str, market: str | None = None) -> dict[str, object]:
            raise AssertionError("playlist Source must not resolve a track individually")

    client = SourceClient()
    result = read_source("spotify:playlist:1234567890123456789012", client=client)

    assert result.uris == tuple(track_uri(i) for i in range(101))
    assert client.calls == [0, 100]


def test_build_owned_name_scan_reads_multiple_pages_before_creating() -> None:
    client = PagedPlaylistClient(
        [
            [{"name": f"Existing {i}", "owner": {"id": "user-123"}} for i in range(50)],
            [{"name": "My Perfect Playlist", "owner": {"id": "user-123"}}],
        ]
    )
    result = build_public_playlist(TrackSequence(uris=(track_uri(1),)), client=client)

    assert result.playlist.name == "My Perfect Playlist (1)"
    assert client.playlist_offsets == [0, 50]


def test_cli_build_and_add_render_contract_success_messages() -> None:
    playlist = CreatedPlaylist(
        id="playlist-123",
        uri="spotify:playlist:playlist-123",
        url="https://open.spotify.com/playlist/playlist-123",
        name="Exact",
        snapshot_id="snapshot-1",
    )
    sequence = TrackSequence(uris=(track_uri(1), track_uri(2)))

    with patch("perfect_playlist.cli.read_source", return_value=sequence):
        with patch(
            "perfect_playlist.cli.build_public_playlist",
            return_value=PlaylistCreateResult(playlist=playlist, added_uris=list(sequence.uris)),
        ):
            build_result = CliRunner().invoke(app, ["build", "tracks.txt", "--name", "Exact"])

        with patch(
            "perfect_playlist.cli.add_to_playlist",
            return_value=PlaylistAddResult(playlist=playlist, added_uris=list(sequence.uris)),
        ):
            add_result = CliRunner().invoke(
                app, ["add", "tracks.txt", "--target", "spotify:playlist:playlist-123"]
            )

    assert build_result.exit_code == 0
    assert " ".join(build_result.output.split()) == (
        'Built and verified "Exact" with 2 tracks: '
        "https://open.spotify.com/playlist/playlist-123"
    )
    assert add_result.exit_code == 0
    assert " ".join(add_result.output.split()) == (
        'Added and verified 2 tracks in "Exact": '
        "https://open.spotify.com/playlist/playlist-123"
    )


@pytest.mark.parametrize(
    "arguments",
    [
        ["build", "tracks.txt", "--dry-run"],
        ["add", "tracks.txt", "--position", "1", "--target", "spotify:playlist:playlist-123"],
        ["verify", "left.txt", "right.txt", "--prefix"],
        ["repair", "tracks.txt"],
    ],
)
def test_legacy_commands_and_options_are_removed(arguments: list[str]) -> None:
    result = CliRunner().invoke(app, arguments)

    assert result.exit_code != 0
    assert "No such command" in result.output or "No such option" in result.output
