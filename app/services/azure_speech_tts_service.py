from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from app.core.config import Settings
from app.models.tts import TTSResult
from app.services.twilio_audio_service import (
    chunk_mulaw_audio_for_twilio,
    encode_pcm16_to_mulaw,
    estimate_audio_duration_ms,
)

logger = logging.getLogger(__name__)

SAFE_SPOKEN_RESPONSE = "รับทราบค่ะ จะส่งข้อมูลให้เจ้าหน้าที่ตรวจสอบทันที กรุณาอยู่ในที่ปลอดภัยถ้าทำได้"

UNSAFE_SPOKEN_PATTERNS = [
    r"ส่ง(ทีม|เจ้าหน้าที่|รถ|กู้ภัย).*แล้ว",
    r"กู้ภัย.*(กำลังไป|ไปแล้ว|ถึงแล้ว)",
    r"รถพยาบาล(กำลัง|จะ|ได้).*ไป",
    r"ambulance.*(on the way|dispatched)",
    r"rescue.*(on the way|dispatched)",
    r"dispatch(ed)?",
    r"diagnos(e|is|ed)",
    r"วินิจฉัย",
    r"คุณเป็นโรค",
    r"ปิดเคส",
    r"ไม่ฉุกเฉิน",
    r"ไม่ต้องขอความช่วยเหลือ",
]


class AzureSpeechTTSService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def configured(self) -> bool:
        return self.settings.azure_speech_tts_configured

    def missing_variables(self) -> list[str]:
        return self.settings.missing_azure_speech_tts_variables()

    def sanitize_spoken_text(self, text: str) -> tuple[str, list[str]]:
        warnings: list[str] = []
        cleaned = " ".join(text.strip().split())
        if not cleaned:
            warnings.append("Response text was empty and was replaced with safe review language.")
            return SAFE_SPOKEN_RESPONSE, warnings

        lowered = cleaned.lower()
        if any(re.search(pattern, lowered, flags=re.IGNORECASE) for pattern in UNSAFE_SPOKEN_PATTERNS):
            warnings.append("Response text contained unsafe caller-facing guidance and was replaced.")
            return SAFE_SPOKEN_RESPONSE, warnings

        if len(cleaned) > self.settings.tts_max_chars:
            warnings.append("Response text exceeded TTS_MAX_CHARS and was shortened.")
            shortened = cleaned[: self.settings.tts_max_chars].rstrip()
            if any(re.search(pattern, shortened.lower(), flags=re.IGNORECASE) for pattern in UNSAFE_SPOKEN_PATTERNS):
                warnings.append("Shortened response remained unsafe and was replaced.")
                return SAFE_SPOKEN_RESPONSE, warnings
            return shortened or SAFE_SPOKEN_RESPONSE, warnings

        return cleaned, warnings

    async def synthesize_twilio_mulaw(
        self,
        text: str,
        *,
        voice: str | None = None,
        session_id: str | None = None,
        call_id: str | None = None,
    ) -> TTSResult:
        selected_voice = voice or self.settings.azure_speech_voice
        safe_text, warnings = self.sanitize_spoken_text(text)

        if not self.configured:
            return TTSResult(
                configured=False,
                voice=selected_voice,
                audio_format=self.settings.tts_output_format,
                warnings=[*warnings, "Azure Speech TTS is not configured."],
                missing_variables=self.missing_variables(),
                sanitized_text=safe_text,
            )

        try:
            audio_bytes, already_mulaw, synth_warnings = await self._synthesize_audio_bytes(safe_text, selected_voice)
            warnings.extend(synth_warnings)
        except Exception as exc:
            logger.warning(
                "tts.failed session_id=%s call_id=%s reason=%s",
                session_id,
                call_id,
                exc,
            )
            return TTSResult(
                configured=True,
                voice=selected_voice,
                audio_format=self.settings.tts_output_format,
                warnings=[*warnings, f"Azure Speech TTS failed: {exc}"],
                sanitized_text=safe_text,
            )

        if not audio_bytes:
            return TTSResult(
                configured=True,
                voice=selected_voice,
                audio_format=self.settings.tts_output_format,
                warnings=[*warnings, "Azure Speech TTS returned empty audio."],
                sanitized_text=safe_text,
            )

        mulaw = audio_bytes if already_mulaw else encode_pcm16_to_mulaw(audio_bytes)
        payloads = chunk_mulaw_audio_for_twilio(mulaw)
        if not payloads:
            warnings.append("Synthesized audio produced zero Twilio media chunks.")

        result = TTSResult(
            configured=True,
            voice=selected_voice,
            audio_format=self.settings.tts_output_format,
            total_bytes=len(mulaw),
            estimated_duration_ms=estimate_audio_duration_ms(len(mulaw)),
            warnings=warnings,
            sanitized_text=safe_text,
        )
        return result.with_payloads(payloads)

    async def _synthesize_audio_bytes(self, text: str, voice: str) -> tuple[bytes, bool, list[str]]:
        return await asyncio.to_thread(self._synthesize_audio_bytes_sync, text, voice)

    def _synthesize_audio_bytes_sync(self, text: str, voice: str) -> tuple[bytes, bool, list[str]]:
        import azure.cognitiveservices.speech as speechsdk

        warnings: list[str] = []
        speech_config = speechsdk.SpeechConfig(
            subscription=self.settings.azure_speech_key,
            region=self.settings.azure_speech_region,
        )
        speech_config.speech_synthesis_voice_name = voice

        output_format = getattr(speechsdk.SpeechSynthesisOutputFormat, "Raw8Khz8BitMonoMULaw", None)
        already_mulaw = output_format is not None
        if output_format is None:
            output_format = getattr(speechsdk.SpeechSynthesisOutputFormat, "Raw8Khz16BitMonoPcm")
            warnings.append("Raw 8 kHz mu-law output was unavailable; using PCM fallback conversion.")
        speech_config.set_speech_synthesis_output_format(output_format)

        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
        result = synthesizer.speak_text_async(text).get()
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return bytes(result.audio_data or b""), already_mulaw, warnings

        details: Any = getattr(result, "cancellation_details", None)
        error_details = getattr(details, "error_details", None) if details else None
        raise RuntimeError(error_details or f"Unexpected Azure Speech synthesis result: {result.reason}")
