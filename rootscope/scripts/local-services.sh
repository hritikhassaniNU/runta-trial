#!/bin/sh
# Start or stop inventory, orders, and the RootScope API with uvicorn.
# Use this when Compose image builds fail (Runta Docker builds lack the egress CA).

set -eu

cd "$(dirname "$0")/.."
PIDFILE=.local-services.pids
export PYTHONPATH="${PWD}:${PWD}/demo-system:${PWD}/apps/api${PYTHONPATH:+:$PYTHONPATH}"
export ROOTSCOPE_DATABASE="${ROOTSCOPE_DATABASE:-$PWD/data/rootscope.db}"
if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    . ./.env
    set +a
fi
export INVENTORY_URL="${INVENTORY_URL:-http://127.0.0.1:8001}"

# Written by scripts/apply-incident.sh config. Wins over the default above.
if [ -f demo-system/incidents/.env.local ]; then
    # shellcheck disable=SC1091
    . demo-system/incidents/.env.local
fi

case "${1:-}" in
start)
    if [ -f "$PIDFILE" ]; then
        echo "already running; see $PIDFILE" >&2
        exit 1
    fi
    # Start in a new session so the services survive the parent shell exiting.
    start_daemon() {
        log="$1"
        shift
        .venv/bin/python -c "
import subprocess, sys
log = open(sys.argv[1], 'w')
proc = subprocess.Popen(sys.argv[2:], stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
print(proc.pid)
" "$log" "$@"
    }
    start_daemon /tmp/inventory.log .venv/bin/uvicorn inventory.app:app --host 127.0.0.1 --port 8001 > "$PIDFILE"
    INVENTORY_URL="$INVENTORY_URL" start_daemon /tmp/orders.log .venv/bin/uvicorn orders.app:app --host 127.0.0.1 --port 8002 >> "$PIDFILE"
    start_daemon /tmp/rootscope-api.log .venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 >> "$PIDFILE"
    echo "started; logs at /tmp/inventory.log /tmp/orders.log /tmp/rootscope-api.log"
    ;;
stop)
    if [ ! -f "$PIDFILE" ]; then
        echo "not running"
        exit 0
    fi
    while read -r pid; do
        kill "$pid" 2>/dev/null || true
    done < "$PIDFILE"
    rm -f "$PIDFILE"
    echo "stopped"
    ;;
*)
    echo "usage: $0 start|stop" >&2
    exit 2
    ;;
esac
