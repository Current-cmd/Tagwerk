# Tagwerk

Site manager walks the site, films and talks. Tagwerk turns that into a live, element-level
graph tied to the contract (GAEB) and the schedule (Primavera P6 XML), a daily dashboard for
the Bauleiter, and exports back to Primavera and Outlook.

Full plan: `docs/PLAN.md` (export of the planning doc).

## Architecture

Everything runs on the GPU laptop (Ubuntu 22.04, GTX 1060). The Mac only edits code.

```
 Chrome upload page (phone/laptop) ──► API :8080 ──► GPU worker :8100 (Whisper int8, ArUco, YOLO11s,
                                        │   │         YOLO-World, RelateAnything)
                                        │   └── context (Open-Meteo) · structuring (Claude or rules) · progress loop
                                        ├── Neo4j :7687 (Docker), browser at :7474
                                        └── websocket /events ──► /graph (live graph) · /dashboard (Bauleiter) · /site
```

Port 8000 is taken by Portainer on the laptop, so the API runs on **8080**.

- **Project state** (`tagwerk/project.py`) is authoritative: seed CSVs + `seed/history.json` + every stored
  capture result, all applied through one function (`apply_structured`). The graph is a projection of it
  (`tagwerk/graph/sync.py`, batched idempotent `MERGE`s; every node also carries `:Tw` for a unique id index).
- **Structuring** (`tagwerk/pipeline/structure.py`): Claude with an enum-restricted tool schema when
  `ANTHROPIC_API_KEY` is set, otherwise German/English keyword rules (elements by alias and row lists, states
  by verb, absences, labour, deliveries, defects) plus ArUco marker hits. Voice/note confirms, vision alone proposes.
- **Forecast**: rate = 100 % / (planned working days × planned crew); remaining work is simulated day by day
  with crew minus that day's absences; finish-to-start successors shift with it. Labelled "projection from
  today's evidence". Activity % is BoQ-weighted (qty × unit price × share of each linked position).
- **Caching / replay**: every stage output lands in `cache/<capture_id>/`. `replay_of=<capture_id>` (or
  `scripts/replay.py <capture_id>`) replays a processed capture with no GPU, network or Claude.

## Run it (on the laptop)

```bash
cd ~/Developer/hacka/Tagwerk
docker compose up -d neo4j
~/tw-restart.sh                                  # (re)starts worker :8100 and API :8080 from this checkout
PYTHONPATH=$PWD .venv/bin/python -m pytest -q    # PYTHONPATH must be set: the shell's ROS paths break the venv
```

Pages: `/graph`, `/dashboard`, `/site`, `/upload`. Exports: `/export/p6.xml`, `/export/p6-baseline.xml`,
`/export/day.ics`, `/export/boq.x83`, `/export/boq.x84`. Demo runbook: `docs/DEMO.md`.

`.env`: `NEO4J_URI=bolt://localhost:7687`, `GPU_WORKER_URL=http://localhost:8100`, `DATA_DATE=2026-11-26`
(the forecast's "today"; live captures are stamped with it). `ANTHROPIC_API_KEY` optional.

## Layout

| Path | What |
| --- | --- |
| `contracts/` | JSON Schemas (capture, transcript, vision, context, structured, graph_event, dashboard) |
| `fixtures/` | One valid example per contract |
| `tagwerk/api/` | FastAPI app, upload, websocket |
| `tagwerk/pipeline/` | Stages: normalize, speech, vision, context, structure, loop, export |
| `tagwerk/graph/` | Neo4j writer |
| `tagwerk/worker_api.py` | GPU worker service |
| `seed/` | Ontology (BOT + DiCon + DIN 276 + GAEB terms), constraints, seed data |
| `web/` | Upload page, live graph (vis-network), dashboard |
| `scripts/` | Environment check, fixture validation, replay |

## Licences to keep in mind

RelateAnything is AGPL-3.0 (weights under the DINOv3 licence); the Schependomlaan dataset is for
academic use. Fine for the hackathon; revisit before any commercial use.
