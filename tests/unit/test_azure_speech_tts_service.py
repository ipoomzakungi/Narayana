from __future__ import annotations

import base64

import pytest

from app.core.config import Settings
from app.models.tts import TTSProfile
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
        async def _synthesize_audio_bytes(self, text: str, voice: str, profile: TTSProfile):
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
        async def _synthesize_audio_bytes(self, text: str, voice: str, profile: TTSProfile):
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
        async def _synthesize_audio_bytes(self, text: str, voice: str, profile: TTSProfile):
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
        async def _synthesize_audio_bytes(self, text: str, voice: str, profile: TTSProfile):
            return b"\xff" * 160, True, []

    result = await MockService(
        Settings(azure_speech_key="super-secret", azure_speech_region="eastus")
    ).synthesize_twilio_mulaw("ตอนนี้อยู่จุดไหนคะ?")

    joined_warnings = " ".join(result.warnings)
    assert "super-secret" not in joined_warnings
    assert result.payloads[0] not in joined_warnings


def test_build_ssml_escapes_text_and_uses_voice() -> None:
    service = AzureSpeechTTSService(Settings())

    ssml = service.build_ssml('อยู่ใกล้ "ตลาด" & โรงเรียนไหมคะ?', "th-TH-PremwadeeNeural")

    assert '&quot;ตลาด&quot;' in ssml
    assert "&amp;" in ssml
    assert 'voice name="th-TH-PremwadeeNeural"' in ssml
    assert 'xml:lang="th-TH"' in ssml


def test_red_profile_uses_slower_rate_and_pitch() -> None:
    service = AzureSpeechTTSService(Settings(tts_rate_red="-12%", tts_pitch_red="-2%"))

    ssml = service.build_ssml("รับทราบค่ะ", "th-TH-PremwadeeNeural", TTSProfile.RED)

    assert 'rate="-12%"' in ssml
    assert 'pitch="-2%"' in ssml


def test_followup_profile_uses_configured_rate() -> None:
    service = AzureSpeechTTSService(Settings(tts_rate_followup="-7%"))

    ssml = service.build_ssml("ตอนนี้อยู่จุดไหนคะ?", "th-TH-PremwadeeNeural", TTSProfile.FOLLOWUP)

    assert 'rate="-7%"' in ssml
    assert 'pitch="0%"' in ssml


def test_greeting_profile_uses_configured_rate_and_pitch() -> None:
    service = AzureSpeechTTSService(Settings(tts_rate_greeting="-6%", tts_pitch_greeting="-1%"))

    ssml = service.build_ssml("สวัสดีค่ะ แจ้งเหตุได้เลยค่ะ", "th-TH-PremwadeeNeural", TTSProfile.GREETING)

    assert 'rate="-6%"' in ssml
    assert 'pitch="-1%"' in ssml


@pytest.mark.asyncio
async def test_unsafe_dispatch_phrase_is_replaced_before_ssml() -> None:
    captured: dict[str, str] = {}

    class MockService(AzureSpeechTTSService):
        async def _synthesize_audio_bytes(self, text: str, voice: str, profile: TTSProfile):
            captured["text"] = text
            captured["ssml"] = self.build_ssml(text, voice, profile)
            return b"\xff" * 160, True, []

    result = await MockService(
        Settings(azure_speech_key="key", azure_speech_region="eastus")
    ).synthesize_twilio_mulaw("รถพยาบาลกำลังไปค่ะ", profile=TTSProfile.RED)

    assert captured["text"] == SAFE_SPOKEN_RESPONSE
    assert "รถพยาบาลกำลังไป" not in captured["ssml"]
    assert result.profile == TTSProfile.SAFE_FALLBACK


@pytest.mark.asyncio
async def test_unsafe_official_hotline_greeting_is_replaced_before_ssml() -> None:
    captured: dict[str, str] = {}

    class MockService(AzureSpeechTTSService):
        async def _synthesize_audio_bytes(self, text: str, voice: str, profile: TTSProfile):
            captured["text"] = text
            captured["ssml"] = self.build_ssml(text, voice, profile)
            return b"\xff" * 160, True, []

    result = await MockService(
        Settings(azure_speech_key="key", azure_speech_region="eastus")
    ).synthesize_twilio_mulaw(
        "นี่คือ official emergency hotline replacement",
        profile=TTSProfile.GREETING,
    )

    assert captured["text"] == SAFE_SPOKEN_RESPONSE
    assert "official emergency hotline" not in captured["ssml"]
    assert result.profile == TTSProfile.SAFE_FALLBACK


@pytest.mark.asyncio
async def test_tts_use_ssml_false_keeps_metadata_disabled() -> None:
    class MockService(AzureSpeechTTSService):
        async def _synthesize_audio_bytes(self, text: str, voice: str, profile: TTSProfile):
            return b"\xff" * 160, True, []

    result = await MockService(
        Settings(azure_speech_key="key", azure_speech_region="eastus", tts_use_ssml=False)
    ).synthesize_twilio_mulaw("ตอนนี้อยู่จุดไหนคะ?")

    assert result.ssml_enabled is False
