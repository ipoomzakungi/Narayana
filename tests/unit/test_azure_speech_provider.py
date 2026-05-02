from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import Settings
from app.models.audio import CallerTurn
from app.models.triage import IncidentType, TriageLevel, TriageResult
from app.services.azure_speech_provider import AzureSpeechOpenAIProvider
from app.services.mock_voice_provider import THAI_SAMPLE


class FakeTriageProvider:
    def __init__(self) -> None:
        self.transcript: str | None = None

    async def triage_transcript(self, transcript: str, language_hint: str = "th") -> TriageResult:
        self.transcript = transcript
        return TriageResult(
            language=language_hint,
            incident_type=IncidentType.FLOOD,
            triage_level=TriageLevel.RED,
            confidence=0.91,
            location_text="หาดใหญ่",
            injuries="elderly person breathing difficulty",
            immediate_needs=["rescue", "medical"],
            ai_summary="Recognized Thai flood transcript.",
            triage_reason="Recognized transcript includes flood and breathing difficulty.",
            human_review_required=True,
        )


def azure_settings() -> Settings:
    return Settings(
        use_mock_services=False,
        azure_speech_key="speech-key",
        azure_speech_region="southeastasia",
        azure_openai_endpoint="https://example.openai.azure.com",
        azure_openai_api_key="openai-key",
        azure_openai_deployment="gpt-4o-mini",
        azure_openai_api_version="2024-08-01-preview",
    )


def turn(audio_ref: str | None) -> CallerTurn:
    return CallerTurn(
        session_id="session_1",
        turn_id="turn_1",
        duration_ms=100,
        pre_speech_padding_ms=200,
        silence_threshold_ms=750,
        audio_ref=audio_ref,
    )


@pytest.mark.asyncio
async def test_azure_speech_provider_uses_audio_ref_for_stt(tmp_path, monkeypatch) -> None:
    audio_ref = tmp_path / "turn.wav"
    audio_ref.write_bytes(b"RIFFfake")
    provider = AzureSpeechOpenAIProvider(azure_settings())
    fake_triage = FakeTriageProvider()
    provider.triage_provider = fake_triage

    async def fake_recognize(path: str) -> str:
        assert path == str(audio_ref)
        return "น้ำท่วมอยู่ที่หาดใหญ่ มีคนแก่หายใจลำบาก ติดอยู่ชั้นสอง"

    monkeypatch.setattr(provider, "recognize_audio_ref", fake_recognize)

    result = await provider.process_turn(turn(str(audio_ref)))

    assert result.transcript_source == "azure_speech_stt"
    assert result.audio_ref == str(audio_ref)
    assert result.transcript == fake_triage.transcript
    assert result.triage.triage_level == TriageLevel.RED


@pytest.mark.asyncio
async def test_missing_speech_credentials_return_safe_fallback(tmp_path) -> None:
    audio_ref = tmp_path / "turn.wav"
    audio_ref.write_bytes(b"RIFFfake")
    provider = AzureSpeechOpenAIProvider(Settings(use_mock_services=False))

    result = await provider.process_turn(turn(str(audio_ref)))

    assert result.transcript_source == "fallback"
    assert result.transcript != THAI_SAMPLE
    assert result.confidence < 0.75
    assert result.triage.human_review_required is True
    assert result.provider_warnings


@pytest.mark.asyncio
async def test_missing_audio_ref_returns_safe_fallback() -> None:
    provider = AzureSpeechOpenAIProvider(azure_settings())

    result = await provider.process_turn(turn(None))

    assert result.transcript_source == "fallback"
    assert result.transcript != THAI_SAMPLE
    assert "transcript" in result.triage.missing_fields
    assert result.triage.human_review_required is True


@pytest.mark.asyncio
async def test_recognizer_exception_returns_safe_fallback(tmp_path, monkeypatch) -> None:
    audio_ref = tmp_path / "turn.wav"
    audio_ref.write_bytes(b"RIFFfake")
    provider = AzureSpeechOpenAIProvider(azure_settings())

    async def fail_recognize(path: str) -> str:
        raise RuntimeError("recognizer failed")

    monkeypatch.setattr(provider, "recognize_audio_ref", fail_recognize)

    result = await provider.process_turn(turn(str(audio_ref)))

    assert result.transcript_source == "fallback"
    assert result.transcript != THAI_SAMPLE
    assert "recognizer failed" in " ".join(result.provider_warnings)
    assert result.triage.human_review_required is True


@pytest.mark.asyncio
async def test_empty_recognizer_text_returns_safe_fallback(tmp_path, monkeypatch) -> None:
    audio_ref = tmp_path / "turn.wav"
    audio_ref.write_bytes(b"RIFFfake")
    provider = AzureSpeechOpenAIProvider(azure_settings())

    async def empty_recognize(path: str) -> str:
        return "   "

    monkeypatch.setattr(provider, "recognize_audio_ref", empty_recognize)

    result = await provider.process_turn(turn(str(audio_ref)))

    assert result.transcript_source == "fallback"
    assert result.transcript != THAI_SAMPLE
    assert result.triage.confidence < 0.75
    assert result.triage.status == "pending"
