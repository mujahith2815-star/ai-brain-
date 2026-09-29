"""
Unit and Integration Tests for Orvix Sphere Web Dashboard API (FastAPI).
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from web.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_dashboard_home_page(client):
    """Verifies that the dashboard root route serves the full HTML interface."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Orvix Sphere" in response.text
    assert "Zenith Dashboard" in response.text
    assert "Gemini 2.0 Flash" in response.text
    assert "Qwen2.5-7B" in response.text


def test_api_status_endpoint(client):
    """Verifies that /api/status returns comprehensive system telemetry."""
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "models" in data
    assert "mcp" in data
    assert "proactive" in data
    assert "primary" in data["models"]
    assert data["primary_model"] == "Gemini 2.0 Flash (cloud)"
    assert data["fallback_model"] == "Qwen2.5-7B (local, W:)"
    assert "router_mode" in data
    assert "mcp_servers_online" in data
    assert "mcp_servers_total" in data
    assert data["mcp_servers_total"] >= 3
    assert data["mcp_servers_online"] >= 3


def test_api_chat_endpoint_mocked(client):
    """Verifies that /api/chat correctly responds to queries."""
    with patch("nlp.answer_pipeline.process_query", return_value="42 is the answer."):
        payload = {"message": "What is the meaning of life?"}
        response = client.post("/api/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "SUCCESS"
        assert data.get("response") == "42 is the answer."


def test_api_tasks_endpoint(client):
    """Verifies scheduled task inspection endpoint."""
    response = client.get("/api/tasks")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "SUCCESS"
    assert "tasks" in data
    assert isinstance(data["tasks"], list)


def test_api_queue_endpoint(client):
    """Verifies pending approval queue inspection endpoint."""
    response = client.get("/api/queue")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "SUCCESS"
    assert "queue" in data
    assert isinstance(data["queue"], list)


def test_api_approve_and_reject_actions(client):
    """Verifies approval and rejection endpoints execute without crashing."""
    resp_approve = client.post("/api/approve/999999")
    assert resp_approve.status_code == 200

    resp_reject = client.post("/api/reject/999999")
    assert resp_reject.status_code == 200


def test_api_audit_trail_endpoint(client):
    """Verifies the audit trail endpoint."""
    response = client.get("/api/audit")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "SUCCESS"
    assert "logs" in data
    assert isinstance(data["logs"], list)


def test_api_health_endpoint(client):
    """Verifies the health check endpoint utilizing SystemDoctor."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "healthy" in data
    assert "checks" in data
    assert data["healthy"] is True


def test_websocket_ping_pong(client):
    """Verifies the WebSocket chat channel handles ping/pong."""
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_text("__PING__")
        resp = ws.receive_json()
        assert resp == {"type": "PONG"}
