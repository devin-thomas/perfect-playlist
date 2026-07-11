from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from .client import SPOTIFY_API_EXCEPTIONS
from .errors import SpotifyExactError
from .io import read_manifest, read_uri_lines
from .models import TrackSummary
from .playlist import add_items_in_order, create_playlist_from_uris
from .search import get_tracks, search_tracks
from .track_refs import normalize_track_ref
from .verify import export_playlist_to_file, verify_playlist_prefix

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


InputFileOption = typer.Option("--from", exists=True, dir_okay=False)
ManifestFileOption = typer.Option("--manifest", exists=True, dir_okay=False)


def _print_track_table(title: str, tracks: Sequence[TrackSummary]) -> None:
    table = Table(title=title)
    table.add_column("#", justify="right")
    table.add_column("Title")
    table.add_column("Artists")
    table.add_column("Duration")
    table.add_column("Explicit")
    table.add_column("URI")
    table.add_column("URL")

    for index, track in enumerate(tracks, start=1):
        duration_ms = track.duration_ms
        duration = ""
        if duration_ms is not None:
            seconds = duration_ms // 1000
            duration = f"{seconds // 60}:{seconds % 60:02d}"
        table.add_row(
            str(index),
            track.title,
            ", ".join(track.artists),
            duration,
            "yes" if track.explicit else "no",
            track.uri,
            track.url,
        )

    console.print(table)


@auth_app.command("login")
def auth_login() -> None:
    """Authenticate and print the active Spotify account."""
    from .client import get_spotify_client

    try:
        user = get_spotify_client().current_user()
    except SpotifyExactError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(3) from exc
    except SPOTIFY_API_EXCEPTIONS as exc:  # pragma: no cover - depends on external auth.
        console.print("[red]Spotify auth failed. Check local Spotify credentials.[/red]")
        raise typer.Exit(3) from exc

    console.print(f"Authenticated as {user.get('display_name') or user.get('id')}")


@auth_app.command("status")
def auth_status() -> None:
    """Check whether Spotify auth can reach the current user endpoint."""
    auth_login()


@playlist_app.command("create")
def playlist_create(
    name: str = typer.Argument("", help="Playlist name; omitted when using --manifest."),
    from_file: Annotated[Path | None, InputFileOption] = None,
    manifest_file: Annotated[Path | None, ManifestFileOption] = None,
    private: Annotated[bool, typer.Option("--private", help="Create a private playlist.")] = False,
    public: Annotated[bool, typer.Option("--public", help="Create a public playlist.")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Validate without writing.")] = False,
    verify: Annotated[bool, typer.Option("--verify/--no-verify")] = True,
) -> None:
    """Create a playlist from exact track URIs, URLs, or a YAML manifest."""
    if private and public:
        console.print("[red]Choose either --private or --public, not both.[/red]")
        raise typer.Exit(2)

    try:
        description = ""
        if from_file is not None and manifest_file is not None:
            raise SpotifyExactError("Choose either --from or --manifest, not both.")
        if manifest_file is not None:
            if name:
                raise SpotifyExactError("Do not provide NAME when using --manifest.")
            if private or public:
                raise SpotifyExactError("Playlist visibility is defined by the manifest.")
            manifest = read_manifest(manifest_file)
            name = manifest.name
            public = manifest.public
            description = manifest.description
            uris = manifest.uris
        else:
            if not name or from_file is None:
                raise SpotifyExactError("Provide NAME and --from, or use --manifest.")
            uris = read_uri_lines(from_file)
        result = create_playlist_from_uris(
            name=name,
            uris=uris,
            public=public and not private,
            description=description,
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
    if result.verified is True:
        console.print("Verification passed.")


@playlist_app.command("add")
def playlist_add(
    playlist_id: str,
    from_file: Annotated[Path, InputFileOption],
    position: Annotated[int | None, typer.Option("--position", min=0)] = None,
) -> None:
    """Add exact tracks to an existing playlist."""
    try:
        uris = read_uri_lines(from_file)
        snapshot_id = add_items_in_order(playlist_id, uris, start_position=position)
    except SpotifyExactError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(2) from exc

    console.print(f"Added {len(uris)} tracks. Snapshot: {snapshot_id}")


@playlist_app.command("verify")
def playlist_verify(
    playlist_id: str,
    from_file: Annotated[Path, InputFileOption],
) -> None:
    """Verify playlist order against a URI file."""
    try:
        uris = read_uri_lines(from_file)
        verify_playlist_prefix(playlist_id, uris)
    except SpotifyExactError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(5) from exc

    console.print(f"Verification passed for {len(uris)} tracks.")


@playlist_app.command("export")
def playlist_export(
    playlist_id: str,
    output_file: Annotated[Path, typer.Option("--out", dir_okay=False)],
) -> None:
    """Export an existing playlist's track URIs in playlist order."""
    try:
        uris = export_playlist_to_file(playlist_id, output_file)
    except SpotifyExactError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(5) from exc

    console.print(f"Exported {len(uris)} tracks to {output_file}.")


@search_app.command("track")
def search_track(
    query: str,
    limit: Annotated[int, typer.Option("--limit", min=1, max=50)] = 10,
    market: Annotated[str | None, typer.Option("--market")] = "US",
    json_output: Annotated[
        bool, typer.Option("--json", help="Print machine-readable JSON.")
    ] = False,
) -> None:
    """Search Spotify track candidates."""
    try:
        tracks = search_tracks(query, limit=limit, market=market)
    except SpotifyExactError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(4) from exc

    if json_output:
        console.print(json.dumps([track.model_dump() for track in tracks], indent=2))
        return

    _print_track_table("Track search results", tracks)


@track_app.command("show")
def track_show(
    uri_or_url: str,
    market: Annotated[str | None, typer.Option("--market")] = "US",
    json_output: Annotated[
        bool, typer.Option("--json", help="Print machine-readable JSON.")
    ] = False,
) -> None:
    """Normalize an exact track reference and show Spotify metadata."""
    try:
        uri = normalize_track_ref(uri_or_url)
        tracks = get_tracks([uri], market=market)
    except SpotifyExactError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(2) from exc

    if not tracks:
        console.print(f"[red]Spotify did not return metadata for {uri}.[/red]")
        raise typer.Exit(4)

    if json_output:
        console.print(json.dumps(tracks[0].model_dump(), indent=2))
        return

    _print_track_table("Track", tracks)


if __name__ == "__main__":
    app()
