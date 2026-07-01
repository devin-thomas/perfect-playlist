from typer.testing import CliRunner

from spotify_exact.cli import app


def test_cli_help() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Create Spotify playlists from exact track URIs" in result.output

