# Handoff: integrate, deploy and rehearse Tagwerk (UI v2 + Scan 3D + Tagesbericht)

You take over from the orchestrator. Work autonomously on the Linux GPU laptop. The user is about to demo.

## 1. Context
- **Tagwerk** is a hackathon project: site videos, photos and voice notes turn into element progress, a task graph, a Bauleiter dashboard and exports (P6 XML, GAEB, .ics).
- **Repo:** `github.com/Current-cmd/Tagwerk`. On the laptop it is checked out at `~/Developer/hacka/Tagwerk`, the **main checkout**: the services run from it.
- **Read first:**
  - `CLAUDE.md`
  - `docs/UI-V2-CONTRACT.md`: the spec for `/api/v2/*`, `/app`, Scan 3D and the Tagesbericht.
  - `docs/DEMO.md`
  - `docs/REVIEW-2026-11-21.md`
- **Always** `export PYTHONPATH=$PWD`. Use the venv `~/Developer/hacka/Tagwerk/.venv`, which has torch `2.14.1+cu126` and pycolmap 4.2.1. Never change torch.
- **Never** use `pkill -f`: it kills your own shell. Kill by PID or pid file only.

**Services (laptop):**

| Port | Service | Restart |
|---|---|---|
| 8100 | GPU worker | `~/tw-restart.sh` |
| 8080 | API, Hörsaal, Neo4j | `~/tw-restart.sh` |
| 8081 | API, Schependomlaan (`DATA_DIR=./data-sp CACHE_DIR=./cache-sp`, in-memory graph) | `~/tw-restart.sh` |
| 8082 | API, scan project `userwalk` (`./data-scan-userwalk`, `./cache-scan-userwalk`) | `~/tw-scanproject.sh userwalk` |

`~/tw-restart.sh` restarts 8100/8080/8081 and keeps data. Always run `~/tw-scanproject.sh userwalk` after it.

**Resets (clean demo state):**
- `.venv/bin/python scripts/reset_demo.py` resets Hörsaal and keeps `cache/`.
- `DATA_DIR=./data-sp CACHE_DIR=./cache-sp NEO4J_URI= PROJECT=schependomlaan .venv/bin/python scripts/reset_demo.py` resets Schependomlaan.
- `rm -rf data-scan-userwalk` resets the scan project (keep `cache-scan-userwalk/`).
- Then restart both service sets as above.

**Pushing:** use the askpass procedure in CLAUDE.md "Rules". The token is the `git=` line in `~/Developer/hacka/.env`; never print, log or commit it.
- **User's instruction for this handoff:** you may push `main` (fast-forward only, never force) once the integration is verified.

**The user's Mac** reaches the laptop at `100.118.181.69`. The user opens the UI on the Mac through an SSH tunnel to localhost:8080/8081/8082; it is not your job. The user decides about the tunnel.

## 2. Current state
- `origin/main` was **`58345af`** (now `a7cc367`), deployed on the laptop. All four services answer 200. It has:
  - UI v2 backend (`tagwerk/v2.py`, `/api/v2/days|day|taskgraph`)
  - the React + shadcn app built into `web/app/` and served at `/app` (source in `web-app/`)
  - the replay picker, the video-beside-graph and the bundled vendor libraries
- **Merged and archived (2026-11-22):** `feat/report`, `feat/scan3d`, `feat/integration`, `feat/core` and every other merged branch are in `main` (`a7cc367`) and were deleted. Each one is kept as a tag `archive/<branch>`; restore with `git branch <branch> archive/<branch>`. The parked `draft/orchestrator-integration` no longer exists.

### Active branches
Only these branches are still being worked on:

| Branch | Where | State |
|---|---|---|
| `main` | origin | `a7cc367`, deploy target |
| `feat/whisper-turbo` | origin | 1 commit not in `main` (`6071357`: speech large-v3-turbo on CPU int8 with fallback to small; worker warms models at startup). 9 commits behind `main`. |
| `fix/mobile-review` | Mac, local only | Based on `a7cc367`. Uncommitted work in `mobile/`. |

## 3. Tasks, in order
1. **Integrate.**
   - Create a worktree: `git worktree add ~/Developer/hacka/Tagwerk-int -b feat/integration origin/feat/core`.
   - Merge `origin/feat/report` (fast-forward), then `origin/feat/scan3d`, and resolve as above.
   - Run the full `pytest -q` and `ruff check .` (line length 130). Both must be green.
   - Run a **CI-like check** too, because GitHub Actions has no GPU, no models and no PYTHONPATH:
     - make a fresh clone or worktree
     - `uv venv --python 3.12 && uv pip install -e ".[dev]"`
     - `.venv/bin/ruff check .`, then `.venv/bin/python scripts/validate_fixtures.py`, then `.venv/bin/pytest -q`
     - Tests that post captures must monkeypatch `speech.transcribe` and `vision.analyse`.
2. **Reconcile the two halves.**
   - **`has_3d`:** `v2.py` sets it true whenever an `sfm.json` exists, failed ones included, while the report sets it only when `ok: true`. Make both use `ok: true`, with a test.
   - **German state labels:** `v2.STATE_DE` says `checked→geprüft`, while `report.py` says `checked→abgenommen`. Use one shared mapping, with `checked→abgenommen` and `tested→geprüft`.
3. **Backend items the frontend asked for.** Each needs a failing test first, and must stay in line with the contract.
   - `activities[].recordings` in `/api/v2/day`: make it `[{capture_id, date, time}]` instead of bare ids. Update `web-app/src` to read it (it currently fetches nearby days to find dates), then rebuild:
     ```bash
     cd web-app && pnpm install && pnpm build
     ```
     The build writes `web/app/`; commit it.
   - Taskgraph: emit `recording -> event` and `recording -> proposal` edges with type `RAISED` (the client adds them today as a workaround).
   - Hörsaal A1020 has `forecast_start` 2026-11-23 although it finished on 2026-11-11. A finished activity's `forecast_start`/`finish` must be its actual dates. Find out why in `project.forecast`.
4. **Deploy.**
   - Fast-forward `feat/core`, then `main`, to the integration head and push both.
   - In the main checkout: `git fetch && git merge --ff-only origin/main`, then `~/tw-restart.sh` and `~/tw-scanproject.sh userwalk`.
   - Check:
     - `/health` returns 200 on all four ports.
     - `/app` loads.
     - `/api/v2/report` returns 200 on 8080 and 8081.
     - `/export/report.html` contains "Tagesbericht".
     - `/api/v2/scan3d/uw-video` on 8082 has `ok: true`, about 30 registered frames and about 20 objects with German relations. If `cache-scan-userwalk/uw-video/sfm.json` is missing, generate it by running the sfm stage on `cache-scan-userwalk/uw-video/media/user_walk.mp4`. The backup clip is `~/Developer/hacka/demo-media/user_walk.mp4`.
   - Wait for the GitHub Actions run on `main` to pass: `gh run list -R Current-cmd/Tagwerk -L 1`.
5. **Rehearse the 3-minute demo end to end.** The flow:
   1. Film a room with voice for about 30 s and upload it.
   2. Pitch for about 2 minutes while it processes.
   3. Show `/app`: the recording, then "3D ansehen" (point cloud with tagged objects), the Live-Graph and the Tagesbericht.

   Simulate it with a real clip: upload `~/Developer/datasets/construction-video/screeding_walls_ghana_60s.mp4`, or your own room clip, to a fresh scan project or to 8082 via `/captures` with a video. Measure:
   - the time until `done`
   - the time until the `sfm` websocket step, which must be under ~120 s
   - whether `/app#/scan/<cid>` and `/app#/report/<date>` show real data, with no "Demo-Daten" badge

   Write the exact presenter steps (URLs, which project and port, what to click, fallback if SfM fails) into `docs/DEMO.md`, in a "3-Minuten-Demo" section. Then reset all projects to a clean state, keeping the caches, and restart.
6. **Open low items.** Do these only if time remains; otherwise list them in `docs/REVIEW-2026-11-21.md`.
   - `context.weather()` blocks the event loop.
   - `/api/scan` answers 409 for a taken project name only after the vision pass.
   - Untraded "Zwei Mann sind krank" gets no activity.
   - Consider raising the RelateAnything `REL_MIN_SCORE` from 0.30 to about 0.40, since many weak or nonsense relations got through on the user's walkthrough. Show before/after counts on `uw-video`.

## 4. Useful extras
- **Annotated video:** `/tmp/annotate.py` on the laptop (it may be gone after a reboot; the Mac has a copy at `/tmp/annotate.py`) draws the cached vision boxes and RelateAnything triplets onto a video:
  ```bash
  .venv/bin/python /tmp/annotate.py <cache dir of capture> <video> /tmp/out.mp4
  ```
  Then ffmpeg it to H.264 with the original audio. It was used for `uw-video`. A version using the denser SfM keyframes (`sfm.json` objects) would look better.
- **Laptop scripts:**
  - `~/tw-doubletest.sh`: full end-to-end check. It must end with FAILS=0; never run two at once.
  - `~/tw-e2e.sh`, `~/tw-userwalk.sh`.
- **Demo media:** `~/Developer/hacka/demo-media/` (`demo.mp4` for the Hörsaal replay `cap-e2e-2`, `user_walk.mp4`, `id.m4a`).

## 5. Report back
Send it to the orchestrator with `reason network send anoushk/reason-network-orchestrator-setup "<report>"`, and also show it in your session. Include:
- commits and the final `main` hash
- pytest and ruff lines, both on the laptop and in the CI-like run
- the GitHub Actions result
- the deploy checks
- the rehearsal timings (done / sfm / total)
- screenshots, if you took any
- the "3-Minuten-Demo" text
- what is left
- your context %

If your context passes 80 %, commit what is done and write `docs/HANDOFF-next.md` with what remains.
