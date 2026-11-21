# Tagwerk UI v2 (`/app`)

React + Vite + TypeScript + Tailwind v4 + shadcn/ui. Spec: `../docs/UI-V2-CONTRACT.md`.
The build goes to `../web/app/` and is committed, so the laptop serves it from FastAPI without Node.

Routes (hash): `#/dashboard`, `#/graph`, `#/scan/<capture_id>`, `#/report/<YYYY-MM-DD>`; the selected day is `?d=YYYY-MM-DD`.

## Dev

```sh
pnpm install
pnpm dev                                   # http://localhost:5173/app/  (proxies /api /health /captures /media /events to :8080)
TAGWERK_API=http://localhost:8081 pnpm dev # against another API (e.g. Schependomlaan)
```

## Build

```sh
pnpm build      # tsc + vite build -> ../web/app/index.html + ../web/app/assets/*  (commit the result)
pnpm preview    # serves the build at http://localhost:4173/app/ with the same proxy
```

vis-network (Live-Graph) and three.js (3D scan) are split into lazy chunks that load only when their page opens.
No CDN: the Geist font is bundled from `@fontsource-variable/geist`.

## Mock mode

- `?mock=1` in the URL (e.g. `/app/?mock=1#/dashboard`) or `VITE_MOCK=1 pnpm dev|build`: everything comes from
  `src/mock/` and nothing goes over the network (no websocket, replay is simulated).
- Without it the app calls `/api/v2/*`. If `/api/v2/days` answers 404 or the API is unreachable, the v2 data falls back
  to the mocks and the header shows the amber **Demo-Daten** badge. `/api/v2/scan3d/{cid}` and `/api/v2/report` fall
  back the same way when the route itself is missing (FastAPI's default `{"detail": "Not Found"}`); an endpoint's own
  404 must use a different `detail` (then the page says there is no 3D data).

`src/mock/base.json` holds the Hörsaal (10 activities, recordings on several days, events incl. weather);
`src/mock/index.ts` derives `/days`, `/day`, `/taskgraph` and `/report` for any date from it, `src/mock/scan3d.ts`
generates a room scan (≈3000 points, 16 camera poses, 11 objects with relations; `cap-1120-a` is a failed one).
