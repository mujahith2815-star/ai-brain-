import pytest

def test_inventory_mock_data():
    items = [
        {"id": "item-001", "name": "ESP32-WROOM-32", "qty": 42},
        {"id": "item-002", "name": "BC547 NPN Transistor", "qty": 250}
    ]
    assert len(items) == 2
    assert items[0]["qty"] > 0
    assert items[1]["name"] == "BC547 NPN Transistor"
