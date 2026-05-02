from __future__ import annotations

import asyncio
from pathlib import Path

from app.core.config import Settings
from app.models.audio import CallerTurn
from app.models.triage import IncidentType, ProviderMode, TriageLevel, TriageResult
from app.services.azure_openai_triage_provider import AzureOpenAITriageProvider
from app.services.voice_agent_provider import ProviderHealth, TranscriptInput, VoiceProviderResult


UNCLEAR_TRANSCRIPT = ""


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
        if not self.settings.azure_speech_configured:
            return self._fallback_result(
                turn=turn,
                reason="Azure Speech credentials are incomplete.",
            )
        if not turn.audio_ref:
            return self._fallback_result(
                turn=turn,
                reason="Committed turn does not include an audio_ref.",
            )
        if not Path(turn.audio_ref).exists():
            return self._fallback_result(
                turn=turn,
                reason=f"Committed turn audio_ref does not exist: {turn.audio_ref}",
            )

        try:
            transcript = (await self.recognize_audio_ref(turn.audio_ref)).strip()
        except Exception as exc:
            return self._fallback_result(
                turn=turn,
                reason=f"Azure Speech recognition failed: {exc}",
            )

        if not transcript:
            return self._fallback_result(
                turn=turn,
                reason="Azure Speech did not return a usable transcript.",
            )

        triage = await self.triage_provider.triage_transcript(transcript, "th")
        return VoiceProviderResult(
            provider_mode=self.mode,
            transcript=transcript,
            transcript_source="azure_speech_stt",
            language=triage.language,
            confidence=triage.confidence,
            triage=triage,
            audio_ref=turn.audio_ref,
            provider_warnings=[],
        )

    async def recognize_audio_ref(self, audio_ref: str) -> str:
        import azure.cognitiveservices.speech as speechsdk

        speech_config = speechsdk.SpeechConfig(
            subscription=self.settings.azure_speech_key,
            region=self.settings.azure_speech_region,
        )
        speech_config.speech_recognition_language = "th-TH"
        audio_config = speechsdk.audio.AudioConfig(filename=audio_ref)
        recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
        result = await asyncio.to_thread(lambda: recognizer.recognize_once_async().get())
        if result.reason == speechsdk.ResultReason.RecognizedSpeech and result.text:
            return result.text
        return ""

    async def process_transcript(self, transcript_input: TranscriptInput) -> VoiceProviderResult:
        triage = await self.triage_provider.triage_transcript(
            transcript_input.transcript,
            transcript_input.language_hint,
        )
        return VoiceProviderResult(
            provider_mode=self.mode,
            transcript=transcript_input.transcript,
            transcript_source="fallback",
            language=triage.language,
            confidence=triage.confidence,
            triage=triage,
            provider_warnings=["Manual transcript input bypassed Azure Speech STT."],
        )

    def _fallback_result(self, turn: CallerTurn, reason: str) -> VoiceProviderResult:
        triage = TriageResult(
            language="th",
            incident_type=IncidentType.UNKNOWN,
            triage_level=TriageLevel.YELLOW,
            confidence=0.35,
            location_text="",
            people_affected=None,
            injuries="unknown due to missing or unclear speech transcript",
            immediate_needs=["human_review"],
            ai_summary="Speech recognition did not produce a usable transcript. Human review is required.",
            triage_reason=reason,
            human_review_required=True,
            missing_fields=["transcript", "location_text", "incident_type"],
        )
        return VoiceProviderResult(
            provider_mode=self.mode,
            transcript=UNCLEAR_TRANSCRIPT,
            transcript_source="fallback",
            language=triage.language,
            confidence=triage.confidence,
            triage=triage,
            audio_ref=turn.audio_ref,
            provider_warnings=[reason],
        )
