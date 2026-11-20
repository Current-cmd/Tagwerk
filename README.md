# Tagwerk

Site manager walks the site, films and talks. Tagwerk turns that into a live, element-level
graph tied to the contract (GAEB) and the schedule (Primavera P6 XML), a daily dashboard for
the Bauleiter, and exports back to Primavera and Outlook.

Full plan: `docs/PLAN.md` (export of the planning doc).

## Architecture

```
 Chrome upload page ──► API (laptop) ──► GPU worker (friend's machine, optional)
                         │   │              speech · vision
                         │   └── Claude structuring · loop · exports
                         ├── Neo4j (Docker)
                         └── websocket ──► live graph page · Bauleiter dashboard
```

- **API** (`tagwerk/api`): uploads, job queue, websocket events, graph writes. Runs anywhere, CPU only.
- **GPU worker** (`tagwerk/worker_api.py`): speech-to-text and vision behind HTTP. Run it on the
  machine with the GPU and point `GPU_WORKER_URL` at it. If unset, the API runs those stages itself.
- **Contracts** (`contracts/`): JSON Schemas every stage must produce. `fixtures/` holds one valid
  example per contract. Stages are stubs that return fixture-shaped data until implemented.

## Quickstart (API side)

```bash
cp .env.example .env              # fill in keys; never commit .env
docker compose up -d neo4j        # graph at http://localhost:7474
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -e ".[dev]"
pytest                            # contracts + API tests, CPU only
uvicorn tagwerk.api.app:app --reload --port 8000
```

Open http://localhost:8000/upload, http://localhost:8000/graph and http://localhost:8000/dashboard.

## GPU worker (Pascal GPUs such as GTX 1060 / 1080 Ti)

```bash
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -e ".[gpu]" -c constraints-cu126.txt \
    --extra-index-url https://download.pytorch.org/whl/cu126
git clone https://github.com/Maelic/RelateAnything ../RelateAnything
uv pip install --no-deps -e ../RelateAnything   # package "relsgg"; add its missing deps by hand
python -c "import torch; print(torch.__version__)"   # must still end in +cu126
python scripts/env_check.py       # CUDA, CTranslate2 int8, YOLO, ArUco, RelateAnything
uvicorn tagwerk.worker_api:app --host 0.0.0.0 --port 8100
```

Then set `GPU_WORKER_URL=http://<gpu-host>:8100` in the API's `.env`.

Pascal rules: torch stays on the cu126 build (never cu128+), fp32 only, no `torch.compile`.

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
