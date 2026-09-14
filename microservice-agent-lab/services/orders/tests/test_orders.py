from fastapi.testclient import TestClient

from services.orders import app as orders_module

client = TestClient(orders_module.app)


def stub_inventory(monkeypatch, payload):
    monkeypatch.setattr(orders_module, "fetch_inventory", lambda sku: payload)


def test_health_reports_service_name():
    assert client.get("/health").json()["service"] == "orders"


def test_order_confirmed_when_stock_is_sufficient(monkeypatch):
    stub_inventory(monkeypatch, {"sku": "ABC", "available": 10})

    response = client.post("/orders", json={"sku": "ABC", "quantity": 2})

    assert response.status_code == 201
    body = response.json()
    assert body["sku"] == "ABC"
    assert body["quantity"] == 2
    assert body["status"] == "confirmed"


def test_order_rejected_when_stock_is_insufficient(monkeypatch):
    stub_inventory(monkeypatch, {"sku": "XYZ", "available": 1})

    response = client.post("/orders", json={"sku": "XYZ", "quantity": 5})

    assert response.status_code == 409


def test_quantity_below_one_is_rejected():
    assert client.post("/orders", json={"sku": "ABC", "quantity": 0}).status_code == 422
