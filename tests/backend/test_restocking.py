"""Tests for the restocking recommendation and order endpoints."""
import main


def test_zero_budget_recommends_nothing(client):
    r = client.get("/api/restocking/recommendations", params={"budget": 0})
    assert r.status_code == 200
    assert r.json()["items"] == []


def test_recommendations_respect_budget(client):
    data = client.get("/api/restocking/recommendations", params={"budget": 5000}).json()
    assert data["items"]
    assert data["total_cost"] <= 5000
    assert data["remaining_budget"] == round(5000 - data["total_cost"], 2)
    assert data["lead_time_days"] == max(i["lead_time_days"] for i in data["items"])


def test_negative_budget_rejected(client):
    assert client.get("/api/restocking/recommendations", params={"budget": -1}).status_code == 400


def test_place_order_rejects_unaffordable_budget(client):
    assert client.post("/api/restocking/orders", json={"budget": 0}).status_code == 400


def test_place_order_appears_in_submitted_orders(client):
    main.submitted_restocking_orders.clear()
    r = client.post("/api/restocking/orders", json={"budget": 25000})
    assert r.status_code == 201
    order = r.json()
    assert order["status"] == "Submitted"
    assert order["lead_time_days"] > 0
    listed = client.get("/api/restocking/orders").json()
    assert [o["id"] for o in listed] == [order["id"]]
    main.submitted_restocking_orders.clear()
