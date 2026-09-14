"""Inventory service. Owns stock and publishes the inventory contract."""

from fastapi import FastAPI, HTTPException

app = FastAPI(title="inventory-service")

STOCK = {
    "ABC": 10,
    "XYZ": 3,
    "OUT": 0,
}


@app.get("/health")
def health():
    return {"status": "ok", "service": "inventory"}


@app.get("/inventory/{sku}")
def get_inventory(sku: str):
    if sku not in STOCK:
        raise HTTPException(status_code=404, detail=f"unknown sku: {sku}")
    return {"sku": sku, "available": STOCK[sku]}
