import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from perfect_playlist.cli import app
from perfect_playlist.errors import ExportError
from perfect_playlist.export import serialize, track_links, write_export
from perfect_playlist.io import read_source
from perfect_playlist.models import TrackSequence

TRACK_A = "spotify:track:354WZaV3u6cuzTG2PmpYwm"
TRACK_B = "spotify:track:78APbsosmvDYIwZHjzC5ZE"
SEQUENCE = TrackSequence(uris=(TRACK_A, TRACK_B, TRACK_A))


@pytest.mark.parametrize("suffix", [".yaml", ".yml", ".json", ".txt"])
def test_export_serializations_round_trip(tmp_path: Path, suffix: str) -> None:
    path = tmp_path / f"playlist{suffix}"
    write_export(SEQUENCE, path)

    assert read_source(path) == SEQUENCE


def test_links_are_text_only_and_render_web_urls() -> None:
    assert track_links(SEQUENCE) == [
        "https://open.spotify.com/track/354WZaV3u6cuzTG2PmpYwm",
        "https://open.spotify.com/track/78APbsosmvDYIwZHjzC5ZE",
        "https://open.spotify.com/track/354WZaV3u6cuzTG2PmpYwm",
    ]
    assert serialize(SEQUENCE, "txt", links=True) == (
        "https://open.spotify.com/track/354WZaV3u6cuzTG2PmpYwm\n"
        "https://open.spotify.com/track/78APbsosmvDYIwZHjzC5ZE\n"
        "https://open.spotify.com/track/354WZaV3u6cuzTG2PmpYwm\n"
    )


def test_json_export_is_canonical_track_array(tmp_path: Path) -> None:
    path = tmp_path / "playlist.json"
    write_export(SEQUENCE, path)

    assert json.loads(path.read_text(encoding="utf-8")) == {"tracks": list(SEQUENCE.uris)}


def test_explicit_output_never_overwrites(tmp_path: Path) -> None:
    path = tmp_path / "playlist.txt"
    path.write_text("keep me", encoding="utf-8")

    with pytest.raises(ExportError, match="File already exists"):
        write_export(SEQUENCE, path)

    assert path.read_text(encoding="utf-8") == "keep me"


@pytest.mark.parametrize("name", ["playlist", "playlist.csv"])
def test_output_requires_supported_extension(tmp_path: Path, name: str) -> None:
    with pytest.raises(ExportError, match="supported extensions"):
        write_export(SEQUENCE, tmp_path / name)


def test_links_can_only_be_saved_as_text(tmp_path: Path) -> None:
    with pytest.raises(ExportError, match="only be saved to a .txt"):
        write_export(SEQUENCE, tmp_path / "playlist.json", links=True)


def test_empty_export_fails_without_creating_file(tmp_path: Path) -> None:
    path = tmp_path / "playlist.txt"

    with pytest.raises(ExportError, match="empty TrackSequence"):
        write_export(TrackSequence(), path)

    assert not path.exists()


def test_cli_explicit_export_confirms_actual_count_and_path(tmp_path: Path) -> None:
    source = tmp_path / "tracks.txt"
    output = tmp_path / "playlist.txt"
    source.write_text(f"{TRACK_A}\n{TRACK_B}\n", encoding="utf-8")

    result = CliRunner().invoke(app, ["export", str(source), "--out", str(output)])

    assert result.exit_code == 0
    assert f"Exported 2 tracks to {output}." in result.output
    assert output.read_text(encoding="utf-8") == f"{TRACK_A}\n{TRACK_B}\n"


def test_cli_without_output_prints_and_does_not_save_non_interactively(tmp_path: Path) -> None:
    source = tmp_path / "tracks.txt"
    source.write_text(f"{TRACK_A}\n", encoding="utf-8")

    result = CliRunner().invoke(app, ["export", str(source)])

    assert result.exit_code == 0
    assert result.output == f"{TRACK_A}\n"
    assert list(tmp_path.iterdir()) == [source]


def test_cli_interactive_implicit_save_uses_collision_free_name(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "tracks.txt"
    source.write_text(f"{TRACK_A}\n", encoding="utf-8")
    (tmp_path / "playlist.yaml").write_text("existing", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("perfect_playlist.cli.command_is_interactive", lambda: True)
    prompts: list[str] = []

    def confirm(prompt: str, **kwargs: object) -> bool:
        prompts.append(prompt)
        return True

    monkeypatch.setattr("perfect_playlist.cli.typer.confirm", confirm)

    result = CliRunner().invoke(app, ["export", str(source)])

    assert result.exit_code == 0
    assert prompts == ["Save as YAML?"]
    assert "Exported 1 tracks to playlist(1).yaml." in result.output
    assert read_source(tmp_path / "playlist(1).yaml") == TrackSequence(uris=(TRACK_A,))
