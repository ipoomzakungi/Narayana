from __future__ import annotations

import asyncio
import logging
import re
from typing import Any
from xml.sax.saxutils import escape as xml_escape

from app.core.config import Settings
from app.models.tts import TTSProfile, TTSResult
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
    r"official emergency hotline",
    r"official hotline replacement",
    r"สายด่วนฉุกเฉินอย่างเป็นทางการ",
    r"แทน(สายด่วน|หน่วยงานฉุกเฉิน|บริการฉุกเฉิน)",
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
        profile: TTSProfile | str = TTSProfile.NORMAL,
        session_id: str | None = None,
        call_id: str | None = None,
    ) -> TTSResult:
        selected_voice = voice or self.settings.azure_speech_voice
        selected_profile = TTSProfile(profile)
        safe_text, warnings = self.sanitize_spoken_text(text)
        if warnings and any("replaced" in warning for warning in warnings):
            selected_profile = TTSProfile.SAFE_FALLBACK

        if not self.configured:
            return TTSResult(
                configured=False,
                voice=selected_voice,
                audio_format=self.settings.tts_output_format,
                profile=selected_profile,
                ssml_enabled=self.settings.tts_use_ssml,
                warnings=[*warnings, "Azure Speech TTS is not configured."],
                missing_variables=self.missing_variables(),
                sanitized_text=safe_text,
            )

        try:
            audio_bytes, already_mulaw, synth_warnings = await self._synthesize_audio_bytes(
                safe_text,
                selected_voice,
                selected_profile,
            )
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
                profile=selected_profile,
                ssml_enabled=self.settings.tts_use_ssml,
                warnings=[*warnings, f"Azure Speech TTS failed: {exc}"],
                sanitized_text=safe_text,
            )

        if not audio_bytes:
            return TTSResult(
                configured=True,
                voice=selected_voice,
                audio_format=self.settings.tts_output_format,
                profile=selected_profile,
                ssml_enabled=self.settings.tts_use_ssml,
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
            profile=selected_profile,
            ssml_enabled=self.settings.tts_use_ssml,
            total_bytes=len(mulaw),
            estimated_duration_ms=estimate_audio_duration_ms(len(mulaw)),
            warnings=warnings,
            sanitized_text=safe_text,
        )
        return result.with_payloads(payloads)

    def _profile_prosody(self, profile: TTSProfile) -> tuple[str, str]:
        if profile == TTSProfile.FOLLOWUP:
            return self.settings.tts_rate_followup, self.settings.tts_pitch_normal
        if profile == TTSProfile.GREETING:
            return self.settings.tts_rate_greeting, self.settings.tts_pitch_greeting
        if profile == TTSProfile.RED:
            return self.settings.tts_rate_red, self.settings.tts_pitch_red
        if profile == TTSProfile.CLOSING:
            return self.settings.tts_rate_closing, self.settings.tts_pitch_closing
        if profile in {TTSProfile.UNCLEAR, TTSProfile.SAFE_FALLBACK}:
            return self.settings.tts_rate_unclear, self.settings.tts_pitch_normal
        return self.settings.tts_rate_normal, self.settings.tts_pitch_normal

    def build_ssml(self, text: str, voice: str, profile: TTSProfile | str = TTSProfile.NORMAL) -> str:
        selected_profile = TTSProfile(profile)
        rate, pitch = self._profile_prosody(selected_profile)
        escaped_text = xml_escape(text, entities={'"': "&quot;", "'": "&apos;"})
        escaped_voice = xml_escape(voice, entities={'"': "&quot;", "'": "&apos;"})
        escaped_rate = xml_escape(rate, entities={'"': "&quot;", "'": "&apos;"})
        escaped_pitch = xml_escape(pitch, entities={'"': "&quot;", "'": "&apos;"})
        escaped_volume = xml_escape(self.settings.tts_volume, entities={'"': "&quot;", "'": "&apos;"})
        voice_parts = voice.split("-")
        language = "-".join(voice_parts[:2]) if len(voice_parts) >= 2 else "th-TH"
        escaped_language = xml_escape(language, entities={'"': "&quot;", "'": "&apos;"})
        return (
            f'<speak version="1.0" xml:lang="{escaped_language}" '
            'xmlns="http://www.w3.org/2001/10/synthesis">'
            f'<voice name="{escaped_voice}">'
            f'<prosody rate="{escaped_rate}" pitch="{escaped_pitch}" volume="{escaped_volume}">'
            f"{escaped_text}"
            "</prosody>"
            "</voice>"
            "</speak>"
        )

    async def _synthesize_audio_bytes(
        self,
        text: str,
        voice: str,
        profile: TTSProfile,
    ) -> tuple[bytes, bool, list[str]]:
        return await asyncio.to_thread(self._synthesize_audio_bytes_sync, text, voice, profile)

    def _synthesize_audio_bytes_sync(
        self,
        text: str,
        voice: str,
        profile: TTSProfile,
    ) -> tuple[bytes, bool, list[str]]:
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
        if self.settings.tts_use_ssml:
            result = synthesizer.speak_ssml_async(self.build_ssml(text, voice, profile)).get()
        else:
            result = synthesizer.speak_text_async(text).get()
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return bytes(result.audio_data or b""), already_mulaw, warnings

        details: Any = getattr(result, "cancellation_details", None)
        error_details = getattr(details, "error_details", None) if details else None
        raise RuntimeError(error_details or f"Unexpected Azure Speech synthesis result: {result.reason}")
