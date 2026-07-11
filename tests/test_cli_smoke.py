from pathlib import Path

import pytest
from typer.testing import CliRunner

from perfect_playlist.cli import app
from perfect_playlist.models import PlaylistManifest, PlaylistManifestTrack, TrackSummary


def test_cli_help() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Create Spotify playlists from exact track URIs" in result.output


def test_playlist_create_dry_run(tmp_path: Path) -> None:
    source = tmp_path / "tracks.txt"
    source.write_text("spotify:track:354WZaV3u6cuzTG2PmpYwm\n", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "playlist",
            "create",
            "Dry Run",
            "--from",
            str(source),
            "--private",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "1 tracks validated" in result.output
    assert "spotify:track:354WZaV3u6cuzTG2PmpYwm" in result.output


def test_playlist_create_from_manifest_dry_run(tmp_path: Path) -> None:
    source = tmp_path / "playlist.yaml"
    source.write_text(
        """
        name: Manifest playlist
        tracks:
          - title: First
            artist: Artist
            uri: spotify:track:354WZaV3u6cuzTG2PmpYwm
          - title: Missing
            artist: Artist
            missing: true
        """,
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        ["playlist", "create", "--manifest", str(source), "--dry-run"],
    )

    assert result.exit_code == 0
    assert "1 tracks validated" in result.output


def test_playlist_create_rejects_manifest_needing_review(tmp_path: Path) -> None:
    source = tmp_path / "needs-review.yaml"
    source.write_text(
        """
        name: Review first
        tracks:
          - title: Ambiguous
            artist: Artist
            needs_review: true
            candidate_uris:
              - spotify:track:354WZaV3u6cuzTG2PmpYwm
        """,
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        ["playlist", "create", "--manifest", str(source), "--dry-run"],
    )

    assert result.exit_code == 2
    assert "1 track(s) still need review" in result.output


def test_resolve_setlist_json_output(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    output = tmp_path / "resolved.yaml"
    manifest = PlaylistManifest(
        name="Setlist",
        tracks=[
            PlaylistManifestTrack(
                title="First",
                artist="Artist",
                uri="spotify:track:354WZaV3u6cuzTG2PmpYwm",
            )
        ],
    )
    monkeypatch.setattr("perfect_playlist.cli.resolve_setlist", lambda *args: manifest)

    result = CliRunner().invoke(
        app,
        ["resolve", "setlist", "setlist.yaml", "--out", str(output), "--json"],
    )

    assert result.exit_code == 0
    assert '"name": "Setlist"' in result.output
    assert '"needs_review": false' in result.output


def test_search_track_json(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_search_tracks(query: str, *, limit: int, market: str | None) -> list[TrackSummary]:
        assert query == 'track:"Get The Message"'
        assert limit == 1
        assert market == "US"
        return [
            TrackSummary(
                uri="spotify:track:354WZaV3u6cuzTG2PmpYwm",
                url="https://open.spotify.com/track/354WZaV3u6cuzTG2PmpYwm",
                title="Get The Message",
                artists=["The Paradox"],
            )
        ]

    monkeypatch.setattr("perfect_playlist.cli.search_tracks", fake_search_tracks)

    result = CliRunner().invoke(
        app,
        ["search", "track", 'track:"Get The Message"', "--limit", "1", "--json"],
    )

    assert result.exit_code == 0
    assert '"title": "Get The Message"' in result.output
    assert '"uri": "spotify:track:354WZaV3u6cuzTG2PmpYwm"' in result.output


def test_track_show_json(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get_tracks(uris: list[str], *, market: str | None) -> list[TrackSummary]:
        assert uris == ["spotify:track:354WZaV3u6cuzTG2PmpYwm"]
        assert market == "US"
        return [
            TrackSummary(
                uri=uris[0],
                url="https://open.spotify.com/track/354WZaV3u6cuzTG2PmpYwm",
                title="Get The Message",
                artists=["The Paradox"],
            )
        ]

    monkeypatch.setattr("perfect_playlist.cli.get_tracks", fake_get_tracks)

    result = CliRunner().invoke(
        app,
        ["track", "show", "https://open.spotify.com/track/354WZaV3u6cuzTG2PmpYwm", "--json"],
    )

    assert result.exit_code == 0
    assert '"title": "Get The Message"' in result.output
