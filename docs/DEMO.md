# Demo runbook (laptop)

All commands in `~/Developer/hacka/Tagwerk`, with `export PYTHONPATH=$PWD`.

## Before the slot
1. Plug in, disable suspend (a resume can break CUDA: `cuInit 999`; fix = stop gnome-remote-desktop,
   `sudo rmmod nvidia_uvm && sudo modprobe nvidia_uvm`).
2. `docker compose up -d neo4j`
3. Reset to the seeded state (keeps cached clips for replay): `.venv/bin/python scripts/reset_demo.py`
4. `~/tw-restart.sh` and check `curl localhost:8080/health` shows `"graph":"Neo4jStore"`. `.env` needs `API_TOKEN`
   (the API will not start without it); open each page once with `?token=<API_TOKEN>` on every demo device.
5. Warm the models once with a throwaway clip (first run loads Whisper/YOLO/RelateAnything, ~10 s extra), then
   reset again (step 3) and restart (step 4).
6. Open `/graph` on the projector, `/dashboard` in a second tab, `/upload` on the phone
   (`http://<laptop-ip>:8080/upload`, same Wi-Fi or Tailscale `100.118.181.69`).

## During the demo
- Filmed walk: upload the clip from the phone/laptop, or replay its cached run:
  `.venv/bin/python scripts/replay.py <capture_id>` (`--list` shows what is cached). Replay needs no GPU,
  network or Claude.
- Replay picker: on `/graph` the header has a list of saved captures and **▶ Abspielen** (hidden when nothing is
  cached). It replays the chosen one with no GPU/network; the graph animates live and a toast says "fertig: N Änderungen".
  The list is the project's `demo_replays` (`seed/project.json`, `seed/projects/<name>/project.json`), else every
  cached capture except `dt-`, `replay-`, `scan-`, `cap-ui-` ones (`GET /api/replays`).
- Video view on `/graph`: picking a replay that has a video opens a panel on the left (about 38 %, ✕ or the
  "🎬 Video" button hides it). ▶ Abspielen starts the video, and when it really plays the server clock starts
  (`POST /captures` with `replay_of` + `sync=1`): every change is published at its second of the video (the item's `t`,
  else estimated from where its words sit in the speech segment), so the graph fills in as the video reaches each
  statement. Under the video: live captions (what is being said, recognised phrases highlighted) and "Erfasst" with
  mm:ss. A replay without video but with a typed note (Schependomlaan) shows the note as a card instead. A new LIVE
  upload with a video shows that video and its "Erfasst" list as soon as the capture is done.
- New replay entry with video: upload the clip once on `/upload` (or `/api/scan`-less: any capture with a video). The
  API copies the first video and up to 3 photos (files over 300 MB are skipped) and the typed note to
  `cache/<capture_id>/media/` and `capture.json`, so it survives `reset_demo.py` (which deletes `data/captures/` but keeps
  `cache/`). Then add `{"id": "<capture_id>", "label": "..."}` to `demo_replays` in `seed/project.json` (Hörsaal) or
  `seed/projects/<name>/project.json`; without it every cached capture except `dt-/replay-/scan-/cap-ui-` is listed.
  An older cache without media: copy the clip to `cache/<id>/media/` by hand (cap-e2e-2: `cache/cap-e2e-2/media/demo.mp4`,
  backup `~/Developer/hacka/demo-media/demo.mp4`).
- Live: photo + short voice note from the phone. Phrases that change the freshly reset demo state (checked by
  `tests/test_demo_phrases.py`): "Stuhlreihe A ist montiert", "Reihen F bis H Unterkonstruktion",
  "zwei Mann vom Trockenbau sind krank", "Lautsprecher links und Lautsprecher rechts angeschlossen", "die Leinwand ist in Betrieb",
  "40 Stühle geliefert", "Kratzer an der Bühne". Each element only moves up once: after a reset they work again.
- Dashboard: KPI strip, forecast moved by the sick workers, exports (P6 XML, .ics, GAEB X84).

## Real-data demo: Schependomlaan (:8081)
The second API (`PROJECT=schependomlaan`, data in `data-sp/`, cache in `cache-sp/`, in-memory graph) shows the
same loop on the real 2082-element building. Its seed history already marks every started task installed, so
use the roof (not started on the data date 24.07.2015) to show movement.
1. Reset only this project and restart:
   `DATA_DIR=./data-sp CACHE_DIR=./cache-sp NEO4J_URI= PROJECT=schependomlaan .venv/bin/python scripts/reset_demo.py && ~/tw-restart.sh`
   (the plain `reset_demo.py` in step 3 above does not touch `data-sp/`).
2. Open `http://100.118.181.69:8081/dashboard` (expect Ist 83.7 %, SPI 1.09, 0 open defects).
3. Replay the cached roof note: `curl -X POST localhost:8081/captures -H "Authorization: Bearer $API_TOKEN" -F replay_of=sp-demo-roof`.
   The open dashboard updates live: 32 `sporenkap` elements confirmed, Ist 83.7 → 84.6 %, SPI 1.09 → 1.10,
   ST01130 2 → 34.7 %, 2× Timmerman absent. The forecast stays 15.10.2015 (ST01130 is far ahead of plan).
4. If `cache-sp/sp-demo-roof` is missing (fresh checkout; `cache-*` is gitignored), create it once with the typed
   note, then reset (step 1):
   `curl -X POST localhost:8081/captures -H "Authorization: Bearer $API_TOKEN" -F capture_id=sp-demo-roof -F zone_id=Z-3 -F "note=Sporenkap derde verdieping geplaatst. Twee timmerlieden ziek."`
Do not replay `sp-live-1` for this: its storey-02 walls are already installed, so nothing moves.

## Room scan demo (:8082): film a room, then talk
Needs the GPU worker (:8100) and the main API (:8080) running (`~/tw-restart.sh`). Only for the scan project: the
Hörsaal (:8080) and Schependomlaan (:8081) demos are not touched.
1. Open `http://100.118.181.69:8080/scan` (or `http://<laptop-ip>:8080/scan`). Pick the room video (or photos),
   **Projektname** `buero1` (letters/digits, umlauts and spaces are converted: "Büro 1" -> `buero-1`),
   Zonenname `Raum`, press *Scannen* (about 10-60 s). The page lists what was seen by category and ends with
   "Projekt erstellt: ... Bauteile, ... Vorgänge". If it says "Keine Bauteile erkannt" no project is created:
   film again, closer and with more light.
2. Start the API for that project on 8082: `~/tw-scanproject.sh buero1` (prints `/health` with the project name).
   It is the same as
   `PROJECT=buero1 DATA_DIR=./data-scan-buero1 CACHE_DIR=./cache-scan-buero1 NEO4J_URI= .venv/bin/uvicorn tagwerk.api.app:app --host 0.0.0.0 --port 8082`
   (own data dir, in-memory graph, so the Neo4j Hörsaal graph stays untouched). The script kills only the process
   in `/tmp/tw-api-scan.pid`, never use `pkill -f`. To start over: `rm -rf data-scan-buero1 cache-scan-buero1`, run it again.
3. Open `http://100.118.181.69:8082/dashboard`, `/graph` and `/upload` (zone "Raum"). Talk or type a note.
   Activities are one per category present (Rohbau, Fenster/Türen, TGA, Ausbau, Ausstattung), 5 working days
   each, one after the other; the forecast "today" is the day of the scan.
4. Phrases that work (verified on a room with 4 walls, door, 2 windows, ceiling, floor, radiator, 3 sockets,
   2 lights, TV, 4 chairs, table). Singular or plural both match, and a plural means all instances:
   - "Die Tür ist eingebaut." / "Die Türen sind eingebaut." / "Beide Fenster sind eingesetzt."
   - "Der Heizkörper ist montiert und angeschlossen."
   - "Die Steckdosen sind angeschlossen." (counts as installed) / "Die Steckdose ist installiert."
   - "Die Leuchten hängen." (mounted) / "Die Leuchte hängt."
   - "Der Boden ist verlegt." / "Die Wände sind gestrichen." / "Die Decke ist verputzt." (ceiling: started) /
     "Die Decke ist fertig." (100 %)
   - "Der Bildschirm ist in Betrieb." / "Die Stühle sind aufgestellt." / "Die Stühle stehen." / "Die Tische stehen."
   - Absence on the right activity: "Zwei Mann vom Elektriker sind krank." (-> TGA). Trades map to the scan trades:
     TGA <- Elektriker, Heizung, Sanitär, Lüftung; Ausbau <- Maler, Trockenbau, Bodenleger, Fliesenleger;
     Rohbau <- Maurer, Zimmerer; Fenster/Türen <- Tischler, Schreiner, Fensterbauer. "Zwei Mann sind krank" alone
     has no trade (shown as "unbekannt", no activity).
   - Defect: "Kratzer an der Tür." (event only, no state change).
   - Combined note: "Die Tür ist eingebaut, die Steckdose ist installiert und der Boden ist verlegt."
   - Not evidence: "Die Tische werden noch geliefert." (future, logged as material only).
   Words that change state: eingebaut/installiert/montiert/aufgestellt/aufgebaut/steht/stehen (installed), hängt
   (mounted, lights), verlegt (floor), gestrichen/verputzt (walls), fertig (100 %), in Betrieb (screens).
   A numbered name updates only that instance: "Stuhl 2 steht." changes CHAIR-2, "Stuhl 3 und Stuhl 4 stehen."
   changes 3 and 4, while "Die Stühle stehen." still changes all of them.
   An absence covers 3 working days, so for a forecast effect you can see, name the trade of the FIRST activity:
   "Zwei Maurer sind krank." -> Rohbau (TGA only starts a week later, so "Elektriker" barely moves the forecast today).
   Only elements the scan found exist: say what is in the project (Wand, Tür, Fenster, Decke, Boden, Steckdose,
   Leuchte, Heizkörper, Kabel, Bildschirm, Stuhl, Tisch, Sofa, ...). Each element only moves up, a repeat shows "unchanged".

## 3-Minuten-Demo (Raum filmen, hochladen, 3D + Tagesbericht)
Project: the scan project `userwalk` on **:8082** (`~/tw-scanproject.sh userwalk`). The Mac opens the laptop through
the SSH tunnel as `http://localhost:8082/...` (without the tunnel: `http://100.118.181.69:8082/...`). Rehearsed
2026-11-21 on the deployed main (276ca5c): `user_walk.mp4` (70 s, with voice) done after 8 s, 3D after 61 s (30 frames
registered, 21 objects); `screeding_walls_ghana_60s.mp4` (19 s) done after 13 s, 3D after 73 s (48 frames, 20 objects).

Before the slot: reset (see "Reset" below), open in the browser tabs: `/app` (Dashboard, today 26.11.) and `/upload`.

1. **0:00-0:30 Film.** Phone: film the room for about 30 s, slowly, and say what you see, e.g. "Die Tür ist
   eingebaut, die Wände sind gestrichen, zwei Mann vom Elektriker sind krank, Kratzer an der Tür."
2. **0:30 Upload.** Tab `/upload`: zone "Rohbau (Video)", pick the video, *Hochladen*. (From the phone directly:
   `http://100.118.181.69:8082/upload`.) Leave the tab; the request returns when the 3D step is done (about 1 min).
3. **0:30-2:30 Pitch.** Switch to `/app`: the recording appears under "Aufnahmen des Tages" within ~10 s (transcript,
   changes, absence), the Gantt and KPIs update live. Open **Live-Graph**: recording -> activity / event edges.
4. **~1:30 "3D ansehen".** In the recording's accordion item press **3D ansehen** (shown once `has_3d`, after
   ~60-75 s): point cloud, camera path, labelled objects; click a label for the thumbnail and relations
   ("neben Wand"). Direct: `/app#/scan/<capture_id>`.
5. **2:30-3:00 Tagesbericht.** Header button **Tagesbericht** (`/app#/report/2026-11-26`): work done, crew,
   inventory from the 3D scan with relations, events, delays, lookahead. *Drucken / PDF* or *Druckversion (HTML)*
   (`/export/report.html`) for the A4 page with signature line.

Fallbacks:
- 3D not ready in time or "Rekonstruktion nicht möglich": keep talking about the report (it uses the 2D detections),
  then open the cached scan `/app#/scan/uw-video` (ok, 30 frames, 22 objects).
- Upload fails (network): upload `~/Developer/hacka/demo-media/user_walk.mp4` from the laptop
  (`/upload` on :8082) or replay it: `curl -X POST localhost:8082/captures -F replay_of=uw-video -F zone_id=Z-SITE`.
- 8082 down: `~/tw-scanproject.sh userwalk`. Everything down: `~/tw-restart.sh && ~/tw-scanproject.sh userwalk` (~30 s).
- Hörsaal story instead (:8080): `/app`, replay picker on the old `/graph` (▶ Abspielen, `cap-e2e-2`).

Reset (clean state, caches kept), on the laptop in `~/Developer/hacka/Tagwerk`:
`PYTHONPATH=$PWD .venv/bin/python scripts/reset_demo.py`;
`DATA_DIR=./data-sp CACHE_DIR=./cache-sp NEO4J_URI= PROJECT=schependomlaan PYTHONPATH=$PWD .venv/bin/python scripts/reset_demo.py`;
`rm -rf data-scan-userwalk`; then `~/tw-restart.sh && ~/tw-scanproject.sh userwalk`.

## Tagesbericht (Bautagebuch)
`http://<laptop-ip>:8080/export/report.html` (today = data date) or `…/export/report.html?date=2026-11-25` is the
auto-filled German daily report; the JSON for `/app` is `/api/v2/report?date=…`. It fills itself from that day's
recordings: confirmed work (one row per spoken sentence, German state names), crew present/absent (labour and sick
reports covering the day), the scan inventory with relations ("neben Wand", from `cache/<id>/sfm.json`, else the
vision detections), events and defects, delays with causes, the next 3 working days and up to 6 photos/keyframes.
Weather comes from the stored readings (no network call for past days). Bericht-Nr. = working day since project
start. For a PDF: open it in the browser, Ctrl+P, "Als PDF speichern", A4 (the page has print CSS). Schependomlaan:
same URL on :8081.

## Fallbacks
1. Live upload fails: stay on replay.
2. GPU worker down: the API runs speech/vision in-process automatically (slower).
3. Everything down: backup screen recording.
