from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import create_app
from app.models.tts import TTSResult


def test_tts_test_route_returns_unconfigured_metadata_without_secrets() -> None:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings()
    client = TestClient(app)

    response = client.post("/api/tts/test", json={"text": "ตอนนี้อยู่จุดไหนคะ?"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["configured"] is False
    assert payload["voice"] == "th-TH-PremwadeeNeural"
    assert payload["audio_format"] == "mulaw_8khz"
    assert payload["payload_count"] == 0
    assert "payloads" not in payload
    assert "AZURE_SPEECH_KEY" in payload["missing_variables"]


def test_tts_test_route_rejects_blank_text() -> None:
    client = TestClient(create_app())

    response = client.post("/api/tts/test", json={"text": "   "})

    assert response.status_code == 422


def test_tts_test_route_uses_mocked_configured_service(monkeypatch) -> None:
    import app.api.routes_tts as routes_tts

    class MockService:
        def __init__(self, settings):
            self.settings = settings

        async def synthesize_twilio_mulaw(self, text: str, *, voice=None, session_id=None, call_id=None):
            return TTSResult(
                configured=True,
                voice=voice or "th-TH-PremwadeeNeural",
                total_bytes=160,
                estimated_duration_ms=20,
                sanitized_text=text,
            ).with_payloads(["abcd"])

    monkeypatch.setattr(routes_tts, "AzureSpeechTTSService", MockService)
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(
        azure_speech_key="key",
        azure_speech_region="eastus",
    )
    client = TestClient(app)

    response = client.post("/api/tts/test", json={"text": "ตอนนี้อยู่จุดไหนคะ?", "voice": "th-TH-TestVoice"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["configured"] is True
    assert payload["voice"] == "th-TH-TestVoice"
    assert payload["payload_count"] == 1
    assert payload["total_bytes"] == 160
    assert "payloads" not in payload


def test_tts_test_route_safety_response_does_not_return_unsafe_text() -> None:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings()
    client = TestClient(app)

    response = client.post("/api/tts/test", json={"text": "รถพยาบาลกำลังไปค่ะ"})

    assert response.status_code == 200
    payload = response.json()
    assert "รถพยาบาลกำลังไป" not in " ".join(payload["warnings"])
    assert "payloads" not in payload
