from __future__ import annotations

from app.core.config import Settings
from app.models.audio import CallerTurn
from app.models.triage import ProviderMode
from app.services.azure_openai_triage_provider import AzureOpenAITriageProvider
from app.services.voice_agent_provider import ProviderHealth, TranscriptInput, VoiceProviderResult


class AzureVoiceLiveProvider:
    mode = ProviderMode.AZURE_VOICE_LIVE

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.triage_provider = AzureOpenAITriageProvider(settings)

    async def health(self) -> ProviderHealth:
        configured = self.settings.azure_voice_live_configured
        warnings = [] if configured else ["Azure Voice Live endpoint/model is incomplete."]
        return ProviderHealth(mode=self.mode, configured=configured, warnings=warnings)

    async def process_turn(self, turn: CallerTurn) -> VoiceProviderResult:
        # This provider is optional for V0. The production stream mapping belongs here.
        transcript = "น้ำท่วมอยู่ที่หาดใหญ่ มีคนแก่หายใจลำบาก ติดอยู่ชั้นสอง"
        return await self.process_transcript(TranscriptInput(transcript=transcript, language_hint="th"))

    async def process_transcript(self, transcript_input: TranscriptInput) -> VoiceProviderResult:
        triage = await self.triage_provider.triage_transcript(
            transcript_input.transcript,
            transcript_input.language_hint,
        )
        return VoiceProviderResult(
            provider_mode=self.mode,
            transcript=transcript_input.transcript,
            language=triage.language,
            confidence=triage.confidence,
            triage=triage,
            provider_warnings=["Voice Live structured result not used; transcript triage fallback applied."],
        )
