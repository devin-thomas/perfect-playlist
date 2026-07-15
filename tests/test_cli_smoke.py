from pathlib import Path

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
    if arguments[0] in {"build", "add"}:
        assert "No Spotify or filesystem changes were made" not in result.output
    else:
        assert "No Spotify or filesystem changes were made" in " ".join(result.output.split())


def test_export_help_includes_the_approved_links_option() -> None:
    result = CliRunner().invoke(app, ["export", "--help"])

    assert result.exit_code == 0
    assert "--links" in result.output


def test_add_requires_target() -> None:
    result = CliRunner().invoke(app, ["add", "tracks.txt"])

    assert result.exit_code == 2
    assert "--target" in result.output


def test_verify_requires_two_sources() -> None:
    result = CliRunner().invoke(app, ["verify", "left.txt"])

    assert result.exit_code == 2
    assert "Missing argument" in result.output


def test_verify_reports_exact_match_and_empty_sources(tmp_path: Path) -> None:
    left = tmp_path / "left.txt"
    right = tmp_path / "right.txt"
    left.write_text("spotify:track:354WZaV3u6cuzTG2PmpYwm\n", encoding="utf-8")
    right.write_text("spotify:track:354WZaV3u6cuzTG2PmpYwm\n", encoding="utf-8")

    result = CliRunner().invoke(app, ["verify", str(left), str(right)])

    assert result.exit_code == 0
    assert "Verified: both sources contain 1 tracks and they all match." in result.output


def test_verify_reports_empty_to_empty_success(tmp_path: Path) -> None:
    left = tmp_path / "left.txt"
    right = tmp_path / "right.txt"
    left.write_text("", encoding="utf-8")
    right.write_text("", encoding="utf-8")

    result = CliRunner().invoke(app, ["verify", str(left), str(right)])

    assert result.exit_code == 0
    assert "Verified: both sources contain 0 tracks and they all match." in result.output


def test_verify_reports_only_count_diagnostics(tmp_path: Path) -> None:
    left = tmp_path / "left.txt"
    right = tmp_path / "right.txt"
    left.write_text("spotify:track:354WZaV3u6cuzTG2PmpYwm\n", encoding="utf-8")
    right.write_text("", encoding="utf-8")

    result = CliRunner().invoke(app, ["verify", str(left), str(right)])

    assert result.exit_code == 1
    assert result.output.splitlines() == [
        "Not verified: track counts differ.",
        "left.txt: 1",
        "right.txt: 0",
    ]


def test_verify_reports_only_first_positional_difference(tmp_path: Path) -> None:
    left = tmp_path / "left.txt"
    right = tmp_path / "right.txt"
    left.write_text(
        "spotify:track:354WZaV3u6cuzTG2PmpYwm\n"
        "spotify:track:78APbsosmvDYIwZHjzC5ZE\n",
        encoding="utf-8",
    )
    right.write_text(
        "spotify:track:354WZaV3u6cuzTG2PmpYwm\n"
        "spotify:track:3REnVcPtMXDxR4g8sZ4QtM\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(app, ["verify", str(left), str(right)])

    assert result.exit_code == 1
    assert result.output.splitlines() == [
        "Not verified at position 2.",
        "left.txt: spotify:track:78APbsosmvDYIwZHjzC5ZE",
        "right.txt: spotify:track:3REnVcPtMXDxR4g8sZ4QtM",
    ]


def test_build_rejects_name_and_target_together() -> None:
    result = CliRunner().invoke(
        app,
        ["build", "tracks.txt", "--name", "Name", "--target", "spotify:playlist:123"],
    )

    assert result.exit_code == 2
    assert "--name and --target cannot be used together" in result.output


def test_non_interactive_private_build_requires_target() -> None:
    result = CliRunner().invoke(app, ["build", "tracks.txt", "--private"])

    assert result.exit_code == 2
    assert "Non-interactive private builds require --target" in result.output


def test_build_rejects_private_name_combination() -> None:
    result = CliRunner().invoke(app, ["build", "tracks.txt", "--private", "--name", "Name"])

    assert result.exit_code == 2
    assert "--private and --name cannot be used together" in result.output
