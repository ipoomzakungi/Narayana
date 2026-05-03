from __future__ import annotations

import pytest
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


class FakeWebSocket:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_json(self, payload: dict) -> None:
        self.sent.append(payload)


@pytest.mark.asyncio
async def test_twilio_tts_skips_when_stream_sid_missing() -> None:
    import app.api.routes_twilio as routes_twilio

    websocket = FakeWebSocket()

    await routes_twilio._maybe_send_tts_response(
        websocket,
        payload={"type": "intake.followup", "response_text": "มีใครบาดเจ็บไหมคะ?"},
        settings=Settings(
            enable_twilio_tts_response=True,
            azure_speech_key="key",
            azure_speech_region="eastus",
        ),
        stream_sid=None,
        call_id="CA123",
        session_id="twilio_CA123",
    )

    assert websocket.sent == []


@pytest.mark.asyncio
async def test_twilio_tts_failure_does_not_raise_or_send_audio(monkeypatch) -> None:
    import app.api.routes_twilio as routes_twilio

    class FailingTTSService:
        configured = True

        def __init__(self, settings):
            self.settings = settings

        def missing_variables(self):
            return []

        async def synthesize_twilio_mulaw(self, text: str, *, session_id=None, call_id=None, voice=None):
            raise RuntimeError("tts unavailable")

    monkeypatch.setattr(routes_twilio, "AzureSpeechTTSService", FailingTTSService)
    websocket = FakeWebSocket()

    await routes_twilio._maybe_send_tts_response(
        websocket,
        payload={"type": "intake.followup", "response_text": "มีใครบาดเจ็บไหมคะ?"},
        settings=Settings(
            enable_twilio_tts_response=True,
            azure_speech_key="key",
            azure_speech_region="eastus",
        ),
        stream_sid="MZ123",
        call_id="CA123",
        session_id="twilio_CA123",
    )

    assert websocket.sent == []


def test_twilio_tts_debug_metadata_is_additive() -> None:
    import app.api.routes_twilio as routes_twilio

    payload = routes_twilio._with_tts_debug_metadata(
        {"type": "intake.followup", "response_text": "มีใครบาดเจ็บไหมคะ?"},
        Settings(enable_twilio_tts_response=True, azure_speech_key="key", azure_speech_region="eastus"),
        "MZ123",
    )

    assert payload["tts"] == {
        "enabled": True,
        "configured": True,
        "voice": "th-TH-PremwadeeNeural",
        "audio_format": "mulaw_8khz",
        "stream_sid_present": True,
    }
