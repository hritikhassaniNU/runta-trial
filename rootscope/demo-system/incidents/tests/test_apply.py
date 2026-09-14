from pathlib import Path

from incidents.apply import apply, read_active, reset
from incidents.catalog import CONFIG_INVENTORY_URL
from incidents.noisy import ERROR_LINE

HAPPY = 'return {"sku": sku, "available": STOCK[sku]}\n'
BROKEN = 'return {"sku": sku, "available_quantity": STOCK[sku]}\n'


def _tree(tmp_path: Path) -> Path:
    inventory = tmp_path / "demo-system" / "inventory"
    incidents = tmp_path / "demo-system" / "incidents" / "contract"
    inventory.mkdir(parents=True)
    incidents.mkdir(parents=True)
    (inventory / "app.py").write_text(HAPPY)
    (incidents / "inventory_app.py").write_text(BROKEN)
    return tmp_path


def test_apply_contract_overlays_and_reset_restores(tmp_path):
    root = _tree(tmp_path)
    live = root / "demo-system" / "inventory" / "app.py"

    apply("contract", root=root)
    assert read_active(root) == "contract"
    assert "available_quantity" in live.read_text()
    assert (root / "demo-system" / "inventory" / "app.py.happy").exists()

    reset(root)
    assert read_active(root) is None
    assert live.read_text() == HAPPY
    assert not (root / "demo-system" / "inventory" / "app.py.happy").exists()


def test_apply_config_writes_env_and_clears_previous_overlay(tmp_path):
    root = _tree(tmp_path)
    apply("contract", root=root)
    apply("config", root=root)

    assert read_active(root) == "config"
    env = (root / "demo-system" / "incidents" / ".env.local").read_text()
    assert CONFIG_INVENTORY_URL in env
    assert (root / "demo-system" / "inventory" / "app.py").read_text() == HAPPY


def test_apply_noisy_writes_findable_error(tmp_path):
    root = _tree(tmp_path)
    apply("noisy", root=root)
    log = root / "demo-system" / "logs" / "orders.log"
    assert ERROR_LINE in log.read_text()
    reset(root)
    assert not log.exists()
