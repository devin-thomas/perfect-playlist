from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, NoReturn, TypeVar

import typer
from rich.console import Console

from .auth import command_is_interactive
from .client import SPOTIFY_API_EXCEPTIONS
from .errors import InvalidTrackRefError, SpotifyExactError
from .export import next_available_path, serialize, write_export
from .io import read_source
from .playlist import add_to_playlist, build_public_playlist, build_target_playlist
from .search import search_tracks
from .track_refs import normalize_playlist_ref, normalize_track_ref
from .verify import compare_track_sequences

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
    """Append an exact Source to a writable Spotify playlist."""
    sequence = _run(lambda: read_source(source))
    result = _run(lambda: add_to_playlist(sequence, target))
    console.print(
        f'Added and verified {len(result.added_uris)} tracks in "{result.playlist.name}": '
        f"{result.playlist.url}"
    )


@app.command("verify")
def verify(left: str = typer.Argument(...), right: str = typer.Argument(...)) -> None:
    """Compare two Sources as exact TrackSequences."""
    left_sequence = _run(lambda: read_source(left))
    right_sequence = _run(lambda: read_source(right))
    result = compare_track_sequences(left_sequence, right_sequence)
    left_label = _source_label(left)
    right_label = _source_label(right)

    if result.matches:
        console.print(
            f"Verified: both sources contain {result.left_count} tracks and they all match."
        )
        return
    if result.left_count != result.right_count:
        console.print("Not verified: track counts differ.")
        console.print(f"{left_label}: {result.left_count}")
        console.print(f"{right_label}: {result.right_count}")
    else:
        console.print(f"Not verified at position {result.first_difference_position}.")
        console.print(f"{left_label}: {result.left_uri}")
        console.print(f"{right_label}: {result.right_uri}")
    raise typer.Exit(1)


def _source_label(source: str) -> str:
    path = Path(source)
    if path.is_file():
        return path.name
    for normalizer in (normalize_track_ref, normalize_playlist_ref):
        try:
            return normalizer(source)
        except InvalidTrackRefError:
            continue
    return source


@app.command("export")
def export(
    source: str = typer.Argument(...),
    out: Annotated[Path | None, typer.Option("--out", dir_okay=False)] = None,
    links: Annotated[bool, typer.Option("--links")] = False,
) -> None:
    """Render an exact Source as text, YAML, or JSON without overwriting files."""
    sequence = _run(lambda: read_source(source))
    if out is not None:
        _run(lambda: write_export(sequence, out, links=links))
        kind = "links" if links else "tracks"
        typer.echo(f"Exported {len(sequence)} {kind} to {out}.")
        return

    _run(lambda: console.print(serialize(sequence, "txt", links=links), end=""))
    if not command_is_interactive():
        return

    prompt = "Save links as text?" if links else "Save as YAML?"
    if not typer.confirm(prompt, default=True):
        return
    suggested = Path("playlist_links.txt" if links else "playlist.yaml")
    destination = _run(lambda: next_available_path(suggested))
    _run(lambda: write_export(sequence, destination, links=links))
    kind = "links" if links else "tracks"
    typer.echo(f"Exported {len(sequence)} {kind} to {destination}.")


@app.command("search")
def search(
    query: str = typer.Argument(...),
    limit: Annotated[int, typer.Option("--limit", min=1, max=10)] = 4,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Find exact Spotify track candidates without writing or choosing tracks."""
    if not query.strip():
        raise typer.BadParameter("Query must not be empty.")

    results = _run(lambda: search_tracks(query, limit=limit))
    if json_output:
        typer.echo(json.dumps({"results": [result.model_dump() for result in results]}))
        return

    for index, result in enumerate(results, start=1):
        artists = ", ".join(result.artists) or "Unknown artist"
        explicit = "yes" if result.explicit else "no"
        duration = _format_duration(result.duration_ms)
        typer.echo(f"{index}. {result.title} - {artists}")
        typer.echo(f"   Explicit: {explicit}")
        typer.echo(f"   Duration: {duration}")
        typer.echo(f"   URI: {result.uri}")
        typer.echo(f"   Link: {result.url}")


def _format_duration(duration_ms: int | None) -> str:
    if duration_ms is None:
        return "unknown"
    total_seconds = duration_ms // 1000
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes}:{seconds:02d}"


@app.command("inspect")
def inspect(
    track_reference: str = typer.Argument(...),
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Show the approved Inspect shell without starting Parent 3 behavior."""
    _pending_command("inspect", "Parent 3")


if __name__ == "__main__":
    app()
