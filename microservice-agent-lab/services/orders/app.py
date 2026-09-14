"""Orders service. Places orders by checking stock in the inventory service."""

import os
import uuid

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="orders-service")

INVENTORY_URL = os.environ.get("INVENTORY_URL", "http://localhost:8001")
REQUEST_TIMEOUT_SECS = 5.0


class OrderRequest(BaseModel):
    sku: str
    quantity: int


def fetch_inventory(sku: str) -> dict:
    """Read one SKU from the inventory service. Replaced in unit tests."""
    try:
        response = httpx.get(
            f"{INVENTORY_URL}/inventory/{sku}", timeout=REQUEST_TIMEOUT_SECS
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503, detail=f"inventory service unreachable: {exc}"
        ) from exc

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail=f"unknown sku: {sku}")
    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"inventory service returned {response.status_code}",
        )

    return response.json()


@app.get("/health")
def health():
    return {"status": "ok", "service": "orders"}


@app.post("/orders", status_code=201)
def create_order(order: OrderRequest):
    if order.quantity < 1:
        raise HTTPException(status_code=422, detail="quantity must be at least 1")

    inventory = fetch_inventory(order.sku)
    available = inventory["available"]

    if available < order.quantity:
        raise HTTPException(
            status_code=409,
            detail=(
                f"insufficient inventory for {order.sku}: "
                f"requested {order.quantity}, available {available}"
            ),
        )

    return {
        "order_id": str(uuid.uuid4()),
        "sku": order.sku,
        "quantity": order.quantity,
        "status": "confirmed",
    }
