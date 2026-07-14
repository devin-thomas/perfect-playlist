import pytest
from typer.testing import CliRunner

from perfect_playlist.cli import app


def test_cli_help_exposes_only_action_commands() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("build", "add", "verify", "export", "search", "inspect", "auth"):
        assert command in result.output
    for legacy in ("playlist", "track", "resolve"):
        assert f"│ {legacy} " not in result.output


def test_auth_help_exposes_only_login_and_status() -> None:
    result = CliRunner().invoke(app, ["auth", "--help"])
    assert result.exit_code == 0
    assert "login" in result.output
    assert "status" in result.output


@pytest.mark.parametrize(
    ("arguments", "parent"),
    [
        (["build", "tracks.txt"], "Source"),
        (["add", "tracks.txt", "--target", "spotify:playlist:123"], "Parent 2"),
        (["verify", "left.txt", "right.txt"], "Parent 2"),
        (["export", "tracks.txt"], "Parent 2"),
        (["search", "query"], "Parent 3"),
        (["inspect", "spotify:track:123"], "Parent 3"),
    ],
)
def test_successor_commands_fail_closed_until_their_parent_starts(
    arguments: list[str], parent: str
) -> None:
    result = CliRunner().invoke(app, arguments)

    assert result.exit_code == 2
    assert parent in result.output
    if arguments[0] == "build":
        assert "No Spotify or filesystem changes were made" not in result.output
    else:
        assert "No Spotify or filesystem changes were made" in " ".join(result.output.split())


def test_export_help_includes_the_approved_links_option() -> None:
    result = CliRunner().invoke(app, ["export", "--help"])

    assert result.exit_code == 0
    assert "--links" in result.output
