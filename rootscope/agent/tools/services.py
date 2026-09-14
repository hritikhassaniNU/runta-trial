"""check_service. HTTP GET to demo hosts only."""

from __future__ import annotations

from typing import Optional
from urllib.parse import urlparse

import httpx

from agent.workspace import ToolError

NAMED = {
    "inventory": "http://127.0.0.1:8001/health",
    "orders": "http://127.0.0.1:8002/health",
    "api": "http://127.0.0.1:8000/health",
    "inventory_sku": "http://127.0.0.1:8001/inventory/ABC",
}

ALLOWED_HOSTS = {"127.0.0.1", "localhost"}
ALLOWED_PORTS = {8000, 8001, 8002, 9001}


def check_service(name: Optional[str] = None, url: Optional[str] = None) -> str:
    target = url or NAMED.get(name or "")
    if not target:
        raise ToolError(
            "provide name (inventory|orders|api|inventory_sku) or a localhost URL"
        )
    _assert_allowed_url(target)
    try:
        response = httpx.get(target, timeout=3.0)
    except httpx.HTTPError as exc:
        return f"GET {target} unreachable: {exc}"
    body = response.text[:800]
    return f"GET {target} -> {response.status_code}\n{body}"


def _assert_allowed_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "http":
        raise ToolError("only http to demo hosts is allowed")
    if parsed.hostname not in ALLOWED_HOSTS:
        raise ToolError("host is not allowed")
    port = parsed.port or 80
    if port not in ALLOWED_PORTS:
        raise ToolError("port is not allowed")
