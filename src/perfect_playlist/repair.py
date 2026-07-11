from __future__ import annotations

from collections.abc import Sequence

from .client import SPOTIFY_API_EXCEPTIONS, PlaylistClient, get_spotify_client
from .errors import PlaylistRepairError
from .models import PlaylistRepairResult
from .track_refs import normalize_track_ref
from .verify import get_playlist_track_uris

MAX_REPLACE_ITEMS = 100


def repair_playlist(
    playlist_id: str,
    expected_uris: Sequence[str],
    *,
    dry_run: bool = True,
    client: PlaylistClient | None = None,
) -> PlaylistRepairResult:
    """Plan or apply an exact replacement of a playlist's track order."""
    expected = [normalize_track_ref(uri) for uri in expected_uris]
    actual = get_playlist_track_uris(playlist_id, client=client)
    changed = actual != expected

    if not changed or dry_run:
        return PlaylistRepairResult(
            playlist_id=playlist_id,
            expected_uris=expected,
            actual_uris=actual,
            changed=changed,
            applied=False,
        )

    if len(expected) > MAX_REPLACE_ITEMS:
        raise PlaylistRepairError(
            "Applying repair is limited to 100 tracks because Spotify's replace-items "
            "operation replaces the full playlist in one request."
        )

    sp = client or get_spotify_client()
    try:
        response = sp.playlist_replace_all_items(playlist_id, expected)
    except SPOTIFY_API_EXCEPTIONS as exc:
        raise PlaylistRepairError(
            f"Spotify rejected repair for playlist {playlist_id}."
        ) from exc

    return PlaylistRepairResult(
        playlist_id=playlist_id,
        expected_uris=expected,
        actual_uris=actual,
        changed=True,
        applied=True,
        snapshot_id=response.get("snapshot_id"),
    )
