from pathlib import Path

from perfect_playlist.io import read_uri_lines


def test_read_uri_lines_preserves_order_and_duplicates(tmp_path: Path) -> None:
    track_a = "spotify:track:354WZaV3u6cuzTG2PmpYwm"
    track_b = "https://open.spotify.com/track/78APbsosmvDYIwZHjzC5ZE?si=abc123"
    source = tmp_path / "tracks.txt"
    source.write_text(
        f"# comment\n\n{track_a}\n{track_b}\n{track_a}\n",
        encoding="utf-8",
    )

    assert read_uri_lines(source) == [
        track_a,
        "spotify:track:78APbsosmvDYIwZHjzC5ZE",
        track_a,
    ]

