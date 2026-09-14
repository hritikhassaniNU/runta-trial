#!/bin/sh
# Apply or reset a demo incident, then restart uvicorn services when needed.
# Run from anywhere; the script cds to rootscope/.

set -eu

cd "$(dirname "$0")/.."
export PYTHONPATH="${PWD}/demo-system${PYTHONPATH:+:$PYTHONPATH}"

ACTION="${1:-}"
case "$ACTION" in
contract|config|noisy|reset|status)
    ;;
*)
    echo "usage: $0 contract|config|noisy|reset|status" >&2
    exit 2
    ;;
esac

.venv/bin/python -m incidents.apply "$ACTION"

if [ "$ACTION" = "status" ]; then
    exit 0
fi

if [ "$ACTION" = "noisy" ]; then
    echo "noisy log written; services do not need a restart"
    exit 0
fi

if [ -f .local-services.pids ]; then
    ./scripts/local-services.sh stop
    ./scripts/local-services.sh start
else
    echo "services were not running; start with ./scripts/local-services.sh start"
fi
