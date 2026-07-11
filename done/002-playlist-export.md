# Task 002: Playlist Export

Status: done

Implemented deterministic export of an existing Spotify playlist to a UTF-8
text file containing one track URI per line. The package exposes
`export_playlist_to_file()`, and the CLI supports
`playlist export PLAYLIST_ID --out FILE`.

Verification:

- Export preserves playlist order.
- Export writes a trailing newline for non-empty files.
- Existing full-suite tests remain green.
