#!/bin/sh
# Start inventory :8001, orders :8002, API :8000, and Next.js :3000.
# Use this inside a Runta runtime after the tree is copied. Do not use
# Docker Compose there — image builds fail TLS on the egress CA.
# This script never calls `runta run`.

set -eu

cd "$(dirname "$0")/.."
export OPENAI_MODEL="${OPENAI_MODEL:-gpt-4.1}"
export API_UPSTREAM="${API_UPSTREAM:-http://127.0.0.1:8000}"
WEB_PIDFILE=.runta-web.pid

if [ ! -x .venv/bin/python ]; then
    echo "missing .venv; run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
    exit 1
fi
if [ ! -d apps/web/node_modules ]; then
    echo "missing apps/web/node_modules; run: cd apps/web && npm install" >&2
    exit 1
fi

mkdir -p data

if [ -f .local-services.pids ]; then
    echo "backend already running; see .local-services.pids"
else
    ./scripts/local-services.sh start
fi

if [ -f "$WEB_PIDFILE" ]; then
    echo "web already running; see $WEB_PIDFILE"
else
    .venv/bin/python -c "
import subprocess, sys
log = open(sys.argv[1], 'w')
proc = subprocess.Popen(sys.argv[2:], stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
print(proc.pid)
" /tmp/rootscope-web.log /usr/bin/env npm --prefix apps/web run dev > "$WEB_PIDFILE"
    echo "web started; log at /tmp/rootscope-web.log"
fi

i=0
while [ "$i" -lt 30 ]; do
    if ./scripts/runta-health.sh >/dev/null 2>&1; then
        ./scripts/runta-health.sh
        echo "public later: https://3000-<runtime_id>.runta.dev"
        exit 0
    fi
    i=$((i + 1))
    sleep 1
done

echo "services did not become healthy; last check:" >&2
./scripts/runta-health.sh || true
exit 1
