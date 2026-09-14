#!/bin/sh
# Start or stop both services with uvicorn. Use this instead of Docker Compose
# in environments where the Docker daemon is not available, such as a Runta
# runtime built from an agent preset image.
#
# Usage: ./scripts/local-services.sh start|stop

set -eu

cd "$(dirname "$0")/.."
PIDFILE=.local-services.pids

case "${1:-}" in
start)
    if [ -f "$PIDFILE" ]; then
        echo "already running; see $PIDFILE" >&2
        exit 1
    fi
    .venv/bin/uvicorn services.inventory.app:app \
        --host 127.0.0.1 --port 8001 > /tmp/inventory.log 2>&1 &
    echo $! > "$PIDFILE"
    INVENTORY_URL=http://127.0.0.1:8001 .venv/bin/uvicorn services.orders.app:app \
        --host 127.0.0.1 --port 8002 > /tmp/orders.log 2>&1 &
    echo $! >> "$PIDFILE"
    echo "started; logs at /tmp/inventory.log and /tmp/orders.log"
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
