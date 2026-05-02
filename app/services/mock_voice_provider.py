from __future__ import annotations

from app.models.audio import CallerTurn
from app.models.triage import IncidentType, ProviderMode, TriageLevel, TriageResult
from app.services.voice_agent_provider import ProviderHealth, TranscriptInput, VoiceProviderResult


THAI_SAMPLE = "น้ำท่วมอยู่ที่หาดใหญ่ มีคนแก่หายใจลำบาก ติดอยู่ชั้นสอง"


class MockVoiceProvider:
    mode = ProviderMode.MOCK

    def __init__(self, warnings: list[str] | None = None) -> None:
        self._warnings = warnings or []

    async def health(self) -> ProviderHealth:
        return ProviderHealth(mode=self.mode, configured=True, warnings=self._warnings)

    async def process_turn(self, turn: CallerTurn) -> VoiceProviderResult:
        result = await self.process_transcript(TranscriptInput(transcript=THAI_SAMPLE, language_hint="th"))
        result.audio_ref = turn.audio_ref
        return result

    async def process_transcript(self, transcript_input: TranscriptInput) -> VoiceProviderResult:
        transcript = transcript_input.transcript.strip()
        lower = transcript.lower()

        if "น้ำท่วม" in transcript or "flood" in lower:
            triage = TriageResult(
                language="th",
                incident_type=IncidentType.FLOOD,
                triage_level=TriageLevel.RED,
                confidence=0.92,
                location_text="หาดใหญ่" if "หาดใหญ่" in transcript else "Hat Yai",
                people_affected=None,
                injuries="elderly person breathing difficulty" if ("คนแก่" in transcript or "หายใจ" in transcript) else "",
                immediate_needs=["rescue", "medical"],
                caller_phone_optional=transcript_input.caller_phone_optional,
                ai_summary="Flood in Hat Yai with an elderly person trapped on the second floor and having breathing difficulty.",
                triage_reason="Caller reports flood, trapped elderly person, and breathing difficulty.",
                human_review_required=True,
                missing_fields=[],
            )
        elif "เสียงไม่ชัด" in transcript or "unclear" in lower or "noise" in lower:
            triage = TriageResult(
                language=transcript_input.language_hint,
                incident_type=IncidentType.UNKNOWN,
                triage_level=TriageLevel.YELLOW,
                confidence=0.45,
                location_text="",
                people_affected=None,
                injuries="unknown due to unclear speech",
                immediate_needs=["human_review"],
                caller_phone_optional=transcript_input.caller_phone_optional,
                ai_summary="Speech is unclear and needs human review.",
                triage_reason="Low confidence transcript requires human review.",
                human_review_required=True,
                missing_fields=["location_text", "incident_type"],
            )
        else:
            triage = TriageResult(
                language=transcript_input.language_hint,
                incident_type=IncidentType.UNKNOWN,
                triage_level=TriageLevel.GREEN,
                confidence=0.84,
                location_text="",
                people_affected=None,
                injuries="",
                immediate_needs=["information"],
                caller_phone_optional=transcript_input.caller_phone_optional,
                ai_summary="No immediate life-threatening detail detected in mock transcript.",
                triage_reason="Mock provider found no RED safety indicator.",
                human_review_required=False,
                missing_fields=["location_text"],
            )

        return VoiceProviderResult(
            provider_mode=self.mode,
            transcript=transcript,
            transcript_source="mock",
            language=triage.language,
            confidence=triage.confidence,
            triage=triage,
            response_text="รับทราบ ระบบจะส่งข้อมูลให้เจ้าหน้าที่ตรวจสอบ โปรดอยู่ในที่ปลอดภัยถ้าทำได้",
            provider_warnings=self._warnings,
        )
