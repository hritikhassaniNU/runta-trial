import json
from pathlib import Path

from fastapi.testclient import TestClient

import orders.app as orders_module
from incidents.catalog import CONFIG_INVENTORY_URL
from incidents.contract.inventory_app import app as broken_inventory
from incidents.noisy import (
    DEFAULT_ERROR_INDEX,
    ERROR_LINE,
    error_lines,
    generate_log,
)
from inventory.app import app as happy_inventory

CONTRACT_PATH = (
    Path(__file__).resolve().parents[2] / "contracts" / "inventory-contract.json"
)

happy_client = TestClient(happy_inventory)
broken_client = TestClient(broken_inventory)
orders_client = TestClient(orders_module.app)


def test_happy_path_inventory_still_matches_contract():
    contract = json.loads(CONTRACT_PATH.read_text())["response"]
    body = happy_client.get("/inventory/ABC").json()
    assert set(body) == set(contract["required"])
    assert "available" in body
    assert "available_quantity" not in body


def test_contract_overlay_renames_availability_field():
    body = broken_client.get("/inventory/ABC").json()
    assert body == {"sku": "ABC", "available_quantity": 10}
    contract = json.loads(CONTRACT_PATH.read_text())["response"]
    assert set(body) != set(contract["required"])
    assert "available" not in body


def test_orders_returns_500_when_inventory_uses_new_field(monkeypatch):
    monkeypatch.setattr(
        orders_module,
        "fetch_inventory",
        lambda sku: broken_client.get(f"/inventory/{sku}").json(),
    )
    # uvicorn turns the unhandled KeyError into 500; TestClient re-raises unless asked not to.
    client = TestClient(orders_module.app, raise_server_exceptions=False)
    response = client.post("/orders", json={"sku": "ABC", "quantity": 1})
    assert response.status_code == 500


def test_config_incident_cannot_reach_inventory(monkeypatch):
    monkeypatch.setattr(orders_module, "INVENTORY_URL", CONFIG_INVENTORY_URL)
    response = orders_client.post("/orders", json={"sku": "ABC", "quantity": 1})
    assert response.status_code == 503
    assert "unreachable" in response.json()["detail"]


def test_noisy_log_buries_the_real_error(tmp_path):
    path = generate_log(tmp_path / "orders.log")
    lines = path.read_text().splitlines()
    assert len(lines) >= 3000
    found = error_lines(path)
    assert found == [ERROR_LINE]
    assert ERROR_LINE not in lines[-50:]
    assert lines[DEFAULT_ERROR_INDEX] == ERROR_LINE
