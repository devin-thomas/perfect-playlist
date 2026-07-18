import os
from pathlib import Path
from typing import Any

import pytest
from requests import RequestException
from spotipy.exceptions import SpotifyException
from typer.testing import CliRunner

import perfect_playlist.auth as auth_module
from perfect_playlist.auth import AUTH_REQUIRED_MESSAGE, authenticate, build_auth_manager
from perfect_playlist.cli import app
from perfect_playlist.errors import AuthConfigError, SpotifyAuthenticationRequiredError


def test_build_auth_manager_reports_missing_env_without_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(auth_module, "SPOTIFY_SECRETS_FILE", tmp_path / "missing.env")
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
    for name in ("SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET", "SPOTIPY_REDIRECT_URI"):
        monkeypatch.delenv(name, raising=False)
    resources = tmp_path / "resources"
    resources.mkdir()
    secrets_file = resources / "spotify-secrets.env"
    secrets_file.write_text(
        "SPOTIPY_CLIENT_ID=client-id\n"
        "SPOTIPY_CLIENT_SECRET=client-secret\n"
        "SPOTIPY_REDIRECT_URI=http://127.0.0.1:4202\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(auth_module, "SPOTIFY_SECRETS_FILE", secrets_file)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    build_auth_manager(cache_path=str(tmp_path / "token-cache.json"), open_browser=False)

    assert os.getenv("SPOTIPY_CLIENT_ID") == "client-id"


def test_build_auth_manager_loads_configured_spotify_secrets_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    for name in ("SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET", "SPOTIPY_REDIRECT_URI"):
        monkeypatch.delenv(name, raising=False)
    secrets_file = tmp_path / "spotify-secrets.env"
    secrets_file.write_text(
        "SPOTIPY_CLIENT_ID=client-id\n"
        "SPOTIPY_CLIENT_SECRET=client-secret\n"
        "SPOTIPY_REDIRECT_URI=http://127.0.0.1:4202\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PERFECT_PLAYLIST_SECRETS_FILE", str(secrets_file))

    build_auth_manager(cache_path=str(tmp_path / "token-cache.json"), open_browser=False)

    assert os.getenv("SPOTIPY_CLIENT_ID") == "client-id"


def test_build_auth_manager_maps_token_cache_filesystem_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("SPOTIPY_CLIENT_ID", "client-id")
    monkeypatch.setenv("SPOTIPY_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:4202")
    blocked_parent = tmp_path / "blocked"
    blocked_parent.write_text("not a directory", encoding="utf-8")

    with pytest.raises(AuthConfigError, match="token cache directory"):
        build_auth_manager(
            cache_path=str(blocked_parent / "token-cache.json"),
            open_browser=False,
        )


class FakeCache:
    def __init__(self, token: dict[str, Any] | None) -> None:
        self.token = token

    def get_cached_token(self) -> dict[str, Any] | None:
        return self.token


class FakeManager:
    def __init__(self, token: dict[str, Any] | None) -> None:
        self.cache_handler = FakeCache(token)
        self.access_token_calls = 0

    def validate_token(self, token: dict[str, Any] | None) -> dict[str, Any] | None:
        return token

    def get_access_token(self, *, check_cache: bool) -> dict[str, str]:
        assert check_cache is False
        self.access_token_calls += 1
        return {"access_token": "redacted"}


def test_authenticate_uses_valid_cache_without_prompt() -> None:
    manager = FakeManager({"access_token": "redacted"})

    authenticate(manager, interactive=False)

    assert manager.access_token_calls == 0


def test_authenticate_rejects_missing_cache_non_interactively() -> None:
    manager = FakeManager(None)

    with pytest.raises(SpotifyAuthenticationRequiredError, match=AUTH_REQUIRED_MESSAGE):
        authenticate(manager, interactive=False)


def test_authenticate_converts_refresh_network_failure_to_auth_error() -> None:
    class FailingManager(FakeManager):
        def validate_token(
            self, token: dict[str, Any] | None
        ) -> dict[str, Any] | None:
            raise RequestException("network unavailable")

    manager = FailingManager({"access_token": "expired", "refresh_token": "redacted"})

    with pytest.raises(SpotifyAuthenticationRequiredError, match=AUTH_REQUIRED_MESSAGE):
        authenticate(manager, interactive=False)


def test_authenticate_prompts_and_resumes_interactively(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = FakeManager(None)
    monkeypatch.setattr("perfect_playlist.auth.typer.confirm", lambda *args, **kwargs: True)

    authenticate(manager, interactive=True)

    assert manager.access_token_calls == 1


def test_auth_login_does_not_force_interactive_browser_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[bool | None] = []

    class FakeClient:
        def current_user(self) -> dict[str, str]:
            return {"id": "listener"}

    def fake_client(*, interactive: bool | None = None) -> FakeClient:
        calls.append(interactive)
        return FakeClient()

    monkeypatch.setattr("perfect_playlist.client.get_spotify_client", fake_client)

    result = CliRunner().invoke(app, ["auth", "login"])

    assert result.exit_code == 0
    assert calls == [None]


def test_cli_does_not_render_raw_spotify_error_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingClient:
        def current_user(self) -> dict[str, str]:
            raise SpotifyException(401, -1, "vendor-sensitive-detail")

    monkeypatch.setattr(
        "perfect_playlist.client.get_spotify_client",
        lambda *, interactive=None: FailingClient(),
    )

    result = CliRunner().invoke(app, ["auth", "status"])

    assert result.exit_code == 2
    assert "Spotify request failed." in result.output
    assert "vendor-sensitive-detail" not in result.output
