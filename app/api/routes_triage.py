from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.models.triage import TriageFromTranscriptRequest, TriageResult
from app.services.safety_rules import apply_safety_rules
from app.services.voice_agent_provider import TranscriptInput, get_voice_provider

router = APIRouter(prefix="/api/triage", tags=["triage"])


@router.post("/from-transcript", response_model=TriageResult)
async def triage_from_transcript(
    request: TriageFromTranscriptRequest,
    settings: Settings = Depends(get_settings),
) -> TriageResult:
    provider = get_voice_provider(settings, request.provider_mode)
    result = await provider.process_transcript(
        TranscriptInput(
            transcript=request.transcript,
            language_hint=request.language_hint,
            caller_phone_optional=request.caller_phone_optional,
        )
    )
    return apply_safety_rules(result.triage, settings.low_confidence_threshold)
