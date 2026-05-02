from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_twilio_webhook_returns_config_error_without_public_base_url(monkeypatch) -> None:
    import app.api.routes_twilio as routes_twilio

    monkeypatch.setattr(routes_twilio, "get_settings", lambda: Settings())
    client = TestClient(create_app())

    response = client.post("/api/telephony/twilio/incoming-call", data={"CallSid": "CA123"})

    assert response.status_code == 503
    assert "public base URL" in response.json()["detail"]


def test_twilio_webhook_requires_call_sid(monkeypatch) -> None:
    import app.api.routes_twilio as routes_twilio

    monkeypatch.setattr(
        routes_twilio,
        "get_settings",
        lambda: Settings(twilio_webhook_public_base_url="https://example.ngrok-free.app"),
    )
    client = TestClient(create_app())

    response = client.post("/api/telephony/twilio/incoming-call", data={})

    assert response.status_code == 400
    assert "CallSid" in response.json()["detail"]


def test_twilio_webhook_returns_twiml_when_configured(monkeypatch) -> None:
    import app.api.routes_twilio as routes_twilio

    monkeypatch.setattr(
        routes_twilio,
        "get_settings",
        lambda: Settings(twilio_webhook_public_base_url="https://example.ngrok-free.app"),
    )
    client = TestClient(create_app())

    response = client.post(
        "/api/telephony/twilio/incoming-call",
        data={"CallSid": "CA123", "From": "+15550001111", "To": "+15552223333", "FromCountry": "US"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    assert "<Connect>" in response.text
    assert '<Stream url="wss://example.ngrok-free.app/ws/telephony/twilio/CA123">' in response.text
    assert 'name="source_input_mode" value="twilio_call"' in response.text
    assert 'name="From" value="+15550001111"' in response.text
    assert 'name="To" value="+15552223333"' in response.text
    assert 'name="FromCountry" value="US"' in response.text
