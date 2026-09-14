#!/bin/sh
# Check the four RootScope ports. Safe to run locally or inside a runtime.
# Does not create a Runta runtime.

set -eu

fail=0
check() {
    name="$1"
    url="$2"
    expect="$3"
    got="$(python3 -c "
import json, sys, urllib.request
try:
    body = urllib.request.urlopen(sys.argv[1], timeout=3).read()
    print(json.loads(body).get('service', ''))
except Exception:
    print('')
" "$url")"
    if [ "$got" = "$expect" ]; then
        echo "ok  $name  $url"
    else
        echo "FAIL $name  $url  -> ${got:-unreachable}" >&2
        fail=1
    fi
}

check inventory "http://127.0.0.1:8001/health" inventory
check orders    "http://127.0.0.1:8002/health" orders
check api       "http://127.0.0.1:8000/health" rootscope-api
check web       "http://127.0.0.1:3000/health" rootscope-api

exit "$fail"
