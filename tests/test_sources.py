import json
from pathlib import Path

import pytest

from perfect_playlist.errors import SourceError
from perfect_playlist.io import read_source
from perfect_playlist.models import TrackSequence

TRACK_A = "spotify:track:354WZaV3u6cuzTG2PmpYwm"
TRACK_B = "spotify:track:78APbsosmvDYIwZHjzC5ZE"


@pytest.mark.parametrize("suffix", [".yaml", ".yml", ".json"])
def test_read_source_accepts_canonical_structured_shapes_and_ignores_extra_fields(
    tmp_path: Path, suffix: str
) -> None:
    source = tmp_path / f"tracks{suffix}"
    data = {
        "tracks": [
            TRACK_A,
            {
                "uri": f"https://open.spotify.com/track/{TRACK_B.rsplit(':', 1)[1]}",
                "title": "ignored",
            },
            TRACK_A,
        ],
        "name": "ignored",
    }
    if suffix == ".json":
        source.write_text(json.dumps(data), encoding="utf-8")
    else:
        source.write_text(
            "tracks:\n  - " + TRACK_A + "\n  - uri: https://open.spotify.com/track/"
            + TRACK_B.rsplit(":", 1)[1] + "\n    title: ignored\n  - " + TRACK_A + "\n"
            + "name: ignored\n",
            encoding="utf-8",
        )

    assert read_source(source) == TrackSequence(uris=(TRACK_A, TRACK_B, TRACK_A))


def test_read_source_accepts_text_comments_and_blank_lines(tmp_path: Path) -> None:
    source = tmp_path / "tracks.txt"
    source.write_text(f"# comment\n\n{TRACK_A}\n{TRACK_B}\n{TRACK_A}\n", encoding="utf-8")

    assert read_source(source).uris == (TRACK_A, TRACK_B, TRACK_A)


@pytest.mark.parametrize("filename", ["tracks", "tracks.csv"])
def test_read_source_rejects_missing_or_unsupported_extension(
    tmp_path: Path, filename: str
) -> None:
    source = tmp_path / filename
    source.write_text("tracks: []", encoding="utf-8")

    with pytest.raises(SourceError, match="supported extensions"):
        read_source(source)


@pytest.mark.parametrize(
    ("suffix", "contents", "message"),
    [
        (".json", "{", "Could not parse Source"),
        (".yaml", "tracks: [", "Could not parse Source"),
        (".json", "[]", "top-level tracks array"),
        (".json", '{"tracks": ["not-a-track"]}', r"uris\[0\]"),
        (".yaml", "tracks:\n  - title: missing uri\n", r"tracks\[0\]"),
        (".txt", "not-a-track", "Line 1"),
    ],
)
def test_read_source_rejects_malformed_or_invalid_content(
    tmp_path: Path, suffix: str, contents: str, message: str
) -> None:
    source = tmp_path / f"tracks{suffix}"
    source.write_text(contents, encoding="utf-8")

    with pytest.raises(SourceError, match=message):
        read_source(source)
