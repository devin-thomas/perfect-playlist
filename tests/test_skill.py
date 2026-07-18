from pathlib import Path

import yaml

SKILL_PATH = Path(__file__).resolve().parents[1] / "SKILL.md"


def _skill_parts() -> tuple[dict[str, str], str]:
    content = SKILL_PATH.read_text(encoding="utf-8")
    assert content.startswith("---\n")
    _, frontmatter, body = content.split("---\n", maxsplit=2)
    metadata = yaml.safe_load(frontmatter)
    assert isinstance(metadata, dict)
    return metadata, body


def test_skill_has_valid_trigger_metadata() -> None:
    metadata, body = _skill_parts()

    assert set(metadata) == {"name", "description"}
    assert metadata["name"] == "perfect-playlist"
    assert "Spotify playlist" in metadata["description"]
    assert len(body.splitlines()) < 500


def test_skill_is_portable_and_preserves_write_safety() -> None:
    _, body = _skill_parts()

    required_guidance = (
        "PERFECT_PLAYLIST_SECRETS_FILE",
        "perfect-playlist search QUERY --json",
        "perfect-playlist inspect TRACK_URI_OR_URL --json",
        "perfect-playlist build SOURCE",
        "perfect-playlist add SOURCE --target PLAYLIST_URI_OR_URL",
        "perfect-playlist verify SOURCE PLAYLIST_URI_OR_URL",
        "Do not automatically retry Build or Add",
        "never choose a similar song",
    )
    assert all(guidance in body for guidance in required_guidance)
    assert "docs/" not in body
    assert "resources/spotify-secrets.env" not in body
