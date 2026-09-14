#!/usr/bin/env python3
"""Validate `runta inspect --json` before the first Investigate.

Reads JSON from a file or stdin. Exit 0 only when capture, all four
saving flags, and the OpenAI secret injection are present.

Do not treat this as a create command. It never calls `runta run`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.runta_ready import check_inspect  # noqa: E402


def main() -> int:
    if len(sys.argv) > 1:
        raw = Path(sys.argv[1]).read_text()
    else:
        raw = sys.stdin.read()
    errors = check_inspect(json.loads(raw))
    if errors:
        for item in errors:
            print(f"FAIL {item}", file=sys.stderr)
        return 1
    print("ok: capture, four saving flags, and secret injection are on")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
