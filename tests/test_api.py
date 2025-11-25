"""Basic API tests."""
import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_health_endpoint():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "service" in data


def test_root_endpoint():
    """Test root endpoint returns HTML."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_create_task_missing_api_key(monkeypatch):
    """Test task creation fails without API key."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = client.post(
        "/v1/tasks",
        json={"task": "test task", "model": "gpt-4o"},
    )
    # Should return 500 if API key is missing
    assert response.status_code in [500, 422]

