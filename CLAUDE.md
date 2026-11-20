# CLAUDE.md

## Goal
Tagwerk turns a site manager's videos, photos and voice notes into an element-level Neo4j graph
linked to the GAEB bill of quantities and the Primavera P6 XML schedule, closes the loop into
progress and forecast, and serves a Bauleiter dashboard plus .ics and P6 XML exports.
Hackathon deadline: Fri 27 Nov 2026, 09:00. Read `docs/PLAN.md` before larger changes.

## Hardware limits (GPU worker)
- Pascal GPU (GTX 1060 6 GB / 1080 Ti). torch 2.14.x from the **cu126** index only; never cu128+.
- fp32 only, no AMP benefit, no `torch.compile` (Triton needs compute capability 7.0+).
- Keep YOLO11s, YOLO-World and RelateAnything loaded; Whisper int8 on CPU or as the only extra GPU model.
- Install RelateAnything with `--no-deps`; re-check `torch.__version__` ends in `+cu126` after every install.

## Contracts are the law
- Every stage reads/writes the JSON shapes in `contracts/`. Fixtures in `fixtures/` must validate.
- Change a contract only together with its fixture, its tests and every consumer.
- `capture_id` is the key end to end; every graph write is an idempotent `MERGE`.

## Ontology (English labels; German in `name_de` and `aliases`)
Labels: Project, Site, Building, Storey, Zone, Element, Marker, BoQPosition, Activity, WBS, Trade,
Actor {role: SiteManager|Labour|Bauleiter}, Capture, Observation, Proposal, Note, WeatherReading,
Event, DailyReport. Relationships: see `seed/ontology.yaml`.

## Decisions
- The site manager uses the tool; labour appears only as data (trades, counts, absences); the Bauleiter reads the dashboard.
- An element state changes only when `evidence` is `voice` or `both`, or on a manual tap. Vision alone creates a Proposal.
- Absences ("zwei Mann krank") are `Event {type: absence, trade, count, date}` linked to the activity.
- States only go up (store the max). Activity % is quantity-weighted.
- DIN 276: three-digit codes, marked `verify` until checked.
- P6 XML: activities, WBS, relationships, user-defined fields. Costs live in GAEB.
- .ics times in UTC with stable UID `capture-<id>@tagwerk`.
- Forecast "today" is `DATA_DATE` from config.

## Commands
- Tests: `pytest`
- Validate fixtures: `python scripts/validate_fixtures.py`
- API: `uvicorn tagwerk.api.app:app --reload --port 8000`
- GPU worker: `uvicorn tagwerk.worker_api:app --host 0.0.0.0 --port 8100`
- Neo4j: `docker compose up -d neo4j`

## Rules
- Keys only from `.env` (gitignored): `ANTHROPIC_API_KEY`, `NEO4J_*`, `HF_TOKEN`.
- One module per branch (`feat/<module>`); `main` stays demo-ready.
- Each new stage gets a pytest that runs on CPU with fixtures.
