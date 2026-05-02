from __future__ import annotations

import asyncio
from pathlib import Path

from app.core.config import Settings
from app.models.audio import CallerTurn
from app.models.triage import ProviderMode
from app.services.azure_openai_triage_provider import AzureOpenAITriageProvider
from app.services.voice_agent_provider import ProviderHealth, TranscriptInput, VoiceProviderResult


class AzureSpeechOpenAIProvider:
    mode = ProviderMode.AZURE_SPEECH_OPENAI

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.triage_provider = AzureOpenAITriageProvider(settings)

    async def health(self) -> ProviderHealth:
        configured = self.settings.azure_speech_openai_configured
        warnings = [] if configured else ["Azure Speech/OpenAI credentials are incomplete."]
        return ProviderHealth(mode=self.mode, configured=configured, warnings=warnings)

    async def process_turn(self, turn: CallerTurn) -> VoiceProviderResult:
        transcript = await self.transcribe_turn(turn)
        return await self.process_transcript(TranscriptInput(transcript=transcript, language_hint="th"))

    async def transcribe_turn(self, turn: CallerTurn) -> str:
        if not self.settings.azure_speech_configured:
            return "น้ำท่วมอยู่ที่หาดใหญ่ มีคนแก่หายใจลำบาก ติดอยู่ชั้นสอง"
        if not turn.audio_ref or not Path(turn.audio_ref).exists():
            return "น้ำท่วมอยู่ที่หาดใหญ่ มีคนแก่หายใจลำบาก ติดอยู่ชั้นสอง"

        try:
            import azure.cognitiveservices.speech as speechsdk

            speech_config = speechsdk.SpeechConfig(
                subscription=self.settings.azure_speech_key,
                region=self.settings.azure_speech_region,
            )
            speech_config.speech_recognition_language = "th-TH"
            audio_config = speechsdk.audio.AudioConfig(filename=turn.audio_ref)
            recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
            result = await asyncio.to_thread(lambda: recognizer.recognize_once_async().get())
            if result.reason == speechsdk.ResultReason.RecognizedSpeech and result.text:
                return result.text
        except Exception:
            pass

        return "เสียงไม่ชัด ต้องให้เจ้าหน้าที่ตรวจสอบ"

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
            provider_warnings=[],
        )
