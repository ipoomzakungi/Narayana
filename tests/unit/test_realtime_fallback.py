from __future__ import annotations

import pytest

from app.core.config import Settings
from app.models.audio import AudioFrame
from app.models.realtime import RealtimeAudioEventType
from app.services.azure_openai_realtime_provider import AzureOpenAIRealtimeProvider
from app.services.realtime_voice_provider import get_realtime_provider


class FailingSocket:
    async def send(self, payload: str) -> None:
        raise RuntimeError("send failed")

    async def recv(self) -> str:
        raise RuntimeError("recv failed")

    async def close(self) -> None:
        return None


def test_missing_realtime_config_returns_not_configured_selection() -> None:
    selection = get_realtime_provider(
        Settings(enable_realtime_voice=True, realtime_provider="azure_openai_realtime")
    )

    assert selection.active_candidate is False
    assert selection.fallback_reason == "not_configured"
    assert selection.warnings


@pytest.mark.asyncio
async def test_provider_connect_failure_returns_safe_fallback() -> None:
    async def fail_connect(*args, **kwargs):
        raise RuntimeError("connect failed")

    provider = AzureOpenAIRealtimeProvider(
        Settings(
            enable_realtime_voice=True,
            realtime_provider="azure_openai_realtime",
            azure_realtime_endpoint="https://aoai.example.openai.azure.com",
            azure_realtime_api_key="secret",
            azure_realtime_deployment="gpt-realtime",
            azure_realtime_api_version="2025-04-01-preview",
        ),
        websocket_factory=fail_connect,
    )

    result = await provider.connect(session_id="twilio_CA123", call_id="CA123", instructions="crisis only")

    assert result.connected is False
    assert result.fallback_reason == "connect_failed"
    assert "connect failed" in result.warnings[0]


@pytest.mark.asyncio
async def test_provider_send_and_receive_failure_return_safe_fallback() -> None:
    provider = AzureOpenAIRealtimeProvider(
        Settings(
            enable_realtime_voice=True,
            realtime_provider="azure_openai_realtime",
            azure_realtime_endpoint="https://aoai.example.openai.azure.com",
            azure_realtime_api_key="secret",
            azure_realtime_deployment="gpt-realtime",
            azure_realtime_api_version="2025-04-01-preview",
        ),
        websocket_factory=lambda *args, **kwargs: FailingSocket(),
    )
    frame = AudioFrame(
        session_id="twilio_CA123",
        sequence=1,
        timestamp_ms=20,
        encoding="pcm16",
        sample_rate_hz=8000,
        channels=1,
        duration_ms=20,
        audio_base64="AAAA",
    )

    connect = await provider.connect(session_id="twilio_CA123", call_id="CA123", instructions="crisis only")
    send = await provider.send_audio_frame(frame)
    event = await provider.receive_audio_event()

    assert connect.connected is False or send.sent is False
    if send.sent is False:
        assert send.fallback_reason == "stream_failed"
    assert event is not None
    assert event.event_type == RealtimeAudioEventType.ERROR
    assert event.fallback_reason == "provider_error"
