# Perfect Playlist scroll-craft preview

This is an isolated editorial direction study for the Perfect Playlist site.
It uses the scroll-craft runtime copied from the skill, hand-authored SVG
technical drawings, and sample track URIs already documented in the repository.

## Local preview

```sh
npm install
npm run dev
```

## Cloudflare preview

```sh
npm run preview
```

The preview worker has its own name and no custom-domain route. The comparison
is local demo logic; it never calls Spotify or writes to a playlist.
