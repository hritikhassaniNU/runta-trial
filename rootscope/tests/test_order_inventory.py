import os

import httpx
import pytest

INVENTORY_URL = os.environ.get("INVENTORY_URL", "http://localhost:8001")
ORDERS_URL = os.environ.get("ORDERS_URL", "http://localhost:8002")
TIMEOUT_SECS = 5.0


@pytest.fixture(scope="session", autouse=True)
def both_services_are_reachable():
    for name, url in (("inventory", INVENTORY_URL), ("orders", ORDERS_URL)):
        try:
            httpx.get(f"{url}/health", timeout=TIMEOUT_SECS).raise_for_status()
        except httpx.HTTPError as exc:
            pytest.fail(f"{name} service is not reachable at {url}: {exc}")


def test_inventory_reports_availability():
    body = httpx.get(f"{INVENTORY_URL}/inventory/ABC", timeout=TIMEOUT_SECS).json()
    assert body["sku"] == "ABC"
    assert body["available"] == 10


def test_order_succeeds_end_to_end():
    response = httpx.post(
        f"{ORDERS_URL}/orders", json={"sku": "ABC", "quantity": 2}, timeout=TIMEOUT_SECS
    )
    assert response.status_code == 201, response.text
    assert response.json()["status"] == "confirmed"


def test_order_rejected_when_requesting_more_than_available():
    response = httpx.post(
        f"{ORDERS_URL}/orders", json={"sku": "XYZ", "quantity": 99}, timeout=TIMEOUT_SECS
    )
    assert response.status_code == 409, response.text


def test_unknown_sku_propagates_as_404():
    response = httpx.post(
        f"{ORDERS_URL}/orders", json={"sku": "NOPE", "quantity": 1}, timeout=TIMEOUT_SECS
    )
    assert response.status_code == 404, response.text
