# Integrated reference command center

The owner-selected reference image supplies the visual direction, not factual data.
Entry: `web/command_center/index.html`, served at `http://127.0.0.1:8770/`.
The preserved previous frontend is still available at `/?view=legacy`.

## Data contracts

- PC metrics: `/api/pc`, sampled every 10 seconds while visible.
- Quotes: `/api/markets`, public provider observations, not an execution feed.
- RSS: `/api/news`, with original source links and publication dates.
- Broker: `/api/trading`; numbers require `account.telemetry_verified === true` and `account.available === true`.
- Services: `/api/platform/status`; HTTP readiness is not functional certification.
- Memory: `/api/memory/status` and owner-requested `/api/memory/search`.
- Local assistant: `/api/reference-ui/local-chat` calls only localhost Ollama. No tool execution or paid fallback.
- Terminal: `/api/terminal/exec`, explicit owner submission only. Existing backend authorization remains authoritative.
- Camera and desktop: explicit Start/Stop controls; never captured at page load.
- World Monitor and Gods Eye View full native interfaces remain inside the Jarvis workspace on demand. This preserves their current controls, but is not a rewrite of all their internal UIs.

Unavailable telemetry stays unavailable. Stale quotes are marked; no example balances, trades,
confidence percentages, camera feeds or success receipts are rendered as observations.

## Dependencies / provenance

Three.js 0.160.1 (MIT) is vendored from the npm distribution. Copyright notice is retained
in `vendor/THREE-LICENSE.txt`. Earth texture is the upstream Three.js r160 example asset:
https://github.com/mrdoob/three.js/blob/r160/examples/textures/planets/earth_atmos_2048.jpg
The texture is a static basemap, not a live satellite image. Globe overlay points come only
from the source-labelled USGS observations and static maritime reference coordinates.

The previous frontend and dashboard server file were backed up under
`backups/reference-ui-20260922/` before changes. Restoring the frontend alone does not require
a service restart; server route changes do.
