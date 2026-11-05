"""
Tests for tasks and purchase order API endpoints.
"""
import pytest


def _po_payload(backlog_item_id, **overrides):
    payload = {
        "backlog_item_id": backlog_item_id,
        "supplier_name": "Acme Supply",
        "quantity": 100,
        "unit_cost": 12.5,
        "expected_delivery_date": "2025-12-01",
        "notes": "test",
    }
    payload.update(overrides)
    return payload


class TestTasksEndpoints:
    """Test suite for task endpoints."""

    def test_get_tasks(self, client):
        """Test getting all tasks."""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_create_toggle_delete_task(self, client):
        """Test the full task lifecycle."""
        response = client.post(
            "/api/tasks",
            json={"title": "Check stock", "priority": "high", "dueDate": "2025-11-01"},
        )
        assert response.status_code == 201
        task = response.json()
        assert task["title"] == "Check stock"
        assert task["status"] == "pending"
        task_id = task["id"]

        assert any(t["id"] == task_id for t in client.get("/api/tasks").json())

        response = client.patch(f"/api/tasks/{task_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "completed"

        response = client.patch(f"/api/tasks/{task_id}")
        assert response.json()["status"] == "pending"

        response = client.delete(f"/api/tasks/{task_id}")
        assert response.status_code == 200
        assert not any(t["id"] == task_id for t in client.get("/api/tasks").json())

    def test_create_task_missing_fields(self, client):
        """Test that missing required fields are rejected."""
        response = client.post("/api/tasks", json={"title": "No due date"})
        assert response.status_code == 422

    def test_nonexistent_task(self, client):
        """Test toggling and deleting a task that doesn't exist."""
        for response in (client.patch("/api/tasks/999999"), client.delete("/api/tasks/999999")):
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()


class TestPurchaseOrderEndpoints:
    """Test suite for purchase order endpoints."""

    def _free_backlog_id(self, client):
        items = client.get("/api/backlog").json()
        free = [b for b in items if not b["has_purchase_order"]]
        if not free:
            pytest.skip("No backlog item without a purchase order left")
        return free[0]["id"]

    def test_create_and_get_purchase_order(self, client):
        """Test creating a PO and fetching it by backlog item."""
        backlog_id = self._free_backlog_id(client)

        response = client.post("/api/purchase-orders", json=_po_payload(backlog_id))
        assert response.status_code == 201
        po = response.json()
        assert po["backlog_item_id"] == backlog_id
        assert po["status"] == "pending"
        assert po["id"].startswith("PO-")

        response = client.get(f"/api/purchase-orders/{backlog_id}")
        assert response.status_code == 200
        assert response.json()["id"] == po["id"]

        flags = {b["id"]: b["has_purchase_order"] for b in client.get("/api/backlog").json()}
        assert flags[backlog_id] is True

    def test_duplicate_purchase_order_rejected(self, client):
        """Test that a second PO for the same backlog item is rejected."""
        backlog_id = self._free_backlog_id(client)
        assert client.post("/api/purchase-orders", json=_po_payload(backlog_id)).status_code == 201

        response = client.post("/api/purchase-orders", json=_po_payload(backlog_id))
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_create_purchase_order_unknown_backlog_item(self, client):
        """Test creating a PO for a nonexistent backlog item."""
        response = client.post("/api/purchase-orders", json=_po_payload("does-not-exist"))
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_create_purchase_order_invalid_quantity(self, client):
        """Test that a non-positive quantity is rejected."""
        backlog_id = self._free_backlog_id(client)
        response = client.post("/api/purchase-orders", json=_po_payload(backlog_id, quantity=0))
        assert response.status_code == 400

    def test_get_nonexistent_purchase_order(self, client):
        """Test fetching a PO for a backlog item without one."""
        response = client.get("/api/purchase-orders/does-not-exist")
        assert response.status_code == 404
