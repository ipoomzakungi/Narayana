from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

from app.core.config import Settings
from app.models.audio import CallerTurn
from app.models.triage import ProviderMode, TriageResult


TranscriptSource = Literal["mock", "azure_speech_stt", "fallback"]


@dataclass
class ProviderHealth:
    mode: ProviderMode
    configured: bool
    warnings: list[str] = field(default_factory=list)


@dataclass
class TranscriptInput:
    transcript: str
    language_hint: str = "th"
    caller_phone_optional: str | None = None


@dataclass
class VoiceProviderResult:
    provider_mode: ProviderMode
    transcript: str
    transcript_source: TranscriptSource
    language: str
    confidence: float
    triage: TriageResult
    audio_ref: str | None = None
    response_text: str | None = None
    provider_warnings: list[str] = field(default_factory=list)


class VoiceAgentProvider(Protocol):
    mode: ProviderMode

    async def process_transcript(self, transcript_input: TranscriptInput) -> VoiceProviderResult:
        ...

    async def process_turn(self, turn: CallerTurn) -> VoiceProviderResult:
        ...

    async def health(self) -> ProviderHealth:
        ...


def get_voice_provider(settings: Settings, requested_mode: ProviderMode | None = None) -> VoiceAgentProvider:
    from app.services.azure_speech_provider import AzureSpeechOpenAIProvider
    from app.services.azure_voice_live_provider import AzureVoiceLiveProvider
    from app.services.mock_voice_provider import MockVoiceProvider

    if requested_mode == ProviderMode.AZURE_VOICE_LIVE and settings.azure_voice_live_configured:
        return AzureVoiceLiveProvider(settings)

    if requested_mode == ProviderMode.AZURE_SPEECH_OPENAI:
        return AzureSpeechOpenAIProvider(settings)

    if settings.use_mock_services:
        return MockVoiceProvider()

    if settings.azure_speech_openai_configured:
        return AzureSpeechOpenAIProvider(settings)

    if settings.azure_voice_live_configured:
        return AzureVoiceLiveProvider(settings)

    return MockVoiceProvider(
        warnings=["Azure provider credentials are incomplete; mock provider fallback is active."]
    )
