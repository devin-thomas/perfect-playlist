from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Annotated, NoReturn, TypeVar

import typer
from rich.console import Console

from .auth import command_is_interactive
from .client import SPOTIFY_API_EXCEPTIONS
from .errors import SpotifyExactError
from .io import read_source
from .playlist import build_public_playlist, build_target_playlist

app = typer.Typer(help="Build deterministic Spotify playlists from exact track Sources.")
auth_app = typer.Typer(help="Authenticate with Spotify.")
app.add_typer(auth_app, name="auth")
console = Console()
T = TypeVar("T")


def _run(action: Callable[[], T]) -> T:
    """Translate handled domain and Spotify failures to exit code 2."""
    try:
        return action()
    except SpotifyExactError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(2) from exc
    except SPOTIFY_API_EXCEPTIONS as exc:  # pragma: no cover - external failure boundary.
        console.print("[red]Spotify request failed.[/red]")
        raise typer.Exit(2) from exc


def _pending_command(command: str, parent: str) -> NoReturn:
    console.print(
        f"[yellow]{command} is not implemented until {parent}. "
        "No Spotify or filesystem changes were made.[/yellow]"
    )
    raise typer.Exit(2)


@auth_app.command("login")
def auth_login() -> None:
    """Authenticate and print the active Spotify account."""
    from .client import get_spotify_client

    user = _run(lambda: get_spotify_client().current_user())
    console.print(f"Authenticated as {user.get('display_name') or user.get('id')}")


@auth_app.command("status")
def auth_status() -> None:
    """Check whether Spotify authentication is valid."""
    from .client import get_spotify_client

    user = _run(lambda: get_spotify_client(interactive=False).current_user())
    console.print(f"Authenticated as {user.get('display_name') or user.get('id')}")


@app.command("build")
def build(
    source: str = typer.Argument(..., help="A durable local Source or Spotify reference."),
    name: Annotated[str | None, typer.Option("--name")] = None,
    target: Annotated[str | None, typer.Option("--target")] = None,
    private: Annotated[bool, typer.Option("--private")] = False,
) -> None:
    """Build a playlist from an exact Source."""
    if name is not None and target is not None:
        raise typer.BadParameter("--name and --target cannot be used together.")
    if name is not None and private:
        raise typer.BadParameter("--private and --name cannot be used together.")
    if private and target is None:
        if not command_is_interactive():
            raise typer.BadParameter("Non-interactive private builds require --target.")
        target = typer.prompt("Private playlist link")
    sequence = _run(lambda: read_source(source))
    if target is None:
        result = _run(lambda: build_public_playlist(sequence, name=name))
    else:
        result = _run(lambda: build_target_playlist(sequence, target, private=private))
    console.print(
        f'Built and verified "{result.playlist.name}" with '
        f"{len(result.added_uris)} tracks: {result.playlist.url}"
    )


@app.command("add")
def add(source: str = typer.Argument(...), target: str = typer.Option(..., "--target")) -> None:
    """Show the approved Add shell without performing a partial workflow."""
    _pending_command("add", "Parent 2")


@app.command("verify")
def verify(left: str = typer.Argument(...), right: str = typer.Argument(...)) -> None:
    """Show the approved Verify shell without partial comparison behavior."""
    _pending_command("verify", "Parent 2")


@app.command("export")
def export(
    source: str = typer.Argument(...),
    out: Annotated[Path | None, typer.Option("--out", dir_okay=False)] = None,
    links: Annotated[bool, typer.Option("--links")] = False,
) -> None:
    """Show the approved Export shell without partial filesystem behavior."""
    _pending_command("export", "Parent 2")


@app.command("search")
def search(
    query: str = typer.Argument(...),
    limit: Annotated[int, typer.Option("--limit", min=1, max=10)] = 4,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Show the approved Search shell without starting Parent 3 behavior."""
    _pending_command("search", "Parent 3")


@app.command("inspect")
def inspect(
    track_reference: str = typer.Argument(...),
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Show the approved Inspect shell without starting Parent 3 behavior."""
    _pending_command("inspect", "Parent 3")


if __name__ == "__main__":
    app()
