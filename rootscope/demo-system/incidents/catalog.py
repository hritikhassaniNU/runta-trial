"""Single source for demo incident metadata. Used by the API and the apply script."""

from typing import Dict

CONFIG_INVENTORY_URL = "http://127.0.0.1:9001"

DEMOS: Dict[str, dict] = {
    "contract": {
        "key": "contract",
        "title": "Contract Regression",
        "description": "Orders started returning 500 after the inventory deployment.",
        "expected_signal": (
            "POST /orders returns 500. Inventory now publishes available_quantity; "
            "orders still reads available. The published contract and the inventory "
            "unit test both fail."
        ),
        "apply_command": "./scripts/apply-incident.sh contract",
        "reset_command": "./scripts/apply-incident.sh reset",
        "needs_restart": True,
    },
    "config": {
        "key": "config",
        "title": "Configuration Failure",
        "description": "Orders cannot reach inventory. Health checks fail on the configured URL.",
        "expected_signal": (
            "POST /orders returns 503 (inventory unreachable). Orders is pointed at "
            f"{CONFIG_INVENTORY_URL} instead of :8001. Inventory itself is healthy."
        ),
        "apply_command": "./scripts/apply-incident.sh config",
        "reset_command": "./scripts/apply-incident.sh reset",
        "needs_restart": True,
    },
    "noisy": {
        "key": "noisy",
        "title": "Noisy Logs",
        "description": "Production logs are huge and repetitive. Something is failing, buried in noise.",
        "expected_signal": (
            "demo-system/logs/orders.log has thousands of heartbeat lines and exactly "
            "one ERROR (KeyError: 'available'). A tail of the last 50 lines misses it."
        ),
        "apply_command": "./scripts/apply-incident.sh noisy",
        "reset_command": "./scripts/apply-incident.sh reset",
        "needs_restart": False,
    },
}
