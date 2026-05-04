from __future__ import annotations

import base64

import pytest

from app.core.config import Settings
from app.services.azure_speech_tts_service import AzureSpeechTTSService, SAFE_SPOKEN_RESPONSE


@pytest.mark.asyncio
async def test_unconfigured_tts_returns_safe_metadata() -> None:
    service = AzureSpeechTTSService(Settings())

    result = await service.synthesize_twilio_mulaw("ตอนนี้อยู่จุดไหนคะ?")

    assert result.configured is False
    assert result.payload_count == 0
    assert result.total_bytes == 0
    assert "AZURE_SPEECH_KEY" in result.missing_variables
    assert "AZURE_SPEECH_REGION" in result.missing_variables
    assert result.payloads == []


@pytest.mark.asyncio
async def test_configured_tts_uses_mocked_mulaw_bytes() -> None:
    class MockService(AzureSpeechTTSService):
        async def _synthesize_audio_bytes(self, text: str, voice: str):
            return b"\xff" * 320, True, []

    result = await MockService(
        Settings(azure_speech_key="key", azure_speech_region="eastus")
    ).synthesize_twilio_mulaw("ตอนนี้อยู่จุดไหนคะ?")

    assert result.configured is True
    assert result.voice == "th-TH-PremwadeeNeural"
    assert result.payload_count == 2
    assert result.total_bytes == 320
    assert result.estimated_duration_ms == 40
    assert all(base64.b64decode(payload) for payload in result.payloads)


@pytest.mark.asyncio
async def test_configured_tts_converts_mocked_pcm_to_mulaw() -> None:
    pcm16 = b"".join(int(1200).to_bytes(2, "little", signed=True) for _ in range(160))

    class MockService(AzureSpeechTTSService):
        async def _synthesize_audio_bytes(self, text: str, voice: str):
            return pcm16, False, ["pcm fallback"]

    result = await MockService(
        Settings(azure_speech_key="key", azure_speech_region="eastus")
    ).synthesize_twilio_mulaw("ตอนนี้อยู่จุดไหนคะ?")

    assert result.configured is True
    assert result.total_bytes == 160
    assert result.payload_count == 1
    assert "pcm fallback" in result.warnings


@pytest.mark.asyncio
async def test_tts_failure_returns_warning_without_crashing() -> None:
    class FailingService(AzureSpeechTTSService):
        async def _synthesize_audio_bytes(self, text: str, voice: str):
            raise RuntimeError("network unavailable")

    result = await FailingService(
        Settings(azure_speech_key="key", azure_speech_region="eastus")
    ).synthesize_twilio_mulaw("ตอนนี้อยู่จุดไหนคะ?")

    assert result.configured is True
    assert result.payload_count == 0
    assert any("failed" in warning.lower() for warning in result.warnings)


@pytest.mark.parametrize(
    "unsafe_text",
    [
        "ส่งเจ้าหน้าที่ไปแล้วค่ะ",
        "รถพยาบาลกำลังไปค่ะ",
        "rescue dispatched",
        "diagnosis is asthma",
        "ปิดเคสนี้ได้ค่ะ",
    ],
)
def test_sanitize_replaces_unsafe_spoken_guidance(unsafe_text: str) -> None:
    service = AzureSpeechTTSService(Settings())

    sanitized, warnings = service.sanitize_spoken_text(unsafe_text)

    assert sanitized == SAFE_SPOKEN_RESPONSE
    assert warnings
    assert "dispatched" not in sanitized.lower()
    assert "รถพยาบาลกำลังไป" not in sanitized


def test_sanitize_shortens_overlong_text() -> None:
    service = AzureSpeechTTSService(Settings(tts_max_chars=20))

    sanitized, warnings = service.sanitize_spoken_text("ก" * 80)

    assert len(sanitized) == 20
    assert warnings


@pytest.mark.asyncio
async def test_warnings_do_not_include_payload_or_secret() -> None:
    class MockService(AzureSpeechTTSService):
        async def _synthesize_audio_bytes(self, text: str, voice: str):
            return b"\xff" * 160, True, []

    result = await MockService(
        Settings(azure_speech_key="super-secret", azure_speech_region="eastus")
    ).synthesize_twilio_mulaw("ตอนนี้อยู่จุดไหนคะ?")

    joined_warnings = " ".join(result.warnings)
    assert "super-secret" not in joined_warnings
    assert result.payloads[0] not in joined_warnings
