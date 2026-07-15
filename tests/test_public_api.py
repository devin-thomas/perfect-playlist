from pathlib import Path

from perfect_playlist import (
    ExportError,
    PlaylistAddError,
    PlaylistCreateError,
    SourceVerificationResult,
    TrackSequence,
    compare_track_sequences,
    serialize,
    track_links,
    write_export,
)

TRACK_A = "spotify:track:354WZaV3u6cuzTG2PmpYwm"
TRACK_B = "spotify:track:78APbsosmvDYIwZHjzC5ZE"


def test_root_api_exposes_typed_workflow_surfaces() -> None:
    sequence = TrackSequence(uris=(TRACK_A, TRACK_B))

    assert compare_track_sequences(sequence, sequence) == SourceVerificationResult(
        matches=True,
        left_count=2,
        right_count=2,
    )
    assert track_links(sequence) == [
        "https://open.spotify.com/track/354WZaV3u6cuzTG2PmpYwm",
        "https://open.spotify.com/track/78APbsosmvDYIwZHjzC5ZE",
    ]
    assert serialize(sequence, "json") == (
        '{\n  "tracks": [\n    "spotify:track:354WZaV3u6cuzTG2PmpYwm",\n'
        '    "spotify:track:78APbsosmvDYIwZHjzC5ZE"\n  ]\n}\n'
    )


def test_root_api_export_writes_canonical_sequence(tmp_path: Path) -> None:
    path = tmp_path / "tracks.json"

    write_export(TrackSequence(uris=(TRACK_A,)), path)

    assert path.exists()


def test_root_api_keeps_typed_failures_distinct() -> None:
    assert issubclass(PlaylistAddError, Exception)
    assert issubclass(PlaylistCreateError, Exception)
    assert issubclass(ExportError, Exception)
