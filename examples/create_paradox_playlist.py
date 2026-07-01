from spotify_exact import create_playlist_from_file


if __name__ == "__main__":
    result = create_playlist_from_file(
        "The Paradox Tiny Desk - Available Tracks",
        "examples/paradox-tiny-desk.txt",
        public=False,
        verify=True,
    )
    print(result.playlist.url)

