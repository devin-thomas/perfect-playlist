from importlib.metadata import requires
from importlib.util import find_spec
from pathlib import Path


def test_package_is_importable_from_repository_root() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    package_directory = repository_root / "perfect_playlist"

    assert package_directory.is_dir()
    assert (package_directory / "__init__.py").is_file()
    assert not (repository_root / "src").exists()

    package_spec = find_spec("perfect_playlist")
    assert package_spec is not None
    assert package_spec.origin is not None
    assert Path(package_spec.origin).resolve().is_relative_to(package_directory)


def test_runtime_metadata_includes_yaml_parser() -> None:
    requirements = requires("perfect-playlist") or []

    assert any(requirement.lower().startswith("pyyaml>=6.0") for requirement in requirements)
