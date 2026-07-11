from pathlib import Path
from typing import Any

from perfect_playlist.verify import export_playlist_to_file


class ExportClient:
    def __init__(self, uris: list[str]) -> None:
        self.uris = uris
        self.calls: list[dict[str, Any]] = []

    def playlist_items(
        self, playlist_id: str, fields: str, limit: int, offset: int
    ) -> dict[str, Any]:
        self.calls.append(
            {"playlist_id": playlist_id, "fields": fields, "limit": limit, "offset": offset}
        )
        page = self.uris[offset : offset + limit]
        return {
            "items": [{"track": {"uri": uri}} for uri in page],
            "next": "next" if offset == 0 and len(self.uris) > limit else None,
        }


def test_export_playlist_writes_ordered_uris(tmp_path: Path) -> None:
    uris = [
        "spotify:track:354WZaV3u6cuzTG2PmpYwm",
        "spotify:track:78APbsosmvDYIwZHjzC5ZE",
    ]
    output = tmp_path / "playlist.txt"

    exported = export_playlist_to_file("playlist-123", output, client=ExportClient(uris))

    assert exported == uris
    assert output.read_text(encoding="utf-8") == "\n".join(uris) + "\n"
