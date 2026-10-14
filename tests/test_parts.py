"""API tests. Each test gets its own fresh temporary database."""
import pytest
from fastapi.testclient import TestClient
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from app.database import get_connection, init_db
from app.main import app, get_db

PUMP = {
    "part_number": "PMP-4410",
    "name": "Seawater cooling pump impeller",
    "category": "Pumps",
    "quantity_on_hand": 5,
    "reorder_level": 2,
    "lead_time_days": 21,
    "supplier": "Atlantic Marine Supply",
}


@pytest.fixture
def client(tmp_path):
    db_file = tmp_path / "test.db"
    init_db(db_file)

    def override_get_db():
        conn = get_connection(db_file)
        try:
            yield conn
        finally:
            conn.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_create_and_get_part(client):
    res = client.post("/parts", json=PUMP)
    assert res.status_code == 201
    part_id = res.json()["id"]

    res = client.get(f"/parts/{part_id}")
    assert res.status_code == 200
    assert res.json()["part_number"] == "PMP-4410"


def test_duplicate_part_number_returns_409(client):
    client.post("/parts", json=PUMP)
    assert client.post("/parts", json=PUMP).status_code == 409


def test_invalid_input_returns_422(client):
    bad = {**PUMP, "quantity_on_hand": -3}
    assert client.post("/parts", json=bad).status_code == 422


def test_missing_part_returns_404(client):
    assert client.get("/parts/999").status_code == 404


def test_filter_by_category(client):
    client.post("/parts", json=PUMP)
    client.post("/parts", json={**PUMP, "part_number": "FLT-100", "category": "Filters"})
    res = client.get("/parts", params={"category": "Filters"})
    assert [p["part_number"] for p in res.json()] == ["FLT-100"]


def test_patch_updates_only_given_fields(client):
    part_id = client.post("/parts", json=PUMP).json()["id"]
    res = client.patch(f"/parts/{part_id}", json={"supplier": "North Sea Parts Ltd"})
    assert res.status_code == 200
    assert res.json()["supplier"] == "North Sea Parts Ltd"
    assert res.json()["name"] == PUMP["name"]  # unchanged


def test_stock_adjustment(client):
    part_id = client.post("/parts", json=PUMP).json()["id"]
    res = client.post(f"/parts/{part_id}/stock", json={"change": -3})
    assert res.json()["quantity_on_hand"] == 2


def test_stock_cannot_go_negative(client):
    part_id = client.post("/parts", json=PUMP).json()["id"]
    res = client.post(f"/parts/{part_id}/stock", json={"change": -10})
    assert res.status_code == 400
    assert client.get(f"/parts/{part_id}").json()["quantity_on_hand"] == 5  # unchanged
    
def test_stock_can_be_removed_down_to_exactly_zero(client):
    part_id = client.post("/parts", json=PUMP).json()["id"]  # starts at 5
    res = client.post(f"/parts/{part_id}/stock", json={"change": -5})
    assert res.status_code == 200
    assert res.json()["quantity_on_hand"] == 0
    # one more removal must now be rejected
    assert client.post(f"/parts/{part_id}/stock", json={"change": -1}).status_code == 400


def test_stock_adjustment_on_missing_part_returns_404(client):
    assert client.post("/parts/999/stock", json={"change": 1}).status_code == 404


def test_concurrent_removals_never_oversell(client):
    """Fire many simultaneous -1 requests at a part with limited stock.
    Exactly `stock` of them may succeed; the rest must be rejected."""
    stock, attempts = 10, 20
    part_id = client.post("/parts", json={**PUMP, "quantity_on_hand": stock}).json()["id"]
    barrier = threading.Barrier(attempts)

    def remove_one(_):
        own_client = TestClient(app)  # one client per thread; the DB override on `app` still applies
        barrier.wait(timeout=10)      # hold every thread here, then release them all at once
        return own_client.post(f"/parts/{part_id}/stock", json={"change": -1}).status_code

    with ThreadPoolExecutor(max_workers=attempts) as pool:
        codes = list(pool.map(remove_one, range(attempts)))

    assert codes.count(200) == stock
    assert codes.count(400) == attempts - stock
    assert client.get(f"/parts/{part_id}").json()["quantity_on_hand"] == 0

def test_low_stock_sorted_by_lead_time(client):
    client.post("/parts", json={**PUMP, "part_number": "A", "quantity_on_hand": 1, "lead_time_days": 5})
    client.post("/parts", json={**PUMP, "part_number": "B", "quantity_on_hand": 0, "lead_time_days": 60})
    client.post("/parts", json={**PUMP, "part_number": "C", "quantity_on_hand": 10})  # healthy stock
    res = client.get("/parts/low-stock")
    assert [p["part_number"] for p in res.json()] == ["B", "A"]


def test_delete_part(client):
    part_id = client.post("/parts", json=PUMP).json()["id"]
    assert client.delete(f"/parts/{part_id}").status_code == 204
    assert client.get(f"/parts/{part_id}").status_code == 404
