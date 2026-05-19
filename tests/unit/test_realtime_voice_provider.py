from __future__ import annotations

import json

import pytest

from app.core.config import Settings
from app.models.audio import AudioFrame
from app.models.realtime import RealtimeAudioEventType, RealtimeProviderMode
from app.services.azure_openai_realtime_provider import AzureOpenAIRealtimeProvider
from app.services.azure_voice_live_realtime_provider import AzureVoiceLiveRealtimeProvider
from app.services.realtime_latency import RealtimeLatencyTracker
from app.services.realtime_voice_provider import (
    build_openai_realtime_session_update,
    build_openai_realtime_uri,
    build_realtime_instructions,
    build_voice_live_uri,
)


class FakeProviderSocket:
    def __init__(self, receive_messages: list[dict] | None = None) -> None:
        self.sent: list[dict] = []
        self.receive_messages = list(receive_messages or [])
        self.closed = False

    async def send(self, payload: str) -> None:
        self.sent.append(json.loads(payload))

    async def recv(self) -> str:
        if not self.receive_messages:
            raise RuntimeError("no message")
        return json.dumps(self.receive_messages.pop(0))

    async def close(self) -> None:
        self.closed = True


def pcm_frame() -> AudioFrame:
    return AudioFrame(
        session_id="twilio_CA123",
        sequence=1,
        timestamp_ms=20,
        encoding="pcm16",
        sample_rate_hz=8000,
        channels=1,
        duration_ms=20,
        audio_base64="AAAA",
    )


def realtime_settings(provider: str = "azure_openai_realtime") -> Settings:
    return Settings(
        enable_realtime_voice=True,
        realtime_provider=provider,
        azure_realtime_endpoint="https://aoai.example.openai.azure.com",
        azure_realtime_api_key="dummy-key",
        azure_realtime_deployment="gpt-realtime",
        azure_realtime_api_version="2025-04-01-preview",
        azure_voice_live_endpoint="wss://voice.example/voice-live/realtime?api-version=2025-10-01",
        azure_voice_live_model="gpt-realtime",
    )


def test_openai_realtime_uri_uses_preview_deployment_format() -> None:
    uri = build_openai_realtime_uri(realtime_settings())

    assert uri.startswith("wss://aoai.example.openai.azure.com/openai/realtime?")
    assert "deployment=gpt-realtime" in uri
    assert "api-version=2025-04-01-preview" in uri
    assert "dummy-key" not in uri


def test_openai_realtime_uri_uses_ga_model_format_when_requested() -> None:
    uri = build_openai_realtime_uri(
        Settings(
            enable_realtime_voice=True,
            realtime_provider="azure_openai_realtime",
            azure_realtime_endpoint="https://aoai.example.openai.azure.com",
            azure_realtime_api_key="dummy-key",
            azure_realtime_deployment="gpt-realtime-1.5-prod",
            azure_realtime_api_version="v1",
        )
    )

    assert uri == "wss://aoai.example.openai.azure.com/openai/v1/realtime?model=gpt-realtime-1.5-prod"


def realtime_g711_settings(provider: str = "azure_openai_realtime") -> Settings:
    return Settings(
        enable_realtime_voice=True,
        realtime_provider=provider,
        azure_realtime_endpoint="https://aoai.example.openai.azure.com",
        azure_realtime_api_key="dummy-key",
        azure_realtime_deployment="gpt-realtime",
        azure_realtime_api_version="2025-04-01-preview",
        azure_voice_live_endpoint="wss://voice.example/voice-live/realtime?api-version=2025-10-01",
        azure_voice_live_model="gpt-realtime",
        realtime_input_audio_format="g711_ulaw",
        realtime_twilio_audio_passthrough=True,
    )


def test_voice_live_uri_adds_model_when_missing() -> None:
    uri = build_voice_live_uri(realtime_settings("azure_voice_live"))

    assert uri.startswith("wss://voice.example/voice-live/realtime?api-version=2025-10-01")
    assert "model=gpt-realtime" in uri


def test_latency_tracker_redacts_audio_and_secret_metadata() -> None:
    tracker = RealtimeLatencyTracker(
        provider=RealtimeProviderMode.AZURE_OPENAI_REALTIME,
        session_id="twilio_CA123",
        call_id="CA123",
    )
    sample = tracker.instant("input_audio_sent", metadata={"audio_base64": "AAAA", "api_key": "secret"})

    assert sample.metadata["audio_base64"] == "[AUDIO_REDACTED]"
    assert sample.metadata["api_key"] == "[REDACTED]"


def test_realtime_instructions_include_crisis_safety_rules() -> None:
    instructions = build_realtime_instructions(Settings())

    assert "crisis intake" in instructions
    assert "Spoken replies should be under 12 Thai words" in instructions
    assert "ระบบนี้รับแจ้งเหตุฉุกเฉินค่ะ" in instructions
    assert "Never say rescue has been dispatched" in instructions
    assert "Never say an ambulance is on the way" in instructions
    assert "Never reveal RED, YELLOW, or GREEN" in instructions
    assert "Do not diagnose" in instructions
    assert "Do not call tools during the live voice conversation" in instructions


def test_openai_realtime_session_update_uses_twilio_compatible_audio_without_tools() -> None:
    payload = build_openai_realtime_session_update(realtime_settings(), "crisis only")

    session = payload["session"]
    assert payload["type"] == "session.update"
    assert session["type"] == "realtime"
    assert session["instructions"] == "crisis only"
    assert "modalities" not in session
    assert session["input_audio_format"] == "pcm16"
    assert session["output_audio_format"] == "g711_ulaw"
    assert "tools" not in session
    assert "tool_choice" not in session
    assert session["turn_detection"]["threshold"] == 0.55
    assert session["turn_detection"]["prefix_padding_ms"] == 200
    assert session["turn_detection"]["silence_duration_ms"] == 300
    assert session["turn_detection"]["create_response"] is True
    assert session["turn_detection"]["interrupt_response"] is True
    assert "input_audio_transcription" not in session


def test_realtime_session_update_can_select_g711_ulaw_input() -> None:
    payload = build_openai_realtime_session_update(realtime_g711_settings(), "crisis only")

    assert payload["session"]["input_audio_format"] == "g711_ulaw"


def test_realtime_session_update_can_enable_input_transcription() -> None:
    payload = build_openai_realtime_session_update(
        Settings(
            enable_realtime_voice=True,
            realtime_provider="azure_openai_realtime",
            azure_realtime_endpoint="https://aoai.example.openai.azure.com",
            azure_realtime_api_key="dummy-key",
            azure_realtime_deployment="gpt-realtime",
            azure_realtime_api_version="2025-04-01-preview",
            realtime_input_transcription_enabled=True,
        ),
        "crisis only",
    )

    assert payload["session"]["input_audio_transcription"] == {"model": "whisper-1"}


def test_openai_realtime_v1_session_update_uses_nested_audio_schema() -> None:
    payload = build_openai_realtime_session_update(
        Settings(
            enable_realtime_voice=True,
            realtime_provider="azure_openai_realtime",
            azure_realtime_endpoint="https://aoai.example.openai.azure.com",
            azure_realtime_api_key="dummy-key",
            azure_realtime_deployment="gpt-realtime-1.5-prod",
            azure_realtime_api_version="v1",
            realtime_input_audio_format="g711_ulaw",
            realtime_twilio_audio_passthrough=True,
            realtime_input_transcription_enabled=True,
            realtime_output_voice="coral",
        ),
        "crisis only",
    )

    session = payload["session"]
    assert payload["type"] == "session.update"
    assert session["type"] == "realtime"
    assert session["instructions"] == "crisis only"
    assert "modalities" not in session
    assert "input_audio_format" not in session
    assert "output_audio_format" not in session
    assert "input_audio_transcription" not in session
    assert session["output_modalities"] == ["audio"]
    assert session["audio"]["input"]["format"] == {"type": "audio/pcmu"}
    assert session["audio"]["input"]["transcription"] == {"model": "whisper-1"}
    assert session["audio"]["input"]["turn_detection"]["threshold"] == 0.55
    assert session["audio"]["input"]["turn_detection"]["prefix_padding_ms"] == 200
    assert session["audio"]["input"]["turn_detection"]["silence_duration_ms"] == 300
    assert session["audio"]["input"]["turn_detection"]["create_response"] is True
    assert session["audio"]["input"]["turn_detection"]["interrupt_response"] is True
    assert session["audio"]["output"]["format"] == {"type": "audio/pcmu"}
    assert session["audio"]["output"]["voice"] == "coral"
    assert "tools" not in session
    assert "tool_choice" not in session


@pytest.mark.asyncio
async def test_openai_provider_connect_send_and_receive_audio_event() -> None:
    fake_socket = FakeProviderSocket([{"type": "response.audio.delta", "delta": "abcd"}])
    provider = AzureOpenAIRealtimeProvider(realtime_settings(), websocket_factory=lambda *args, **kwargs: fake_socket)

    connection = await provider.connect(session_id="twilio_CA123", call_id="CA123", instructions="crisis only")
    send = await provider.send_audio_frame(pcm_frame())
    event = await provider.receive_audio_event()

    assert connection.connected is True
    assert send.sent is True
    assert fake_socket.sent[0]["type"] == "session.update"
    assert fake_socket.sent[1] == {"type": "input_audio_buffer.append", "audio": "AAAA"}
    assert event is not None
    assert event.event_type == RealtimeAudioEventType.OUTPUT_AUDIO_RECEIVED
    assert event.audio_base64 == "abcd"


@pytest.mark.asyncio
async def test_openai_provider_sends_safe_tool_result_response() -> None:
    fake_socket = FakeProviderSocket()
    provider = AzureOpenAIRealtimeProvider(realtime_settings(), websocket_factory=lambda *args, **kwargs: fake_socket)

    await provider.connect(session_id="twilio_CA123", call_id="CA123", instructions="crisis only")
    result = await provider.send_tool_result(
        tool_call_id="call_123",
        result={
            "status": "case_created",
            "missing_fields": [],
            "human_review_required": True,
            "case_id": "case_123",
        },
    )

    assert result.sent is True
    assert fake_socket.sent[1]["type"] == "conversation.item.create"
    assert fake_socket.sent[1]["item"]["type"] == "function_call_output"
    assert fake_socket.sent[1]["item"]["call_id"] == "call_123"
    assert json.loads(fake_socket.sent[1]["item"]["output"]) == {
        "status": "case_created",
        "missing_fields": [],
        "human_review_required": True,
        "case_id": "case_123",
    }
    assert len(fake_socket.sent) == 2


@pytest.mark.asyncio
async def test_openai_provider_can_commit_audio_and_create_response() -> None:
    fake_socket = FakeProviderSocket()
    provider = AzureOpenAIRealtimeProvider(realtime_settings(), websocket_factory=lambda *args, **kwargs: fake_socket)

    await provider.connect(session_id="twilio_CA123", call_id="CA123", instructions="crisis only")
    commit = await provider.commit_audio_buffer()
    response = await provider.create_response(instructions="ทักทายสั้น ๆ")

    assert commit.sent is True
    assert response.sent is True
    assert fake_socket.sent[1] == {"type": "input_audio_buffer.commit"}
    assert fake_socket.sent[2] == {"type": "response.create", "response": {"instructions": "ทักทายสั้น ๆ"}}


@pytest.mark.asyncio
async def test_openai_provider_normalizes_transcript_and_tool_events() -> None:
    fake_socket = FakeProviderSocket(
        [
            {"type": "conversation.item.input_audio_transcription.completed", "transcript": "ไฟไหม้ที่หาดใหญ่"},
            {"type": "response.audio_transcript.delta", "delta": "อยู่ในที่ปลอดภัย"},
            {
                "type": "conversation.item.input_audio_transcription.failed",
                "item_id": "item_failed",
                "error": {"message": "transcription unavailable"},
            },
            {
                "type": "response.function_call_arguments.done",
                "name": "crisis_intake_update",
                "arguments": json.dumps(
                    {
                        "situation": "fire",
                        "incident_type": "fire",
                        "location": "หาดใหญ่",
                        "people_affected": 2,
                        "injuries": "smoke",
                        "immediate_needs": ["fire"],
                        "caller_phone": "+15550001111",
                        "language": "th",
                        "missing_fields": [],
                        "caller_tone": "urgent",
                        "recommended_operator_action": "immediate_human_review",
                    }
                ),
                "call_id": "call_abc",
            },
        ]
    )
    provider = AzureOpenAIRealtimeProvider(realtime_settings(), websocket_factory=lambda *args, **kwargs: fake_socket)

    await provider.connect(session_id="twilio_CA123", call_id="CA123", instructions="crisis only")
    caller = await provider.receive_audio_event()
    assistant = await provider.receive_audio_event()
    failed = await provider.receive_audio_event()
    tool = await provider.receive_audio_event()

    assert caller is not None
    assert caller.event_type == RealtimeAudioEventType.CALLER_TRANSCRIPT_COMPLETED
    assert caller.text == "ไฟไหม้ที่หาดใหญ่"
    assert assistant is not None
    assert assistant.event_type == RealtimeAudioEventType.ASSISTANT_TRANSCRIPT_DELTA
    assert failed is not None
    assert failed.event_type == RealtimeAudioEventType.CALLER_TRANSCRIPTION_FAILED
    assert failed.metadata["item_id"] == "item_failed"
    assert failed.warnings == ["transcription unavailable"]
    assert tool is not None
    assert tool.event_type == RealtimeAudioEventType.STRUCTURED_EXTRACTION
    assert tool.metadata["tool_call_id"] == "call_abc"
    assert tool.metadata["tool_arguments"]["location"] == "หาดใหญ่"


@pytest.mark.asyncio
async def test_unknown_provider_event_type_is_normalized_without_raw_payload_or_secret() -> None:
    fake_socket = FakeProviderSocket(
        [
            {
                "type": "provider.unexpected",
                "audio": "raw-audio",
                "api_key": "secret-key",
            },
        ]
    )
    provider = AzureOpenAIRealtimeProvider(realtime_settings(), websocket_factory=lambda *args, **kwargs: fake_socket)

    await provider.connect(session_id="twilio_CA123", call_id="CA123", instructions="crisis only")
    event = await provider.receive_audio_event()

    assert event is not None
    assert event.event_type == RealtimeAudioEventType.UNKNOWN_PROVIDER_EVENT
    assert event.metadata == {"provider_event_type": "provider.unexpected"}
    assert "raw-audio" not in str(event.metadata)
    assert "secret-key" not in str(event.metadata)


@pytest.mark.asyncio
async def test_voice_live_provider_connect_and_receive_response_events() -> None:
    fake_socket = FakeProviderSocket(
        [
            {"type": "response.created"},
            {"type": "response.done"},
        ]
    )
    provider = AzureVoiceLiveRealtimeProvider(
        realtime_settings("azure_voice_live"),
        websocket_factory=lambda *args, **kwargs: fake_socket,
    )

    connection = await provider.connect(session_id="twilio_CA123", call_id="CA123", instructions="crisis only")
    started = await provider.receive_audio_event()
    completed = await provider.receive_audio_event()

    assert connection.connected is True
    assert fake_socket.sent[0]["type"] == "session.update"
    assert started is not None
    assert started.event_type == RealtimeAudioEventType.RESPONSE_STARTED
    assert completed is not None
    assert completed.event_type == RealtimeAudioEventType.RESPONSE_COMPLETED


@pytest.mark.asyncio
async def test_provider_receive_error_returns_fallback_event() -> None:
    fake_socket = FakeProviderSocket([{"type": "error", "error": {"message": "bad realtime"}}])
    provider = AzureOpenAIRealtimeProvider(realtime_settings(), websocket_factory=lambda *args, **kwargs: fake_socket)

    await provider.connect(session_id="twilio_CA123", call_id="CA123", instructions="crisis only")
    event = await provider.receive_audio_event()

    assert event is not None
    assert event.event_type == RealtimeAudioEventType.ERROR
    assert event.fallback_reason == "provider_error"
    assert "bad realtime" in event.warnings[0]


@pytest.mark.asyncio
async def test_openai_provider_retries_when_input_transcription_is_rejected() -> None:
    fake_socket = FakeProviderSocket(
        [
            {
                "type": "error",
                "error": {
                    "message": "Unknown parameter: session.input_audio_transcription",
                    "param": "session.input_audio_transcription",
                },
            }
        ]
    )
    provider = AzureOpenAIRealtimeProvider(
        Settings(
            enable_realtime_voice=True,
            realtime_provider="azure_openai_realtime",
            azure_realtime_endpoint="https://aoai.example.openai.azure.com",
            azure_realtime_api_key="dummy-key",
            azure_realtime_deployment="gpt-realtime",
            azure_realtime_api_version="2025-04-01-preview",
            realtime_input_transcription_enabled=True,
        ),
        websocket_factory=lambda *args, **kwargs: fake_socket,
    )

    await provider.connect(session_id="twilio_CA123", call_id="CA123", instructions="crisis only")
    event = await provider.receive_audio_event()

    assert event is not None
    assert event.event_type == RealtimeAudioEventType.UNKNOWN_PROVIDER_EVENT
    assert fake_socket.sent[0]["session"]["input_audio_transcription"] == {"model": "whisper-1"}
    assert "input_audio_transcription" not in fake_socket.sent[1]["session"]
    assert "secret" not in str(event.metadata)
