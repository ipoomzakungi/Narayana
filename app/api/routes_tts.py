from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.models.tts import TTSRequest, TTSTestResponse
from app.services.azure_speech_tts_service import AzureSpeechTTSService

router = APIRouter(tags=["tts"])


@router.post("/api/tts/test", response_model=TTSTestResponse)
async def test_tts(request: TTSRequest, settings: Settings = Depends(get_settings)) -> TTSTestResponse:
    result = await AzureSpeechTTSService(settings).synthesize_twilio_mulaw(
        request.text,
        voice=request.voice,
        profile=request.profile,
        session_id="tts_test",
    )
    return TTSTestResponse(
        configured=result.configured,
        voice=result.voice,
        audio_format=result.audio_format,
        profile=result.profile,
        ssml_enabled=result.ssml_enabled,
        payload_count=result.payload_count,
        total_bytes=result.total_bytes,
        estimated_duration_ms=result.estimated_duration_ms,
        warnings=result.warnings,
        missing_variables=result.missing_variables,
    )
