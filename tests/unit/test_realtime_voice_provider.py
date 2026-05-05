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
    assert "Never say rescue has been dispatched" in instructions
    assert "Do not diagnose" in instructions


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
