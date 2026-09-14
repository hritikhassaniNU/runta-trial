#!/bin/sh
# Stop Next.js (if this script started it) and the three uvicorn services.

set -eu

cd "$(dirname "$0")/.."
WEB_PIDFILE=.runta-web.pid

if [ -f "$WEB_PIDFILE" ]; then
    while read -r pid; do
        kill "$pid" 2>/dev/null || true
    done < "$WEB_PIDFILE"
    rm -f "$WEB_PIDFILE"
    echo "web stopped"
else
    echo "web not started by runta-start.sh"
fi

./scripts/local-services.sh stop
