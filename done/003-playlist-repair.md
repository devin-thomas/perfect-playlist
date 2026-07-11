# Task 003: Playlist Repair

Status: done

Implemented an opt-in exact playlist repair workflow. The package compares the
current ordered track URIs with the requested URI file, reports differences in
dry-run mode, and applies a full replacement only when `dry_run=False`. Repairs
over 100 tracks are rejected because Spotify's replace-all operation has a
100-item limit.

CLI:

```powershell
perfect-playlist playlist repair PLAYLIST_ID --from tracks.txt
perfect-playlist playlist repair PLAYLIST_ID --from tracks.txt --apply
```

Verification:

- Dry-run repair performs no write.
- Apply mode preserves the requested exact order.
- Matching playlists are not rewritten.
- Oversized repairs fail before the write operation.
