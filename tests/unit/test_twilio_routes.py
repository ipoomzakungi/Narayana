from __future__ import annotations

import asyncio

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


class FakeRealtimeToolProvider:
    mode = RealtimeProviderMode.AZURE_OPENAI_REALTIME

    def __init__(self) -> None:
        self.tool_results: list[dict] = []
        self.created_responses: list[str | None] = []

    async def send_tool_result(self, *, tool_call_id: str | None, result: dict):
        from app.models.realtime import RealtimeSendResult

        self.tool_results.append({"tool_call_id": tool_call_id, "result": result})
        return RealtimeSendResult(sent=True, provider=self.mode, latency_ms=2)

    async def create_response(self, *, instructions: str | None = None):
        from app.models.realtime import RealtimeSendResult

        self.created_responses.append(instructions)
        return RealtimeSendResult(sent=True, provider=self.mode, latency_ms=2)


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
async def test_handle_realtime_error_can_speak_tts_fallback(monkeypatch) -> None:
    import app.api.routes_twilio as routes_twilio

    class MockTTSService:
        configured = True

        def __init__(self, settings):
            self.settings = settings

        def missing_variables(self):
            return []

        async def synthesize_twilio_mulaw(self, text: str, *, session_id=None, call_id=None, voice=None, profile="normal"):
            assert text == routes_twilio.REALTIME_FAILURE_TTS_TEXT
            assert profile == TTSProfile.UNCLEAR
            return TTSResult(
                configured=True,
                voice="th-TH-PremwadeeNeural",
                profile=profile,
                total_bytes=160,
                estimated_duration_ms=20,
            ).with_payloads(["fallback-audio"])

    monkeypatch.setattr(routes_twilio, "AzureSpeechTTSService", MockTTSService)
    websocket = FakeWebSocket()
    event = RealtimeAudioEvent(
        event_type=RealtimeAudioEventType.ERROR,
        provider=RealtimeProviderMode.AZURE_OPENAI_REALTIME,
        fallback_reason="provider_error",
        warnings=["active response in progress"],
    )

    fallback = await routes_twilio._handle_realtime_event(
        websocket,
        settings=Settings(azure_speech_key="key", azure_speech_region="eastus"),
        event=event,
        stream_sid="MZ123",
        session_id="twilio_CA123",
        call_id="CA123",
    )

    assert fallback is True
    assert websocket.sent[0] == {"event": "media", "streamSid": "MZ123", "media": {"payload": "fallback-audio"}}
    assert websocket.sent[1]["event"] == "mark"
    assert websocket.sent[1]["streamSid"] == "MZ123"
    assert websocket.sent[2]["type"] == "realtime.fallback"


@pytest.mark.asyncio
async def test_handle_realtime_transcript_creates_case(tmp_path) -> None:
    import app.api.routes_twilio as routes_twilio

    get_intake_session_store().clear()
    websocket = FakeWebSocket()
    event = RealtimeAudioEvent(
        event_type=RealtimeAudioEventType.CALLER_TRANSCRIPT_COMPLETED,
        provider=RealtimeProviderMode.AZURE_OPENAI_REALTIME,
        text="ไฟไหม้ที่หาดใหญ่ มีควันไฟ มีคนบาดเจ็บ 2 คน",
        metadata={"item_id": "item_fire"},
    )
    debug_state = {}

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
        debug_state=debug_state,
    )
    await asyncio.gather(*debug_state["background_intake_tasks"])

    assert fallback is False
    assert websocket.sent[0]["type"] == "realtime.transcript.caller.completed"
    assert not any(message.get("type") == "triage.case.created" for message in websocket.sent)
    state = get_intake_session_store().snapshot("twilio_CA_REALTIME_CASE")
    assert state is not None
    assert state.final_case_id
    assert state.realtime_provider == "azure_openai_realtime"
    assert state.realtime_model_or_deployment == "gpt-realtime"
    assert state.caller_tone in {"unknown", "urgent", "distressed"}
    assert state.human_review_required is True
    assert state.realtime_transcript_turns[0]["text"] == event.text
    assert state.realtime_transcript_turns[0]["metadata"]["item_id"] == "item_fire"


@pytest.mark.asyncio
async def test_realtime_transcript_completed_duplicate_item_does_not_duplicate_intake(tmp_path) -> None:
    import app.api.routes_twilio as routes_twilio

    get_intake_session_store().clear()
    websocket = FakeWebSocket()
    settings = Settings(
        use_mock_services=True,
        enable_realtime_voice=True,
        realtime_provider="azure_openai_realtime",
        azure_realtime_deployment="gpt-realtime",
        case_store_path=str(tmp_path / "cases.json"),
    )
    event = RealtimeAudioEvent(
        event_type=RealtimeAudioEventType.CALLER_TRANSCRIPT_COMPLETED,
        provider=RealtimeProviderMode.AZURE_OPENAI_REALTIME,
        text="ไฟไหม้ที่หาดใหญ่ มีควันไฟ มีคนบาดเจ็บ 2 คน",
        metadata={"item_id": "item_same"},
    )
    debug_state = {}

    for _ in range(2):
        await routes_twilio._handle_realtime_event(
            websocket,
            settings=settings,
            event=event,
            stream_sid="MZ123",
            session_id="twilio_CA_REALTIME_DUP_ITEM",
            call_id="CA_REALTIME_DUP_ITEM",
            debug_state=debug_state,
        )
    await asyncio.gather(*debug_state["background_intake_tasks"])

    state = get_intake_session_store().snapshot("twilio_CA_REALTIME_DUP_ITEM")
    assert state is not None
    assert len(state.realtime_transcript_turns) == 1
    assert len(state.conversation_turns) == 2
    assert debug_state["background_intake_item_ids"] == ["CA_REALTIME_DUP_ITEM:item_same"]


@pytest.mark.asyncio
async def test_realtime_transcription_failed_marks_operator_review() -> None:
    import app.api.routes_twilio as routes_twilio

    get_intake_session_store().clear()
    websocket = FakeWebSocket()
    event = RealtimeAudioEvent(
        event_type=RealtimeAudioEventType.CALLER_TRANSCRIPTION_FAILED,
        provider=RealtimeProviderMode.AZURE_OPENAI_REALTIME,
        warnings=["transcription unavailable"],
        metadata={
            "provider_event_type": "conversation.item.input_audio_transcription.failed",
            "item_id": "item_failed",
            "error": {"message": "transcription unavailable"},
        },
    )

    fallback = await routes_twilio._handle_realtime_event(
        websocket,
        settings=Settings(call_audit_enabled=True),
        event=event,
        stream_sid="MZ123",
        session_id="twilio_CA_REALTIME_TX_FAIL",
        call_id="CA_REALTIME_TX_FAIL",
    )

    assert fallback is False
    assert websocket.sent[0]["type"] == "realtime.transcript.caller.failed"
    state = get_intake_session_store().snapshot("twilio_CA_REALTIME_TX_FAIL")
    assert state is not None
    assert state.human_review_required is True
    assert state.recommended_operator_action == "operator_review_transcription_failed"
    assert state.decision_audit[-1]["caller_audio_received"] is True
    assert state.decision_audit[-1]["transcription_failed"] is True


@pytest.mark.asyncio
async def test_realtime_transcript_completed_can_emit_intake_followup(tmp_path) -> None:
    import app.api.routes_twilio as routes_twilio

    get_intake_session_store().clear()
    websocket = FakeWebSocket()
    event = RealtimeAudioEvent(
        event_type=RealtimeAudioEventType.CALLER_TRANSCRIPT_COMPLETED,
        provider=RealtimeProviderMode.AZURE_OPENAI_REALTIME,
        text="น้ำท่วมอยู่ที่หาดใหญ่",
    )
    debug_state = {}

    fallback = await routes_twilio._handle_realtime_event(
        websocket,
        settings=Settings(
            use_mock_services=True,
            enable_multi_turn_intake=True,
            enable_realtime_voice=True,
            realtime_provider="azure_openai_realtime",
            case_store_path=str(tmp_path / "cases.json"),
        ),
        event=event,
        stream_sid="MZ123",
        session_id="twilio_CA_REALTIME_FOLLOWUP",
        call_id="CA_REALTIME_FOLLOWUP",
        debug_state=debug_state,
    )
    await asyncio.gather(*debug_state["background_intake_tasks"])

    assert fallback is False
    assert not any(message.get("type") == "intake.followup" for message in websocket.sent)
    state = get_intake_session_store().snapshot("twilio_CA_REALTIME_FOLLOWUP")
    assert state is not None
    assert state.conversation_turns[0].text == event.text
    assert state.collected_fields.missing_fields


@pytest.mark.asyncio
async def test_realtime_transcript_delta_is_not_persisted_without_debug() -> None:
    import app.api.routes_twilio as routes_twilio

    get_intake_session_store().clear()
    websocket = FakeWebSocket()
    event = RealtimeAudioEvent(
        event_type=RealtimeAudioEventType.ASSISTANT_TRANSCRIPT_DELTA,
        provider=RealtimeProviderMode.AZURE_OPENAI_REALTIME,
        text="สวัสดี",
        metadata={"provider_event_type": "response.output_audio_transcript.delta"},
    )
    settings = Settings(
        enable_realtime_voice=True,
        realtime_provider="azure_openai_realtime",
        twilio_debug_payloads_enabled=False,
        debug_realtime_deltas=False,
    )

    fallback = await routes_twilio._handle_realtime_event(
        websocket,
        settings=settings,
        event=event,
        stream_sid="MZ123",
        session_id="twilio_CA_REALTIME_DELTA",
        call_id="CA_REALTIME_DELTA",
    )

    assert fallback is False
    state = get_intake_session_store().snapshot("twilio_CA_REALTIME_DELTA")
    assert state is not None
    assert state.realtime_transcript_turns == []
    assert [item.type for item in state.timeline_events] == []


@pytest.mark.asyncio
async def test_realtime_transcript_delta_can_be_persisted_in_debug() -> None:
    import app.api.routes_twilio as routes_twilio

    get_intake_session_store().clear()
    websocket = FakeWebSocket()
    event = RealtimeAudioEvent(
        event_type=RealtimeAudioEventType.ASSISTANT_TRANSCRIPT_DELTA,
        provider=RealtimeProviderMode.AZURE_OPENAI_REALTIME,
        text="สวัสดี",
        metadata={"provider_event_type": "response.output_audio_transcript.delta"},
    )
    settings = Settings(
        enable_realtime_voice=True,
        realtime_provider="azure_openai_realtime",
        twilio_debug_payloads_enabled=False,
        debug_realtime_deltas=True,
    )

    fallback = await routes_twilio._handle_realtime_event(
        websocket,
        settings=settings,
        event=event,
        stream_sid="MZ123",
        session_id="twilio_CA_REALTIME_DELTA_DEBUG",
        call_id="CA_REALTIME_DELTA_DEBUG",
    )

    assert fallback is False
    state = get_intake_session_store().snapshot("twilio_CA_REALTIME_DELTA_DEBUG")
    assert state is not None
    assert state.realtime_transcript_turns[0]["text"] == "สวัสดี"
    assert state.realtime_transcript_turns[0]["is_delta"] is True
    assert state.timeline_events[0].type == "realtime.transcript.assistant.delta"


@pytest.mark.asyncio
async def test_realtime_dispatch_loop_forwards_audio_without_twilio_media() -> None:
    import asyncio
    import app.api.routes_twilio as routes_twilio

    get_intake_session_store().clear()
    websocket = FakeWebSocket()
    provider = FakeRealtimeToolProvider()
    queue: asyncio.Queue[RealtimeAudioEvent] = asyncio.Queue()
    fallback_event = asyncio.Event()
    task = asyncio.create_task(
        routes_twilio._realtime_event_dispatch_loop(
            websocket,
            settings=Settings(
                enable_realtime_voice=True,
                realtime_provider="azure_openai_realtime",
                twilio_debug_payloads_enabled=False,
            ),
            provider=provider,
            queue=queue,
            stream_sid_ref=lambda: "MZ123",
            session_id="twilio_CA_DISPATCH",
            call_id="CA_DISPATCH",
            debug_state={},
            fallback_event=fallback_event,
        )
    )

    await queue.put(
        RealtimeAudioEvent(
            event_type=RealtimeAudioEventType.OUTPUT_AUDIO_RECEIVED,
            provider=RealtimeProviderMode.AZURE_OPENAI_REALTIME,
            audio_base64="abcd",
            audio_format=RealtimeAudioFormat.MULAW_8KHZ,
            metadata={"provider_event_type": "response.output_audio.delta"},
        )
    )
    for _ in range(20):
        if websocket.sent:
            break
        await asyncio.sleep(0.01)
    await routes_twilio._cancel_realtime_receive_task(task)

    assert fallback_event.is_set() is False
    assert websocket.sent == [
        {
            "event": "media",
            "streamSid": "MZ123",
            "media": {"payload": "abcd"},
        }
    ]


@pytest.mark.asyncio
async def test_realtime_structured_extraction_creates_case_and_sends_tool_result(tmp_path) -> None:
    import app.api.routes_twilio as routes_twilio

    get_intake_session_store().clear()
    websocket = FakeWebSocket()
    provider = FakeRealtimeToolProvider()
    event = RealtimeAudioEvent(
        event_type=RealtimeAudioEventType.STRUCTURED_EXTRACTION,
        provider=RealtimeProviderMode.AZURE_OPENAI_REALTIME,
        metadata={
            "tool_call_id": "call_structured",
            "tool_arguments": {
                "situation": "ไฟไหม้บ้าน",
                "incident_type": "fire",
                "location": "หาดใหญ่",
                "people_affected": 2,
                "injuries": "smoke inhalation",
                "immediate_needs": ["fire", "medical"],
                "caller_phone": "+15550001111",
                "language": "th",
                "missing_fields": [],
                "caller_tone": "urgent",
                "recommended_operator_action": "immediate_human_review",
            },
        },
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
        provider_client=provider,
        event=event,
        stream_sid="MZ123",
        session_id="twilio_CA_REALTIME_STRUCTURED",
        call_id="CA_REALTIME_STRUCTURED",
    )

    assert fallback is False
    case_payload = next(message for message in websocket.sent if message.get("type") == "triage.case.created")
    assert case_payload["record"]["case"]["incident_type"] == "fire"
    assert case_payload["record"]["case"]["realtime_provider"] == "azure_openai_realtime"
    assert provider.tool_results == [
        {
            "tool_call_id": "call_structured",
            "result": {
                "status": "escalated",
                "missing_fields": [],
                "human_review_required": True,
                "case_id": case_payload["record"]["case"]["case_id"],
            },
        }
    ]


@pytest.mark.asyncio
async def test_realtime_tool_result_is_deduped_and_response_create_is_deferred(tmp_path) -> None:
    import app.api.routes_twilio as routes_twilio

    get_intake_session_store().clear()
    websocket = FakeWebSocket()
    provider = FakeRealtimeToolProvider()
    settings = Settings(
        use_mock_services=True,
        enable_realtime_voice=True,
        realtime_provider="azure_openai_realtime",
        azure_realtime_deployment="gpt-realtime",
        case_store_path=str(tmp_path / "cases.json"),
    )
    debug_state = {}
    event = RealtimeAudioEvent(
        event_type=RealtimeAudioEventType.STRUCTURED_EXTRACTION,
        provider=RealtimeProviderMode.AZURE_OPENAI_REALTIME,
        metadata={
            "provider_event_type": "response.function_call_arguments.done",
            "tool_call_id": "call_structured",
            "tool_arguments": {
                "situation": "น้ำท่วม",
                "incident_type": "flood",
                "location": "หาดใหญ่",
                "people_affected": 1,
                "injuries": "หายใจลำบาก",
                "immediate_needs": ["medical"],
                "missing_fields": [],
            },
        },
    )

    await routes_twilio._handle_realtime_event(
        websocket,
        settings=settings,
        provider_client=provider,
        event=event,
        stream_sid="MZ123",
        session_id="twilio_CA_REALTIME_DEDUPE",
        call_id="CA_REALTIME_DEDUPE",
        debug_state=debug_state,
    )
    duplicate = event.model_copy(
        update={"metadata": {**event.metadata, "provider_event_type": "response.output_item.done"}}
    )
    await routes_twilio._handle_realtime_event(
        websocket,
        settings=settings,
        provider_client=provider,
        event=duplicate,
        stream_sid="MZ123",
        session_id="twilio_CA_REALTIME_DEDUPE",
        call_id="CA_REALTIME_DEDUPE",
        debug_state=debug_state,
    )

    assert len(provider.tool_results) == 1
    assert provider.created_responses == []
    assert debug_state["pending_tool_response_create"] is True

    await routes_twilio._handle_realtime_event(
        websocket,
        settings=settings,
        provider_client=provider,
        event=RealtimeAudioEvent(
            event_type=RealtimeAudioEventType.RESPONSE_COMPLETED,
            provider=RealtimeProviderMode.AZURE_OPENAI_REALTIME,
            metadata={"provider_event_type": "response.done", "response_status": "completed"},
        ),
        stream_sid="MZ123",
        session_id="twilio_CA_REALTIME_DEDUPE",
        call_id="CA_REALTIME_DEDUPE",
        debug_state=debug_state,
    )

    assert provider.created_responses == [None]
    assert "pending_tool_response_create" not in debug_state


@pytest.mark.asyncio
async def test_realtime_transcript_plus_structured_extraction_updates_existing_case(tmp_path) -> None:
    import json
    import app.api.routes_twilio as routes_twilio

    get_intake_session_store().clear()
    websocket = FakeWebSocket()
    settings = Settings(
        use_mock_services=True,
        enable_realtime_voice=True,
        realtime_provider="azure_openai_realtime",
        azure_realtime_deployment="gpt-realtime",
        case_store_path=str(tmp_path / "cases.json"),
    )
    session_id = "twilio_CA_REALTIME_IDEMPOTENT"
    debug_state = {}

    await routes_twilio._handle_realtime_event(
        websocket,
        settings=settings,
        event=RealtimeAudioEvent(
            event_type=RealtimeAudioEventType.CALLER_TRANSCRIPT_COMPLETED,
            provider=RealtimeProviderMode.AZURE_OPENAI_REALTIME,
            text="ไฟไหม้ที่หาดใหญ่ มีควันไฟ มีคนบาดเจ็บ 2 คน",
        ),
        stream_sid="MZ123",
        session_id=session_id,
        call_id="CA_REALTIME_IDEMPOTENT",
        debug_state=debug_state,
    )
    await asyncio.gather(*debug_state["background_intake_tasks"])
    await routes_twilio._handle_realtime_event(
        websocket,
        settings=settings,
        event=RealtimeAudioEvent(
            event_type=RealtimeAudioEventType.STRUCTURED_EXTRACTION,
            provider=RealtimeProviderMode.AZURE_OPENAI_REALTIME,
            metadata={
                "tool_arguments": {
                    "situation": "ไฟไหม้บ้าน",
                    "incident_type": "fire",
                    "location": "หาดใหญ่",
                    "people_affected": 2,
                    "injuries": "smoke inhalation",
                    "immediate_needs": ["fire", "medical"],
                    "caller_phone": "+15550001111",
                    "language": "th",
                    "missing_fields": [],
                    "caller_tone": "urgent",
                    "recommended_operator_action": "immediate_human_review",
                },
            },
        ),
        stream_sid="MZ123",
        session_id=session_id,
        call_id="CA_REALTIME_IDEMPOTENT",
    )

    created = [message for message in websocket.sent if message.get("type") == "triage.case.created"]
    updated = [message for message in websocket.sent if message.get("type") == "case.updated"]
    assert len(created) == 0
    assert len(updated) == 1
    state = get_intake_session_store().snapshot(session_id)
    assert state is not None
    assert state.final_case_id == updated[0]["record"]["case"]["case_id"]
    data = json.loads((tmp_path / "cases.json").read_text(encoding="utf-8"))
    assert list(data) == [state.final_case_id]


@pytest.mark.asyncio
async def test_finalize_realtime_call_summary_updates_existing_case_after_call_end(tmp_path) -> None:
    import json
    import app.api.routes_twilio as routes_twilio

    get_intake_session_store().clear()
    settings = Settings(
        use_mock_services=True,
        enable_realtime_voice=True,
        realtime_provider="azure_openai_realtime",
        azure_realtime_deployment="gpt-realtime-1.5",
        case_store_path=str(tmp_path / "cases.json"),
    )
    websocket = FakeWebSocket()
    session_id = "twilio_CA_REALTIME_FINAL"
    call_id = "CA_REALTIME_FINAL"
    structured = RealtimeAudioEvent(
        event_type=RealtimeAudioEventType.STRUCTURED_EXTRACTION,
        provider=RealtimeProviderMode.AZURE_OPENAI_REALTIME,
        metadata={
            "tool_arguments": {
                "situation": "ไฟไหม้บ้าน",
                "incident_type": "fire",
                "location": "หาดใหญ่",
                "people_affected": 2,
                "injuries": "สำลักควัน",
                "immediate_needs": ["fire", "medical"],
                "caller_phone": "+15550001111",
                "language": "th",
                "missing_fields": ["landmark"],
                "caller_tone": "urgent",
                "recommended_operator_action": "immediate_human_review",
            },
        },
    )

    await routes_twilio._handle_realtime_event(
        websocket,
        settings=settings,
        event=structured,
        stream_sid="MZ123",
        session_id=session_id,
        call_id=call_id,
    )
    state = get_intake_session_store().snapshot(session_id)
    assert state is not None
    state.realtime_transcript_turns.append(
        {
            "speaker": "caller",
            "text": "ไฟไหม้บ้านที่หาดใหญ่ มีคนสำลักควันสองคน",
            "is_delta": False,
            "provider": "azure_openai_realtime",
        }
    )
    get_intake_session_store().save(state)
    original_case_id = state.final_case_id

    result = await routes_twilio.finalize_realtime_call_summary(
        settings=settings,
        session_id=session_id,
        call_id=call_id,
        realtime_transcript_turns=state.realtime_transcript_turns,
        collected_fields=state.collected_fields,
    )

    assert result["case_id"] == original_case_id
    assert result["ai_summary"]
    assert result["caller_tone"] == "urgent"
    data = json.loads((tmp_path / "cases.json").read_text(encoding="utf-8"))
    assert list(data) == [original_case_id]
    stored = data[original_case_id]
    assert stored["case"]["ai_summary"] == result["ai_summary"]
    assert stored["case"]["full_transcript"].startswith("caller:")
    assert stored["case"]["final_structured_fields"]["location_text"] == "หาดใหญ่"
    assert stored["case"]["realtime_provider"] == "azure_openai_realtime"
    assert stored["case"]["realtime_model_or_deployment"] == "gpt-realtime-1.5"


@pytest.mark.asyncio
async def test_finalize_realtime_call_summary_creates_case_when_no_case_but_signal_exists(tmp_path) -> None:
    import json
    import app.api.routes_twilio as routes_twilio

    get_intake_session_store().clear()
    settings = Settings(
        use_mock_services=True,
        enable_realtime_voice=True,
        realtime_provider="azure_openai_realtime",
        azure_realtime_deployment="gpt-realtime-1.5",
        case_store_path=str(tmp_path / "cases.json"),
    )
    fields = routes_twilio.IntakeCollectedFields(
        language="th",
        incident_type=routes_twilio.IncidentType.FIRE,
        location_text="หาดใหญ่",
        injuries="ควันไฟ",
        missing_fields=["people_affected"],
    )
    turns = [
        {
            "speaker": "caller",
            "text": "ไฟไหม้ที่หาดใหญ่ มีควันไฟ",
            "is_delta": False,
            "provider": "azure_openai_realtime",
        }
    ]

    result = await routes_twilio.finalize_realtime_call_summary(
        settings=settings,
        session_id="twilio_CA_FINAL_CREATE",
        call_id="CA_FINAL_CREATE",
        realtime_transcript_turns=turns,
        collected_fields=fields,
    )

    assert result["case_id"]
    data = json.loads((tmp_path / "cases.json").read_text(encoding="utf-8"))
    assert list(data) == [result["case_id"]]
    stored = data[result["case_id"]]
    assert stored["source_provider"] == "azure_openai_realtime"
    assert stored["case"]["status"] == "pending"
    assert stored["case"]["human_review_required"] is True


def test_final_realtime_summary_uses_caller_text_not_assistant_json() -> None:
    import app.api.routes_twilio as routes_twilio

    summary = routes_twilio._final_summary_from_realtime(
        realtime_transcript_turns=[
            {
                "speaker": "caller",
                "text": "เจ็บขาอยู่แถวบางพลี",
                "is_delta": False,
                "provider": "azure_openai_realtime",
            },
            {
                "speaker": "assistant",
                "text": '{"facts_extracted":{"incident_type":"บาดเจ็บขา"}}',
                "is_delta": False,
                "provider": "azure_openai_realtime",
            },
        ],
        collected_fields=routes_twilio.IntakeCollectedFields(),
        caller_tone=None,
        recommended_operator_action=None,
    )

    assert "เจ็บขาอยู่แถวบางพลี" in summary["ai_summary"]
    assert "facts_extracted" not in summary["ai_summary"]


@pytest.mark.asyncio
async def test_unknown_realtime_provider_event_is_logged_safely(caplog) -> None:
    import app.api.routes_twilio as routes_twilio

    websocket = FakeWebSocket()
    event = RealtimeAudioEvent(
        event_type=RealtimeAudioEventType.UNKNOWN_PROVIDER_EVENT,
        provider=RealtimeProviderMode.AZURE_OPENAI_REALTIME,
        metadata={"provider_event_type": "provider.unexpected", "audio_base64": "AAAA", "api_key": "secret"},
    )
    debug_state = {}

    with caplog.at_level("INFO", logger="app.api.routes_twilio"):
        fallback = await routes_twilio._handle_realtime_event(
            websocket,
            settings=Settings(call_audit_enabled=True),
            event=event,
            stream_sid="MZ123",
            session_id="twilio_CA_UNKNOWN",
            call_id="CA_UNKNOWN",
            debug_state=debug_state,
        )

    assert fallback is False
    assert debug_state == {
        "last_event_type": "unknown_provider_event",
        "last_provider_event_type": "provider.unexpected",
    }
    assert websocket.sent[0]["type"] == "realtime.unknown_provider_event"
    assert "provider.unexpected" in caplog.text
    assert "AAAA" not in caplog.text
    assert "secret" not in caplog.text


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


@pytest.mark.asyncio
async def test_realtime_watchdog_commits_and_creates_response(caplog) -> None:
    import app.api.routes_twilio as routes_twilio
    from app.models.realtime import RealtimeSendResult

    class FakeProvider:
        mode = RealtimeProviderMode.AZURE_OPENAI_REALTIME

        def __init__(self) -> None:
            self.committed = False
            self.created = False

        async def commit_audio_buffer(self):
            self.committed = True
            return RealtimeSendResult(sent=True, provider=self.mode, latency_ms=1)

        async def create_response(self, *, instructions=None):
            self.created = True
            return RealtimeSendResult(sent=True, provider=self.mode, latency_ms=1)

    provider = FakeProvider()
    debug_state = {
        "speech_started_at_monotonic": 0,
        "turn_response_started": False,
        "watchdog_forced_commit": False,
    }

    with caplog.at_level("INFO", logger="app.api.routes_twilio"):
        await routes_twilio._maybe_force_realtime_turn_commit(
            settings=Settings(call_audit_enabled=True),
            provider=provider,
            session_id="twilio_CA_WATCHDOG",
            call_id="CA_WATCHDOG",
            debug_state=debug_state,
        )

    assert provider.committed is True
    assert provider.created is True
    assert debug_state["watchdog_forced_commit"] is True
    assert "realtime.watchdog.force_commit" in caplog.text
    assert "realtime.response.create.sent" in caplog.text
