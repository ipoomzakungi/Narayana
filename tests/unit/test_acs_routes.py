from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_acs_events_return_not_implemented_without_credentials() -> None:
    client = TestClient(create_app())

    response = client.post("/api/telephony/acs/events", json={})

    assert response.status_code == 501
    assert "not implemented" in response.json()["detail"]


def test_acs_media_websocket_closes_with_clear_error() -> None:
    client = TestClient(create_app())

    with client.websocket_connect("/ws/telephony/acs/acs_call_1") as websocket:
        message = websocket.receive_json()

    assert message["type"] == "error"
    assert "not implemented" in message["detail"]
    assert message["call_id"] == "acs_call_1"
