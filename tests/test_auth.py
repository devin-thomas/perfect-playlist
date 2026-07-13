import os
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


def test_build_auth_manager_creates_token_cache_parent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("SPOTIPY_CLIENT_ID", "client-id")
    monkeypatch.setenv("SPOTIPY_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:4202")
    cache_path = tmp_path / "missing" / "token-cache.json"

    build_auth_manager(cache_path=str(cache_path), open_browser=False)

    assert cache_path.parent.is_dir()


def test_build_auth_manager_loads_repository_spotify_secrets_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    for name in ("SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET", "SPOTIPY_REDIRECT_URI"):
        monkeypatch.delenv(name, raising=False)
    resources = tmp_path / "resources"
    resources.mkdir()
    (resources / "spotify-secrets.env").write_text(
        "SPOTIPY_CLIENT_ID=client-id\n"
        "SPOTIPY_CLIENT_SECRET=client-secret\n"
        "SPOTIPY_REDIRECT_URI=http://127.0.0.1:4202\n",
        encoding="utf-8",
    )

    build_auth_manager(cache_path=str(tmp_path / "token-cache.json"), open_browser=False)

    assert os.getenv("SPOTIPY_CLIENT_ID") == "client-id"
