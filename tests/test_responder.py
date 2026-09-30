import importlib.util
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

spec = importlib.util.spec_from_file_location("responder", Path(__file__).parents[1] / "incident-response/responder.py")
responder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(responder)


@pytest.fixture(autouse=True)
def isolate_incident_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(responder, "INCIDENTS", tmp_path)


def test_resolved_alert_does_not_start_agent():
    response = TestClient(responder.app).post("/alerts", json={"alerts": [{"status": "resolved"}]})
    assert response.status_code == 202
    assert "no repair started" in response.json()["status"]


def test_unknown_alert_is_rejected():
    response = TestClient(responder.app).post("/alerts", json={"alerts": [{"status": "firing", "labels": {"alertname": "Unrelated"}}]})
    assert response.status_code == 422


def test_invalid_alert_payload_is_rejected():
    response = TestClient(responder.app).post("/alerts", json={"alerts": "not an array"})
    assert response.status_code == 422
