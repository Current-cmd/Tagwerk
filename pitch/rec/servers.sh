#!/bin/sh
# Servers for the dashboard recordings (no GPU, no Neo4j, no stubs).
#   pitch/rec/servers.sh reset   stop :8080, reset Hörsaal to the seeded on-plan state, start :8080 again
#   pitch/rec/servers.sh start   start whatever is not running (:8080 Hörsaal, :8081 Schependomlaan)
#   pitch/rec/servers.sh stop    stop both
cd "$(dirname "$0")/../.." || exit 1
export TAGWERK_DEV=1 NEO4J_URI= PYTHONPATH=.
stop() { p=$(lsof -ti "tcp:$1" -sTCP:LISTEN); [ -n "$p" ] && kill $p && sleep 1; return 0; }
wait_up() { for i in $(seq 1 60); do curl -sf "localhost:$1/health" >/dev/null && return 0; sleep 0.5; done; echo "port $1 did not come up" >&2; return 1; }
hs() { lsof -ti tcp:8080 -sTCP:LISTEN >/dev/null || nohup .venv/bin/uvicorn tagwerk.api.app:app --port 8080 >/tmp/tw-8080.log 2>&1 & wait_up 8080; }
sp() { lsof -ti tcp:8081 -sTCP:LISTEN >/dev/null || PROJECT=schependomlaan DATA_DIR=./data-sp CACHE_DIR=./cache-sp nohup .venv/bin/uvicorn tagwerk.api.app:app --port 8081 >/tmp/tw-8081.log 2>&1 & wait_up 8081; }
case "$1" in
  reset) stop 8080; .venv/bin/python scripts/reset_demo.py && rm -rf cache/walk-2611 && hs ;;
  start) hs && sp ;;
  stop) stop 8080; stop 8081 ;;
  *) echo "usage: $0 reset|start|stop" >&2; exit 2 ;;
esac
