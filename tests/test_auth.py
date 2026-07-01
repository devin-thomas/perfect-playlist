from pathlib import Path

import pytest

from perfect_playlist.auth import build_auth_manager
from perfect_playlist.errors import AuthConfigError


def test_build_auth_manager_reports_missing_env_without_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    for name in ("SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET", "SPOTIPY_REDIRECT_URI"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(AuthConfigError) as exc_info:
        build_auth_manager(open_browser=False)

    message = str(exc_info.value)
    assert "SPOTIPY_CLIENT_ID" in message
    assert "SPOTIPY_CLIENT_SECRET" in message
    assert "SPOTIPY_REDIRECT_URI" in message
    assert "=" not in message
