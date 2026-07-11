from pathlib import Path
from typing import Any

from perfect_playlist.resolve import resolve_setlist

TRACK_A = "spotify:track:354WZaV3u6cuzTG2PmpYwm"
TRACK_B = "spotify:track:78APbsosmvDYIwZHjzC5ZE"


def _summary(uri: str, title: str, artists: list[str]) -> dict[str, Any]:
    return {
        "uri": uri,
        "name": title,
        "artists": [{"name": artist} for artist in artists],
        "external_urls": {"spotify": f"https://open.spotify.com/track/{uri.rsplit(':', 1)[1]}"},
        "album": {"name": "Album"},
        "duration_ms": 120000,
        "explicit": False,
    }


class SearchClient:
    def __init__(self, responses: dict[str, list[dict[str, Any]]]) -> None:
        self.responses = responses
        self.queries: list[str] = []

    def search(
        self, q: str, type: str, limit: int, market: str | None = None
    ) -> dict[str, Any]:
        self.queries.append(q)
        return {"tracks": {"items": self.responses[q]}}


def test_resolve_selects_one_exact_match_and_marks_ambiguous_tracks(tmp_path: Path) -> None:
    source = tmp_path / "setlist.yaml"
    output = tmp_path / "resolved.yaml"
    source.write_text(
        """
        name: Setlist
        tracks:
          - title: First Song
            artist: Artist
          - title: Unclear Song
            artist: Artist
        """,
        encoding="utf-8",
    )
    client = SearchClient(
        {
            'track:"First Song" artist:"Artist"': [_summary(TRACK_A, "First Song", ["Artist"])],
            'track:"Unclear Song" artist:"Artist"': [
                _summary(TRACK_A, "Unclear Song", ["Artist"]),
                _summary(TRACK_B, "Unclear Song", ["Artist"]),
            ],
        }
    )

    manifest = resolve_setlist(source, output, client=client)

    assert manifest.tracks[0].uri == TRACK_A
    assert manifest.tracks[0].needs_review is False
    assert manifest.tracks[0].confidence == 1.0
    assert manifest.tracks[1].needs_review is True
    assert manifest.tracks[1].uri is None
    assert manifest.tracks[1].confidence == 1.0
    assert manifest.tracks[1].candidate_uris == [TRACK_A, TRACK_B]
    assert manifest.uris == [TRACK_A]
    assert "needs_review: true" in output.read_text(encoding="utf-8")
