from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.core.config import Settings
from app.models.audio import CallerTurn
from app.services.azure_speech_provider import AzureSpeechOpenAIProvider
from app.services.mock_voice_provider import THAI_SAMPLE


def azure_manual_ready() -> bool:
    required = [
        "AZURE_SPEECH_KEY",
        "AZURE_SPEECH_REGION",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_DEPLOYMENT",
        "AZURE_OPENAI_API_VERSION",
        "AZURE_SPEECH_TEST_WAV",
    ]
    return all(os.getenv(name) for name in required) and Path(os.environ["AZURE_SPEECH_TEST_WAV"]).exists()


@pytest.mark.skipif(not azure_manual_ready(), reason="Azure Speech/OpenAI credentials and AZURE_SPEECH_TEST_WAV are required")
@pytest.mark.asyncio
async def test_manual_azure_speech_thai_wav_validation() -> None:
    audio_ref = os.environ["AZURE_SPEECH_TEST_WAV"]
    provider = AzureSpeechOpenAIProvider(Settings.from_env())
    turn = CallerTurn(
        session_id="manual_azure",
        turn_id="manual_turn",
        duration_ms=1000,
        pre_speech_padding_ms=200,
        silence_threshold_ms=750,
        audio_ref=audio_ref,
    )

    result = await provider.process_turn(turn)

    assert result.transcript_source == "azure_speech_stt"
    assert result.audio_ref == audio_ref
    assert result.transcript
    assert result.transcript != THAI_SAMPLE
    assert result.triage.status == "pending"
