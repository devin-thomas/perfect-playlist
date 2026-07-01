from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .errors import SpotifyExactError
from .io import read_uri_lines
from .playlist import create_playlist_from_uris
from .track_refs import normalize_track_ref

app = typer.Typer(help="Create Spotify playlists from exact track URIs.")
auth_app = typer.Typer(help="Authenticate with Spotify.")
playlist_app = typer.Typer(help="Create and verify playlists.")
search_app = typer.Typer(help="Search Spotify without writing playlists.")
track_app = typer.Typer(help="Inspect exact Spotify tracks.")

app.add_typer(auth_app, name="auth")
app.add_typer(playlist_app, name="playlist")
app.add_typer(search_app, name="search")
app.add_typer(track_app, name="track")

console = Console()


@auth_app.command("login")
def auth_login() -> None:
    """Authenticate and print the active Spotify account."""
    from .client import get_spotify_client

    try:
        user = get_spotify_client().current_user()
    except Exception as exc:  # pragma: no cover - depends on external auth.
        raise typer.Exit(3) from exc

    console.print(f"Authenticated as {user.get('display_name') or user.get('id')}")


@auth_app.command("status")
def auth_status() -> None:
    """Check whether Spotify auth can reach the current user endpoint."""
    auth_login()


@playlist_app.command("create")
def playlist_create(
    name: str,
    from_file: Path = typer.Option(..., "--from", exists=True, dir_okay=False),
    private: bool = typer.Option(False, "--private", help="Create a private playlist."),
    public: bool = typer.Option(False, "--public", help="Create a public playlist."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate without writing."),
    verify: bool = typer.Option(True, "--verify/--no-verify"),
) -> None:
    """Create a playlist from exact track URIs or URLs."""
    if private and public:
        console.print("[red]Choose either --private or --public, not both.[/red]")
        raise typer.Exit(2)

    try:
        uris = read_uri_lines(from_file)
        result = create_playlist_from_uris(
            name=name,
            uris=uris,
            public=public and not private,
            dry_run=dry_run,
            verify=verify,
        )
    except SpotifyExactError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(2) from exc

    if dry_run:
        table = Table(title=f"Dry run: {name}")
        table.add_column("#", justify="right")
        table.add_column("URI")
        for index, uri in enumerate(result.added_uris, start=1):
            table.add_row(str(index), uri)
        console.print(table)
        console.print(f"{len(result.added_uris)} tracks validated.")
        return

    console.print(f"Created playlist: {result.playlist.url}")


@playlist_app.command("add")
def playlist_add() -> None:
    """Add exact tracks to an existing playlist."""
    console.print("playlist add is planned for the MVP implementation.")


@playlist_app.command("verify")
def playlist_verify() -> None:
    """Verify playlist order against a URI file."""
    console.print("playlist verify is planned for the MVP implementation.")


@search_app.command("track")
def search_track() -> None:
    """Search Spotify track candidates."""
    console.print("search track is planned for the MVP implementation.")


@track_app.command("show")
def track_show(uri_or_url: str) -> None:
    """Normalize and show an exact track reference."""
    try:
        console.print(normalize_track_ref(uri_or_url))
    except SpotifyExactError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(2) from exc


if __name__ == "__main__":
    app()

