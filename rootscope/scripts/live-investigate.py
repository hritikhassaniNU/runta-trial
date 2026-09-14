"""One live investigation against the contract fixture. Does not print secrets."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request

from agent.workspace import load_dotenv, workspace_root


def _req(method: str, path: str, body=None):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        f"http://127.0.0.1:8000{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode())


def main() -> int:
    root = workspace_root()
    load_dotenv(root / ".env")
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set", file=sys.stderr)
        return 1
    model = os.environ.get("OPENAI_MODEL") or "gpt-4.1"
    print(f"model={model} key=set")

    subprocess.check_call(["./scripts/apply-incident.sh", "contract"], cwd=root)
    time.sleep(0.8)
    try:
        created = _req("POST", "/api/incidents", {"demo_key": "contract"})
        incident_id = created["id"]
        print(f"incident={incident_id}")
        _req("POST", f"/api/incidents/{incident_id}/investigate")
        for _ in range(90):
            time.sleep(2)
            detail = _req("GET", f"/api/incidents/{incident_id}")
            print(f"status={detail['status']} events={len(detail.get('events') or [])}")
            if detail["status"] in {"diagnosed", "failed"}:
                diagnosis = detail.get("diagnosis") or {}
                print(f"confidence={diagnosis.get('confidence')}")
                print(f"root_cause={diagnosis.get('root_cause')}")
                return 0 if detail["status"] == "diagnosed" else 2
        print("timed out", file=sys.stderr)
        return 3
    finally:
        subprocess.call(["./scripts/apply-incident.sh", "reset"], cwd=root)


if __name__ == "__main__":
    sys.exit(main())
