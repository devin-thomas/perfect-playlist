from collections.abc import Sequence

import pytest

from perfect_playlist.errors import PlaylistRepairError
from perfect_playlist.repair import repair_playlist


def _uri(index: int) -> str:
    return f"spotify:track:{index:022d}"


class RepairClient:
    def __init__(self, actual: list[str]) -> None:
        self.actual = actual
        self.replacements: list[tuple[str, list[str]]] = []

    def playlist_items(
        self, playlist_id: str, fields: str, limit: int, offset: int
    ) -> dict[str, object]:
        page = self.actual[offset : offset + limit]
        return {"items": [{"track": {"uri": uri}} for uri in page], "next": None}

    def playlist_replace_all_items(
        self, playlist_id: str, items: Sequence[str]
    ) -> dict[str, str]:
        self.replacements.append((playlist_id, list(items)))
        return {"snapshot_id": "snapshot-repaired"}


def test_repair_defaults_to_dry_run_and_reports_difference() -> None:
    client = RepairClient([_uri(1), _uri(3)])

    result = repair_playlist("playlist-123", [_uri(1), _uri(2)], client=client)

    assert result.changed is True
    assert result.applied is False
    assert client.replacements == []


def test_repair_apply_replaces_playlist_in_exact_order() -> None:
    client = RepairClient([_uri(1), _uri(3)])

    result = repair_playlist(
        "playlist-123", [_uri(1), _uri(2)], dry_run=False, client=client
    )

    assert result.applied is True
    assert result.snapshot_id == "snapshot-repaired"
    assert client.replacements == [("playlist-123", [_uri(1), _uri(2)])]


def test_repair_does_not_write_when_playlist_already_matches() -> None:
    client = RepairClient([_uri(1), _uri(2)])

    result = repair_playlist(
        "playlist-123", [_uri(1), _uri(2)], dry_run=False, client=client
    )

    assert result.changed is False
    assert result.applied is False
    assert client.replacements == []


def test_repair_rejects_apply_over_100_tracks() -> None:
    client = RepairClient([])

    with pytest.raises(PlaylistRepairError, match="limited to 100 tracks"):
        repair_playlist(
            "playlist-123",
            [_uri(index) for index in range(101)],
            dry_run=False,
            client=client,
        )
