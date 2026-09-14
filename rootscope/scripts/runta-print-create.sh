#!/bin/sh
# Print the REST create command used for the final RootScope runtime.
# This script does not create a runtime.

set -eu
cd "$(dirname "$0")/.."

cat <<EOF2
Before creating the runtime:
  1. replace REPLACE_WITH_RUNTA_SECRET_ID in deploy/create-runtime.json
  2. export RUNTA_TOKEN in your shell

Create command:

curl -sS \\
  -X POST \\
  -H "Authorization: Bearer \$RUNTA_TOKEN" \\
  -H "Content-Type: application/json" \\
  --data-binary @$PWD/deploy/create-runtime.json \\
  https://api.runta.com/v2/runtimes

Then verify the effective runtime policy with:
  runta inspect rootscope --json > /tmp/rootscope-inspect.json
  python3 $PWD/scripts/runta-inspect-check.py /tmp/rootscope-inspect.json
EOF2
