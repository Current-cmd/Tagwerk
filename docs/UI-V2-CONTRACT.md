# UI v2: contract between the API and the React app

Goal (from the user's spoken brief, 2026-11-21): a simpler Bauleiter dashboard and a task-based live graph for
projects without a BIM model (the Hörsaal), styled with shadcn/ui, with a day slider to step left/right through the
project and watch the work and the schedule build up. No costs anywhere.

Served by the existing FastAPI app. The React app is built to static files in `web/app/` (committed), so the laptop
needs no Node. Old pages (`/dashboard`, `/graph`, `/site`, `/upload`, `/scan`) stay as they are.

## Routes
- `GET /app` and `GET /app/{path}`: the built SPA (`web/app/index.html`, `web/app/assets/*`). Unknown paths under
  `/app/` return `index.html` (hash routing is used anyway: `/app#/dashboard`, `/app#/graph`).
- `GET /api/v2/days`
- `GET /api/v2/day?date=YYYY-MM-DD` (default: project "today" = data_date)
- `GET /api/v2/taskgraph?date=YYYY-MM-DD`
- Existing and reused: `GET /health`, `GET /api/replays`, `POST /captures` (incl. `replay_of`, `sync=1`),
  `GET /media/{cid}/{file}`, websocket `/events` (refetch the day on `{"type":"status","props":{"step":"done"}}`).

## "As of day D"
State at the END of day D: seed + history entries with date <= D + stored captures with date <= D, applied in date
order. Forecasts are computed with today = D (for D <= project today) so the slider shows how the forecast looked that
day. For D after project today, show the plan only (`is_future: true`): no actuals beyond today.

## GET /api/v2/days
```json
{"today": "2026-11-26", "first": "2026-11-16", "last": "2026-12-04",
 "days": [{"date": "2026-11-16", "workday": true, "recordings": 1, "events": 0}]}
```
`first` = earliest planned start or first history date, `last` = max(baseline finish, forecast finish). Every calendar
day in between is listed.

## GET /api/v2/day?date=D
```json
{
 "date": "2026-11-26", "today": "2026-11-26", "is_future": false,
 "project": {"name": "Hörsaal Sanierung", "bim": false},
 "kpi": {"pct_actual": 73.3, "pct_planned": 70.1, "spi": 1.05, "forecast_finish": "2026-12-01",
         "baseline_finish": "2026-11-28", "delay_d": 1, "open_defects": 1},
 "weather": {"tempC": 6.1, "precipMm": 0.0, "windKmh": 12.0, "source": "open-meteo"},
 "recordings": [{
   "capture_id": "cap-e2e-2", "time": "10:42", "zone_id": "Z-AUDIENCE", "zone_name": "Zuschauerraum",
   "kind": "video", "transcript": "Stuhlreihe A ist montiert, …", "note": null,
   "video": "/media/cap-e2e-2/demo.mp4", "photos": [],
   "changes": [{"element_id": "E-ROW-A", "element_name": "Stuhlreihe A", "action": "confirmed",
                "state": "installed", "activity_id": "A1080", "activity_name": "Bestuhlung montieren",
                "quote": "Stuhlreihe A ist montiert", "evidence": "both"}],
   "proposals": [{"element_id": "E-DOOR-1", "element_name": "Tür 1", "state": "started", "activity_id": "A1010"}],
   "absences": [{"trade": "Trockenbau", "count": 2, "reason": "krank", "activity_id": "A1060"}],
   "events": [{"type": "delay", "text": "…", "severity": "medium", "activity_id": "A1060"}],
   "material": [], "labour": []
 }],
 "activities": [{
   "id": "A1080", "name": "Bestuhlung montieren", "wbs": "1.3", "trade": "Bestuhlung",
   "zones": ["Zuschauerraum"], "gaeb": [{"oz": "01.04.0010", "text": "Bestuhlung neu liefern und montieren"}],
   "planned_start": "2026-11-23", "baseline_finish": "2026-11-25", "forecast_start": "2026-11-23",
   "forecast_finish": "2026-12-01", "pct": 34.4, "planned_pct": 60.0, "delay_d": 4, "tracked": true, "done": false,
   "cause": "2× Trockenbau krank", "recordings": ["cap-e2e-2"], "last_recording": "2026-11-26",
   "predecessors": ["A1070"]
 }],
 "lookahead": [{"date": "2026-11-27", "activities": [{"id": "A1090", "name": "…", "trade": "…",
                "zones": ["…"], "planned_pct_by_end": 40.0}]}],
 "events": [{"id": "cap-e2e-2:absence:0", "date": "2026-11-26", "type": "absence", "text": "2× Trockenbau krank",
             "severity": "medium", "activity_id": "A1060", "capture_id": "cap-e2e-2", "source": "capture"},
            {"id": "weather:2026-11-26", "date": "2026-11-26", "type": "weather", "text": "Starkregen 12 mm: Außenarbeiten ruhen",
             "severity": "medium", "activity_id": null, "capture_id": null, "source": "weather"}]
}
```
- `recordings`: captures of day D only, newest first. `activities`: all activities, sorted by planned start (the Gantt
  order). `lookahead`: the next 3 working days after D with the activities planned to run on them. `events`: all events
  with date <= D, newest first, plus weather events.
- Weather events: from the weather reading of that day's captures (or the context weather for today): precip >= 5 mm,
  wind >= 50 km/h or temp <= 0 °C produce one event naming the constraint (outdoor work, concrete/screed, crane). Only
  when a reading exists; no network calls for past days.
- No cost fields anywhere (`ev_eur`, `pv_eur`, `ac_eur`, `bac_eur` are not part of v2).

## GET /api/v2/taskgraph?date=D
Non-BIM view: GAEB position - P6 activity - place (zone) - recording - event/proposal. No element nodes.
```json
{"date": "2026-11-26",
 "nodes": [{"id": "oz:01.04.0010", "type": "gaeb", "label": "01.04.0010 Bestuhlung neu liefern"},
           {"id": "A1080", "type": "activity", "label": "Bestuhlung montieren", "pct": 34.4, "delay_d": 4, "done": false,
            "planned_start": "2026-11-23", "forecast_finish": "2026-12-01"},
           {"id": "Z-AUDIENCE", "type": "zone", "label": "Zuschauerraum"},
           {"id": "cap-e2e-2", "type": "recording", "label": "10:42 Video", "date": "2026-11-26"},
           {"id": "cap-e2e-2:absence:0", "type": "event", "label": "2× Trockenbau krank", "severity": "medium"},
           {"id": "prop:cap-x:E-DOOR-1", "type": "proposal", "label": "Tür 1: begonnen? (nur Bild)"}],
 "edges": [{"src": "oz:01.04.0010", "dst": "A1080", "type": "PRICES"},
           {"src": "A1080", "dst": "Z-AUDIENCE", "type": "IN_ZONE"},
           {"src": "A1070", "dst": "A1080", "type": "PRECEDES"},
           {"src": "cap-e2e-2", "dst": "A1080", "type": "PROGRESSED", "label": "Stuhlreihe A montiert"},
           {"src": "cap-e2e-2:absence:0", "dst": "A1060", "type": "AFFECTS"},
           {"src": "prop:cap-x:E-DOOR-1", "dst": "A1010", "type": "PROPOSES"}]}
```
Recordings, events and proposals of day D only (activities/GAEB/zones always). Activity zones come from its elements'
zones; GAEB links from mapping.csv.

## Frontend (React + Vite + TypeScript + Tailwind + shadcn/ui), German UI
Header: project name, the day slider (prev/next buttons, a range over `days`, keyboard ←/→, "Heute" button; dots on
days with recordings), tabs Dashboard | Live-Graph, link to the old pages.
- KPI strip (small, one row): Fortschritt Ist/Soll %, SPI, Prognose-Ende with Verzug in AT, offene Mängel,
  Wetter heute. No cost.
- Dashboard: three tiles only.
  1. Aufnahmen des Tages: list of recordings with time, place, kind; each expands (accordion) to show the transcript or
     note, the video, what was captured (changes with element + state + quote), which activities it is linked to,
     absences, events, proposals ("was der Agent daraus erkannt hat").
  2. Vorgänge (Activities): toggle between a Gantt chart (baseline bar + actual/forecast bar, today line, delay in red,
     links) and a table; clicking an activity opens a detail sheet: dates, %, delay and cause, GAEB positions, zones,
     linked recordings (click jumps to that day and recording), predecessors. Below: "Vorschau: nächste 3 Arbeitstage"
     from `lookahead`.
  3. Ereignisse: special events, absences, defects, weather events, newest first, with severity badges.
- Live-Graph: the task graph (vis-network from npm, bundled; hierarchical left to right: GAEB, activity, zone,
  recording, event/proposal), activity nodes coloured by % and red-outlined when delayed, proposals dashed; the day
  slider drives it. Left panel (collapsible) keeps the existing replay video feature: picker from `/api/replays`,
  ▶ Abspielen starts the video, then POSTs `replay_of` + `sync=1` when the video fires `playing`; captions from the
  entry's segments; an "Erfasst" list fed by the websocket. On `done`, refetch day + taskgraph.
- Must work offline: no CDN, fonts bundled (or system font stack).

## Scan 3D + Tagesbericht (added 2026-11-21)
Demo flow (3 min): film the room with voice (~30 s), upload, pitch for ~2 min while it processes, then show the 3D room,
the tagged objects and the auto-filled daily report in `/app`.

### Pipeline
- New stage `sfm` for captures with a video (and for `/api/scan` uploads), run after vision on the GPU worker process
  (`worker_api.py`, same `_gpu_stage` pattern and cache): extract ~2-3 fps (40-80 frames, longest side 1280 px), pycolmap
  (installed in the laptop venv, 4.2.1, CPU) SIFT + sequential matching + incremental mapping. Hard time limit 150 s; on
  failure or timeout return `ok: false` with a German `reason`, never fail the capture. Replays read the cached `sfm.json`.
- 3D objects: for every detection (vision frames: YOLO/YOLO-World objects, markers excluded) take the triangulated 3D
  points whose 2D observation in that frame falls inside the box; object position = median, extent = 10-90 % range.
  Frames used for SfM and for vision must be matched by time (vision uses ~1 fps; map by nearest timestamp or run
  vision detections on the SfM frames). Merge detections of the same label whose 3D positions are close (relative to
  the scene size) into one object instance.
- Relations: RelateAnything triplets (vision `frames[].triplets`, source "model" or "geometry") are attached to the
  merged objects (map frame obj_id to instance), aggregated with counts/max score, German predicate labels.

### cache/<cid>/sfm.json  and  GET /api/v2/scan3d/{cid}  (404 when there is none)
```json
{"capture_id": "uw-video", "ok": true, "reason": null, "seconds": 74.2, "frames_used": 61, "frames_registered": 55,
 "points": [[0.1, 0.2, 1.3, 180, 170, 160]],
 "cameras": [{"t": 0.0, "position": [0, 0, 0], "look": [0, 0, 1], "frame": "/media/uw-video/sfm/0001.jpg"}],
 "objects": [{"id": "obj-1", "label": "door", "name_de": "Tür", "category_de": "Öffnungen", "position": [0.4, 0.1, 2.0],
              "extent": [0.9, 2.0, 0.1], "detections": 12, "first_t": 3.0, "last_t": 9.5, "conf": 0.81,
              "thumb": "/media/uw-video/sfm/0004.jpg", "bbox_in_thumb": [x1, y1, x2, y2],
              "element_id": "E-DOOR-1",
              "relations": [{"rel": "next to", "rel_de": "neben", "target": "obj-2", "target_name": "Wand",
                             "score": 0.52, "count": 4, "source": "model"}]}],
 "units": "relative (SfM scale is arbitrary)"}
```
`points` downsampled to <= 20000. `element_id`: the project element this object most likely is (same CATALOG label /
alias as the scan project or the seed), else null.

### GET /api/v2/report?date=D   (Tagesbericht / Bautagebuch, German)
```json
{"date": "2026-11-26", "project": {"name": "…", "site": "…", "client": "…"},
 "weather": {"tempC": 6.1, "precipMm": 0.0, "windKmh": 12.0},
 "recordings": [{"capture_id": "…", "time": "10:42", "zone_name": "…", "kind": "video", "has_3d": true}],
 "work_done": [{"activity_id": "A1080", "activity_name": "…", "element_name": "Stuhlreihe A", "state_de": "montiert",
                "quote": "…", "capture_id": "…"}],
 "workforce": {"present": [{"trade": "Elektro", "count": 3}], "absent": [{"trade": "Trockenbau", "count": 2, "reason": "krank"}]},
 "inventory": [{"name_de": "Tür", "count": 1, "relations": ["neben Wand", "unter Leuchte"], "thumb": "…", "capture_id": "…"}],
 "events": [{"type": "defect", "text": "…", "severity": "low"}],
 "photos": ["/media/…"],
 "delays": [{"activity_id": "…", "activity_name": "…", "delay_d": 4, "cause": "…"}],
 "lookahead": [{"date": "…", "activities": ["…"]}]}
```
Also `GET /export/report.html?date=D` (print-ready, German, A4) for a PDF via the browser.

### Frontend additions
- `#/scan/<cid>`: 3D viewer (three.js from npm, bundled; OrbitControls): coloured point cloud, camera path as a line with
  small frustums, one labelled marker per object (name_de, click shows thumb with box, detections, relations as chips
  "neben Wand"), category colours; side list of objects grouped by category. "Rekonstruktion nicht möglich: <reason>"
  card when ok is false, still listing objects/relations from 2D.
- `#/report/<date>`: the Tagesbericht laid out like a German Bautagebuch page (shadcn Cards/Table), print button
  (window.print with print CSS) and link to `/export/report.html`.
- Recording accordion items with `has_3d` get a "3D ansehen" button; the dashboard header gets "Tagesbericht".
