# Demo runbook (laptop)

All commands in `~/Developer/hacka/Tagwerk`, with `export PYTHONPATH=$PWD`.

## Before the slot
1. Plug in, disable suspend (a resume can break CUDA: `cuInit 999`; fix = stop gnome-remote-desktop,
   `sudo rmmod nvidia_uvm && sudo modprobe nvidia_uvm`).
2. `docker compose up -d neo4j`
3. Reset to the seeded state (keeps cached clips for replay): `.venv/bin/python scripts/reset_demo.py`
4. `~/tw-restart.sh` and check `curl localhost:8080/health` shows `"graph":"Neo4jStore"`.
5. Warm the models once with a throwaway clip (first run loads Whisper/YOLO/RelateAnything, ~10 s extra), then
   reset again (step 3) and restart (step 4).
6. Open `/graph` on the projector, `/dashboard` in a second tab, `/upload` on the phone
   (`http://<laptop-ip>:8080/upload`, same Wi-Fi or Tailscale `100.118.181.69`).

## During the demo
- Filmed walk: upload the clip from the phone/laptop, or replay its cached run:
  `.venv/bin/python scripts/replay.py <capture_id>` (`--list` shows what is cached). Replay needs no GPU,
  network or Claude.
- Live: photo + short voice note from the phone. Phrases that change the freshly reset demo state (checked by
  `tests/test_demo_phrases.py`): "Stuhlreihe A ist montiert", "Reihen F bis H Unterkonstruktion",
  "zwei Mann vom Trockenbau sind krank", "Lautsprecher links und rechts angeschlossen", "die Leinwand ist in Betrieb",
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
3. Replay the cached roof note: `curl -X POST localhost:8081/captures -F replay_of=sp-demo-roof`.
   The open dashboard updates live: 32 `sporenkap` elements confirmed, Ist 83.7 → 84.6 %, SPI 1.09 → 1.10,
   ST01130 2 → 34.7 %, 2× Timmerman absent. The forecast stays 15.10.2015 (ST01130 is far ahead of plan).
4. If `cache-sp/sp-demo-roof` is missing (fresh checkout; `cache-*` is gitignored), create it once with the typed
   note, then reset (step 1):
   `curl -X POST localhost:8081/captures -F capture_id=sp-demo-roof -F zone_id=Z-3 -F "note=Sporenkap derde verdieping geplaatst. Twee timmerlieden ziek."`
Do not replay `sp-live-1` for this: its storey-02 walls are already installed, so nothing moves.

## Fallbacks
1. Live upload fails: stay on replay.
2. GPU worker down: the API runs speech/vision in-process automatically (slower).
3. Everything down: backup screen recording.
