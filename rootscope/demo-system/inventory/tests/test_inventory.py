import json
from pathlib import Path

from fastapi.testclient import TestClient

from inventory.app import app

CONTRACT_PATH = (
    Path(__file__).resolve().parents[2] / "contracts" / "inventory-contract.json"
)
JSON_TYPES = {"string": str, "integer": int}

client = TestClient(app)


def test_health_reports_service_name():
    assert client.get("/health").json()["service"] == "inventory"


def test_known_sku_returns_availability():
    response = client.get("/inventory/ABC")
    assert response.status_code == 200
    assert response.json() == {"sku": "ABC", "available": 10}


def test_unknown_sku_returns_404():
    assert client.get("/inventory/NOPE").status_code == 404


def test_response_matches_published_contract():
    contract = json.loads(CONTRACT_PATH.read_text())["response"]
    body = client.get("/inventory/ABC").json()
    assert set(body) == set(contract["required"])
    for field, spec in contract["properties"].items():
        assert isinstance(body[field], JSON_TYPES[spec["type"]])
