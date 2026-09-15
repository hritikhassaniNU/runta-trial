#!/bin/sh
# Wait for a Runta image build to finish, then boot a runtime from it and
# confirm the baked-in proof file is present.
#
# Usage: ./verify-image.sh <BUILD_ID> [RUNTIME_NAME]

set -eu

BUILD_ID="${1:?usage: verify-image.sh <BUILD_ID> [RUNTIME_NAME]}"
RUNTIME_NAME="${2:-repo-doctor-image-check}"
IMAGE_ID="custom-$BUILD_ID"

while :; do
    STATUS="$(runta image build ls --json \
        | python3 -c 'import json,sys;b=json.load(sys.stdin)["builds"];print(next((x["status"] for x in b if x["id"]==sys.argv[1]),"gone"))' "$BUILD_ID")"
    printf '%s %s\n' "$(date -u +%H:%M:%SZ)" "$STATUS"
    case "$STATUS" in
        succeeded) break ;;
        failed|cancelled|gone) echo "build did not succeed: $STATUS" >&2; exit 1 ;;
    esac
    sleep 30
done

runta run --name "$RUNTIME_NAME" --cpus 1 --memory 512 --image "$IMAGE_ID"
runta exec "$RUNTIME_NAME" -- sh -lc 'cat /opt/runta-image-proof.txt 2>/dev/null || cat /workspace/IMAGE_BUILD_PROOF.txt'
runta exec "$RUNTIME_NAME" -- sh -lc 'python3 --version && (pytest --version || true)'
