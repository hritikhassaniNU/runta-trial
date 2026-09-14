"""Inventory overlay for the contract incident. Not the happy-path service.

The published contract and orders still use `available`. This response uses
`available_quantity`, which is the break.
"""

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
    return {"sku": sku, "available_quantity": STOCK[sku]}
