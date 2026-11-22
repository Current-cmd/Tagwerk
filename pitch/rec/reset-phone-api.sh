#!/bin/sh
# Stops the phone-recording API (:8090), wipes its state and starts it again in the seeded state.
cd "$(dirname "$0")/../.." || exit 1
lsof -ti tcp:8090 -sTCP:LISTEN | xargs kill 2>/dev/null; sleep 1
rm -rf data-phone cache-phone
TAGWERK_DEV=1 NEO4J_URI= DATA_DIR=./data-phone CACHE_DIR=./cache-phone PYTHONPATH=. nohup .venv/bin/uvicorn tagwerk.api.app:app --port 8090 > /tmp/tw-phone-api.log 2>&1 &
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do curl -sf localhost:8090/health >/dev/null && break; sleep 1; done
curl -s localhost:8090/health; echo
