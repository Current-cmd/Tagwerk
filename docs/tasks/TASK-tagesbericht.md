# Task: Tagesbericht (daily report) backend for Tagwerk

You are working on the Linux GPU laptop in the Tagwerk repo, a hackathon project. The demo is a 3-minute pitch:
1. The presenter films a room with voice.
2. They upload it and pitch while it processes.
3. They show the output, which ends with an auto-filled German daily report (Tagesbericht / Bautagebuch).

You build the **report backend**. Other agents build the SfM/3D part (`tagwerk-opus`, branch `feat/scan3d`) and the
React UI (on the Mac). Do not do their parts.

## Setup
```bash
cd ~/Developer/hacka/Tagwerk && git fetch -q origin
git worktree add ~/Developer/hacka/Tagwerk-report -b feat/report origin/feat/core
cd ~/Developer/hacka/Tagwerk-report && export PYTHONPATH=$PWD
PY=~/Developer/hacka/Tagwerk/.venv/bin/python   # use the main checkout's venv
```
Read first:
- `CLAUDE.md`: rules, ports, ids and the git push procedure.
- `docs/UI-V2-CONTRACT.md`: section "GET /api/v2/report" plus the `/export/report.html` line. This is the spec, and the field names must match exactly.
- `tagwerk/v2.py`: the existing day snapshot. Reuse it and do not rebuild state yourself.
- `tagwerk/api/app.py`
- `tagwerk/project.py`
- `tagwerk/pipeline/structure.py`: holds `STATES`, the state names and the trade words.

## Hard rules
- Do NOT restart, kill or touch the running services on 8080, 8081, 8082 and 8100. Do not edit the main checkout
  `~/Developer/hacka/Tagwerk`. If you need a temp API, use port 8084 with copied dirs:
  `DATA_DIR=/tmp/rp-data CACHE_DIR=/tmp/rp-cache NEO4J_URI=`.
- Never use `pkill -f`, because it kills your own shell. Kill only by PID.
- Write a failing test first, then the fix.
- Before every commit, both of these must be green. CI has no GPU or speech/vision models, so monkeypatch
  `tagwerk.pipeline.speech.transcribe` and `tagwerk.pipeline.vision.analyse` to empty outputs in API tests that post
  captures (see `tests/test_api.py::test_absence_only_capture_publishes_activity_update_and_graph_delay`).
  - `$PY -m pytest -q`
  - `$PY -m ruff check .` (line length 130)
- Push ONLY `feat/report`, using the askpass procedure in CLAUDE.md "Rules". Never print the token and never push `main` or `feat/core`.
- Do not touch `tagwerk/pipeline/sfm.py`, `worker_api.py`, the runner sfm stage or `web/`. Those belong to the other agents.

## Build
1. **`GET /api/v2/report?date=YYYY-MM-DD`** (default: the project's today = data_date). Implement it in a new module
   `tagwerk/report.py`, keep the route in app.py thin, and validate the date (400 when invalid). Fields, exactly per the contract:
   - `project` {name, site, client}: from project meta, with nulls when missing.
   - `weather`: that day's reading from the captures or context. Make no network call for past days.
   - `recordings`: captures of that day with {capture_id, time, zone_name, kind, has_3d}. `has_3d` is true when
     `cache/<cid>/sfm.json` exists with `"ok": true`.
   - `work_done`: confirmed changes of that day (not proposals) with {activity_id, activity_name, element_name,
     state_de, quote, capture_id}. `state_de` uses German state labels: started→begonnen, installed→eingebaut/montiert,
     mounted→montiert, connected→angeschlossen, wired→verkabelt, tested→geprüft, commissioned→in Betrieb,
     checked→abgenommen, painted→gestrichen, primed→grundiert, prepared→vorbereitet, covered→verlegt, levelled→nivelliert,
     substructure/framed→Unterkonstruktion, boarded→beplankt, stripped/removed→ausgebaut/entfernt. Put them in one mapping
     constant and cover every state in `STATES`.
   - `workforce`: present comes from labour of that day and absent from absence events covering that day. Sum per trade.
   - `inventory`: from `cache/<cid>/sfm.json` objects of that day's recordings when present, grouped by name_de:
     {name_de, count, relations (German strings "neben Wand", deduplicated, max 5), thumb, capture_id}. If there is no
     sfm.json, fall back to the vision detections in `cache/<cid>/vision.json`. Group by label using `CATALOG` German names from
     `tagwerk/pipeline/scan.py`, take relations from `frames[].triplets`, and translate predicates to German (on→auf,
     under/below→unter, above→über, next to/beside→neben, in front of→vor, behind→hinter, attached to→an,
     standing on→steht auf, holding→hält; anything unknown stays as it is).
   - `events`: that day's events (defect, delay, safety, weather, absence) with severity.
   - `photos`: up to 6 media URLs of that day: kept photos, plus video keyframes from `cache/<cid>/media/` or `derived/frames`.
   - `delays`: activities with delay_d > 0 as of that day, with cause (from the v2 day snapshot).
   - `lookahead`: the next 3 working days (from the v2 day snapshot).
2. **`GET /export/report.html?date=`**: a self-contained, print-ready German A4 page with inline CSS and no external
   assets except the images, which are relative `/media/...` URLs. Layout of a Bautagebuch page:
   - Kopf: Projekt, Bauherr, Ort, Datum, Wetter, Bericht-Nr. = working day number since project start.
   - Sections: Ausgeführte Arbeiten, Personal (anwesend / abwesend), Inventar aus Scan (mit Relationen), Ereignisse &
     Mängel, Verzüge, Vorschau (nächste 3 Arbeitstage), Fotos (grid).
   - Unterschriftszeile: Bauleiter, Datum.
   - `@media print` rules, page breaks avoided inside tables.
   - Empty sections say "keine".
3. **Tests**, in a new file `tests/test_report.py`:
   - Hörsaal seed, a past day: report from history only. Check the field shapes, `state_de` is German, and there are no cost fields.
   - After posting a typed note "Stuhlreihe A ist montiert. Zwei Mann vom Trockenbau sind krank." with
     `capture_id=rep-1`: `work_done` has Stuhlreihe A → montiert, and absent has Trockenbau 2.
   - Inventory from a synthetic `cache/rep-1/sfm.json` (write one in the test per the contract) groups objects and
     translates relations. The fallback works from a synthetic `vision.json` with triplets.
   - `has_3d` true/false.
   - The HTML export returns 200 with `text/html`, contains "Tagesbericht", the date and "Unterschrift", and has no
     `http(s)://` script or style references.
   - A bad date returns 400.
   - Schependomlaan works (see `tests/test_schependomlaan.py` for loading it) and stays under 1.5 s.
4. **Real check** (temp API on 8084 with copies of the real cache, `cp -r ~/Developer/hacka/Tagwerk/cache /tmp/rp-cache`):
   - Post the typed note above and fetch both endpoints.
   - Save the HTML to `/tmp/tw-report/hoersaal.html` and render a screenshot with headless Chrome to
     `/tmp/tw-report/hoersaal.png`.
   - Do the same for Schependomlaan on a copy of `cache-sp` after replaying `sp-demo-roof`.
   - Stop the temp API and delete the `/tmp` copies when done.
5. **Docs:** add a "Tagesbericht" paragraph to `docs/DEMO.md` (URL, what fills it, print to PDF via the browser).

## Report back
Send this to the orchestrator with
`reason network send anoushk/reason-network-orchestrator-setup "<report>"`, or paste it here if that fails:
- commit hash on `feat/report`, plus diff stat
- the new test names, plus the pytest and ruff summary lines
- the `/api/v2/report` JSON for the Hörsaal after the typed note (trimmed)
- screenshot paths
- anything from the contract you could not fill, and why
- your context %
