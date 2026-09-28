# Preview verification

## URLs

- Public preview: https://perfect-playlist-scroll-preview.uppercut-labs.workers.dev/
- Local preview: http://localhost:4500

The Cloudflare Worker is named `perfect-playlist-scroll-preview` and has no
custom-domain route. It does not replace the production site.

## Scroll and interaction evidence

- Desktop Chrome, 1440 x 900: 7.8 viewport-heights; `flow > pin > flow`; no
  dead scroll. See `lab/desktop/sheet.png` and `lab/desktop/report.json`.
- Portrait Chrome, 390 x 844: 7.5 viewport-heights; no horizontal overflow and
  no dead scroll. See `lab/mobile/sheet.png` and `lab/mobile/report.json`.
- Reduced-motion Chrome: 7.8 viewport-heights; the source, comparison controls,
  proof, and close remain available. See `lab/reduced/sheet.png` and
  `lab/reduced/report.json`.
- Opening and comparison frames: `lab/desktop-opening.png`,
  `lab/desktop-alignment.png`, `lab/mobile-opening.png`, and
  `lab/mobile-alignment.png`.
- Demo interaction: swapping the sample result reports “First difference at
  position 2”; restoring it reports “Exact sequence matched”. The demo makes no
  Spotify request and does not write a playlist.
- Keyboard: the comparison controls keep a visible green focus ring on the dark
  stage.
- Remote preview: HTTP 200, correct page title, browser interaction succeeded,
  and no browser errors or failed requests appeared in the phone-sized run.
- Build checks: `npm run build`, JavaScript syntax checks, Wrangler dry run, and
  `npm audit` passed; the dependency audit found no vulnerabilities.

## Feel check

| Intended | Felt in the rendered page |
|---|---|
| Calm title page | Calm |
| Tension at the handoff | Unease |
| Clarity in the sequence drawing | Understanding |
| Focus during the comparison | Control |
| Confidence in the read-back | Confidence |
| Resolve at the colophon | Resolve |

The sequence drawing felt like understanding, which serves the planned clarity
beat. The comparison felt controllable as well as focused. No stage lost its
intended role, so no curve change was needed.

Headless phone emulation is not a physical iPhone test. Open the public preview
on the phone itself to check its browser and touch behavior.
