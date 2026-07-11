from pathlib import Path

import pytest

from perfect_playlist.errors import ManifestError
from perfect_playlist.io import read_manifest


def test_read_manifest_keeps_metadata_and_excludes_missing_tracks(tmp_path: Path) -> None:
    source = tmp_path / "playlist.yaml"
    source.write_text(
        """
        name: Setlist
        public: false
        description: Exact setlist
        tracks:
          - title: First
            artist: Artist
            uri: spotify:track:354WZaV3u6cuzTG2PmpYwm
          - title: Unavailable
            artist: Artist
            missing: true
            note: Not released in this market.
          - title: Second
            artist: Artist
            uri: https://open.spotify.com/track/78APbsosmvDYIwZHjzC5ZE?si=abc
        """,
        encoding="utf-8",
    )

    manifest = read_manifest(source)

    assert manifest.name == "Setlist"
    assert manifest.public is False
    assert manifest.description == "Exact setlist"
    assert manifest.uris == [
        "spotify:track:354WZaV3u6cuzTG2PmpYwm",
        "spotify:track:78APbsosmvDYIwZHjzC5ZE",
    ]
    assert manifest.tracks[1].missing is True


def test_read_manifest_rejects_track_without_uri_or_missing_flag(tmp_path: Path) -> None:
    source = tmp_path / "playlist.yaml"
    source.write_text(
        """
        name: Invalid
        tracks:
          - title: Unknown
            artist: Artist
        """,
        encoding="utf-8",
    )

    with pytest.raises(ManifestError, match="must include uri or set missing: true"):
        read_manifest(source)


def test_read_manifest_rejects_uri_marked_missing(tmp_path: Path) -> None:
    source = tmp_path / "playlist.yaml"
    source.write_text(
        """
        name: Invalid
        tracks:
          - title: Track
            artist: Artist
            uri: spotify:track:354WZaV3u6cuzTG2PmpYwm
            missing: true
        """,
        encoding="utf-8",
    )

    with pytest.raises(ManifestError, match="cannot include uri when missing: true"):
        read_manifest(source)
