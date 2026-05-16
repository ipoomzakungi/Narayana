from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.call_lifecycle_service import CallLifecycleService, CallLifecycleState
from app.models.realtime import RealtimeAudioEvent, RealtimeAudioEventType, RealtimeAudioFormat, RealtimeProviderMode
from app.models.tts import TTSProfile, TTSResult
from app.services.intake_session_store import get_intake_session_store


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
async def test_send_tts_media_sends_media_and_mark(monkeypatch) -> None:
    import app.api.routes_twilio as routes_twilio

    class MockTTSService:
        configured = True

        def __init__(self, settings):
            self.settings = settings

        def missing_variables(self):
            return []

        async def synthesize_twilio_mulaw(self, text: str, *, session_id=None, call_id=None, voice=None, profile="normal"):
            assert text == "สวัสดีค่ะ"
            assert profile == TTSProfile.GREETING
            return TTSResult(
                configured=True,
                voice="th-TH-PremwadeeNeural",
                profile=profile,
                total_bytes=320,
                estimated_duration_ms=40,
            ).with_payloads(["abcd", "efgh"])

    monkeypatch.setattr(routes_twilio, "AzureSpeechTTSService", MockTTSService)
    websocket = FakeWebSocket()

    await routes_twilio._send_tts_media(
        websocket,
        settings=Settings(azure_speech_key="key", azure_speech_region="eastus"),
        stream_sid="MZ123",
        text="สวัสดีค่ะ",
        profile=TTSProfile.GREETING,
        call_id="CA123",
        session_id="twilio_CA123",
        purpose="greeting",
        mark_name="narayana_initial_greeting",
    )

    assert websocket.sent == [
        {"event": "media", "streamSid": "MZ123", "media": {"payload": "abcd"}},
        {"event": "media", "streamSid": "MZ123", "media": {"payload": "efgh"}},
        {"event": "mark", "streamSid": "MZ123", "mark": {"name": "narayana_initial_greeting"}},
    ]


@pytest.mark.asyncio
async def test_send_tts_media_skips_when_unconfigured() -> None:
    import app.api.routes_twilio as routes_twilio

    websocket = FakeWebSocket()

    await routes_twilio._send_tts_media(
        websocket,
        settings=Settings(),
        stream_sid="MZ123",
        text="สวัสดีค่ะ",
        profile=TTSProfile.GREETING,
        call_id="CA123",
        session_id="twilio_CA123",
        purpose="greeting",
        mark_name="narayana_initial_greeting",
    )

    assert websocket.sent == []


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
async def test_initial_greeting_failure_does_not_raise_or_send_audio(monkeypatch) -> None:
    import app.api.routes_twilio as routes_twilio

    class FailingTTSService:
        configured = True

        def __init__(self, settings):
            self.settings = settings

        def missing_variables(self):
            return []

        async def synthesize_twilio_mulaw(self, text: str, *, session_id=None, call_id=None, voice=None, profile="normal"):
            raise RuntimeError("tts unavailable")

    monkeypatch.setattr(routes_twilio, "AzureSpeechTTSService", FailingTTSService)
    websocket = FakeWebSocket()

    await routes_twilio._send_initial_greeting(
        websocket,
        settings=Settings(
            enable_twilio_initial_greeting=True,
            azure_speech_key="key",
            azure_speech_region="eastus",
        ),
        stream_sid="MZ123",
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

        async def synthesize_twilio_mulaw(self, text: str, *, session_id=None, call_id=None, voice=None, profile="normal"):
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
        "profile": "followup",
        "ssml_enabled": True,
        "stream_sid_present": True,
    }


def test_twilio_tts_profile_detects_red_and_unclear_payloads() -> None:
    import app.api.routes_twilio as routes_twilio

    red_payload = {
        "type": "triage.case.created",
        "record": {"case": {"triage_level": "RED"}},
        "response_text": "รับทราบค่ะ",
    }
    unclear_payload = {
        "type": "triage.case.created",
        "transcript_source": "fallback",
        "response_text": "เสียงไม่ชัด",
    }

    assert routes_twilio._tts_profile_for_payload(red_payload) == "red"
    assert routes_twilio._tts_profile_for_payload(unclear_payload) == "unclear"


@pytest.mark.asyncio
async def test_handle_barge_in_sends_twilio_clear(monkeypatch, caplog) -> None:
    import app.api.routes_twilio as routes_twilio

    settings = Settings(call_audit_enabled=True)
    lifecycle_service = CallLifecycleService(settings)
    lifecycle_state = CallLifecycleState(session_id="twilio_CA123", call_id="CA123")
    lifecycle_service.track_assistant_playback_started(
        lifecycle_state,
        mark_name="narayana_tts_test",
        purpose="tts",
        estimated_duration_ms=1000,
    )
    websocket = FakeWebSocket()

    with caplog.at_level("INFO", logger="app.api.routes_twilio"):
        await routes_twilio._handle_barge_in(
            websocket,
            settings=settings,
            lifecycle_service=lifecycle_service,
            lifecycle_state=lifecycle_state,
            stream_sid="MZ123",
            call_id="CA123",
            session_id="twilio_CA123",
            metadata={"sequence": 7},
        )

    assert websocket.sent == [{"event": "clear", "streamSid": "MZ123"}]
    assert lifecycle_state.assistant_speaking is False
    assert "barge_in.detected" in caplog.text
    assert "barge_in.clear_sent" in caplog.text


def test_twilio_mark_event_reports_playback_completed(monkeypatch) -> None:
    import app.api.routes_twilio as routes_twilio

    class MockTTSService:
        configured = True

        def __init__(self, settings):
            self.settings = settings

        def missing_variables(self):
            return []

        async def synthesize_twilio_mulaw(self, text: str, *, session_id=None, call_id=None, voice=None, profile="normal"):
            return TTSResult(
                configured=True,
                voice="th-TH-PremwadeeNeural",
                profile=profile,
                total_bytes=160,
                estimated_duration_ms=20,
                sanitized_text=text,
            ).with_payloads(["abcd"])

    monkeypatch.setattr(
        routes_twilio,
        "get_settings",
        lambda: Settings(
            use_mock_services=True,
            enable_twilio_initial_greeting=True,
            azure_speech_key="key",
            azure_speech_region="eastus",
        ),
    )
    monkeypatch.setattr(routes_twilio, "AzureSpeechTTSService", MockTTSService)
    client = TestClient(create_app())

    with client.websocket_connect("/ws/telephony/twilio/CA123") as websocket:
        websocket.send_json(
            {
                "event": "start",
                "sequenceNumber": "1",
                "start": {
                    "callSid": "CA123",
                    "streamSid": "MZ123",
                    "mediaFormat": {"encoding": "audio/x-mulaw", "sampleRate": 8000, "channels": 1},
                },
            }
        )
        assert websocket.receive_json()["type"] == "session.started"
        assert websocket.receive_json()["event"] == "media"
        mark = websocket.receive_json()
        assert mark["event"] == "mark"
        websocket.send_json({"event": "mark", "streamSid": "MZ123", "mark": {"name": "narayana_initial_greeting"}})
        completed = websocket.receive_json()
        close_twilio = {"event": "stop"}
        websocket.send_json(close_twilio)
        assert websocket.receive_json()["type"] == "session.closed"

    assert completed["type"] == "assistant.playback.completed"
    assert completed["mark_name"] == "narayana_initial_greeting"


@pytest.mark.asyncio
async def test_handle_realtime_event_sends_debug_payload_and_twilio_media(caplog) -> None:
    import app.api.routes_twilio as routes_twilio

    websocket = FakeWebSocket()
    event = RealtimeAudioEvent(
        event_type=RealtimeAudioEventType.OUTPUT_AUDIO_RECEIVED,
        provider=RealtimeProviderMode.AZURE_OPENAI_REALTIME,
        audio_base64="abcd",
        audio_format=RealtimeAudioFormat.MULAW_8KHZ,
        latency_ms=42,
    )

    with caplog.at_level("INFO", logger="app.api.routes_twilio"):
        fallback = await routes_twilio._handle_realtime_event(
            websocket,
            settings=Settings(call_audit_enabled=True),
            event=event,
            stream_sid="MZ123",
            session_id="twilio_CA123",
            call_id="CA123",
        )

    assert fallback is False
    assert websocket.sent[0]["type"] == "realtime.audio.output.received"
    assert websocket.sent[0]["latency_ms"] == 42
    assert websocket.sent[1] == {"event": "media", "streamSid": "MZ123", "media": {"payload": "abcd"}}
    assert "realtime.audio.output.received" in caplog.text


@pytest.mark.asyncio
async def test_handle_realtime_error_sends_fallback_and_logs(caplog) -> None:
    import app.api.routes_twilio as routes_twilio

    websocket = FakeWebSocket()
    event = RealtimeAudioEvent(
        event_type=RealtimeAudioEventType.ERROR,
        provider=RealtimeProviderMode.AZURE_VOICE_LIVE,
        fallback_reason="provider_error",
        warnings=["provider failed"],
        latency_ms=9,
    )

    with caplog.at_level("INFO", logger="app.api.routes_twilio"):
        fallback = await routes_twilio._handle_realtime_event(
            websocket,
            settings=Settings(call_audit_enabled=True),
            event=event,
            stream_sid="MZ123",
            session_id="twilio_CA123",
            call_id="CA123",
        )

    assert fallback is True
    assert websocket.sent[0]["type"] == "realtime.fallback"
    assert websocket.sent[0]["fallback_reason"] == "provider_error"
    assert "realtime.error" in caplog.text
    assert "realtime.fallback" in caplog.text


@pytest.mark.asyncio
async def test_handle_realtime_transcript_creates_case(tmp_path) -> None:
    import app.api.routes_twilio as routes_twilio

    get_intake_session_store().clear()
    websocket = FakeWebSocket()
    event = RealtimeAudioEvent(
        event_type=RealtimeAudioEventType.CALLER_TRANSCRIPT_COMPLETED,
        provider=RealtimeProviderMode.AZURE_OPENAI_REALTIME,
        text="ไฟไหม้ที่หาดใหญ่ มีควันไฟ มีคนบาดเจ็บ 2 คน",
    )

    fallback = await routes_twilio._handle_realtime_event(
        websocket,
        settings=Settings(
            use_mock_services=True,
            enable_realtime_voice=True,
            realtime_provider="azure_openai_realtime",
            azure_realtime_deployment="gpt-realtime",
            case_store_path=str(tmp_path / "cases.json"),
        ),
        event=event,
        stream_sid="MZ123",
        session_id="twilio_CA_REALTIME_CASE",
        call_id="CA_REALTIME_CASE",
    )

    assert fallback is False
    assert websocket.sent[0]["type"] == "realtime.transcript.caller.completed"
    case_payload = next(message for message in websocket.sent if message.get("type") == "triage.case.created")
    assert case_payload["record"]["source_provider"] == "azure_openai_realtime"
    assert case_payload["record"]["case"]["realtime_provider"] == "azure_openai_realtime"
    assert case_payload["record"]["case"]["realtime_model_or_deployment"] == "gpt-realtime"
    assert case_payload["record"]["case"]["caller_tone"] in {"unknown", "urgent", "distressed"}
    assert case_payload["record"]["case"]["recommended_operator_action"] == "immediate_human_review"
    assert case_payload["record"]["case"]["realtime_transcript_turns"][0]["text"] == event.text


def test_realtime_logging_redacts_raw_audio_and_secrets(caplog) -> None:
    import app.api.routes_twilio as routes_twilio

    with caplog.at_level("INFO", logger="app.api.routes_twilio"):
        routes_twilio._log_realtime(
            settings=Settings(call_audit_enabled=True),
            event_type="audio.output.received",
            session_id="twilio_CA123",
            call_id="CA123",
            provider="azure_openai_realtime",
            metadata={"audio_base64": "AAAA", "api_key": "secret", "safe": "ok"},
        )

    assert "AAAA" not in caplog.text
    assert "secret" not in caplog.text
    assert "[AUDIO_REDACTED]" in caplog.text
    assert "[REDACTED]" in caplog.text
