from __future__ import annotations

from datetime import datetime, timezone
import logging
from urllib.parse import parse_qs
from xml.sax.saxutils import escape

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

from app.core.config import get_settings
from app.models.audio import VadState
from app.models.telephony import CallMetadata, TelephonyCodec, TelephonyProvider, VoiceInputMode
from app.models.triage import ProviderMode
from app.models.tts import TTSProfile
from app.services.audio_session_processor import AudioSessionProcessor
from app.services.azure_speech_tts_service import AzureSpeechTTSService
from app.services.twilio_audio_service import (
    TwilioMediaError,
    build_twilio_mark_event,
    build_twilio_media_event,
    normalize_twilio_media_message,
    twilio_call_metadata,
)

router = APIRouter(tags=["telephony-twilio"])
logger = logging.getLogger(__name__)


def _twilio_stream_url(public_base_url: str, call_id: str) -> str:
    base_url = public_base_url.rstrip("/")
    if base_url.startswith("https://"):
        base_url = "wss://" + base_url.removeprefix("https://")
    elif base_url.startswith("http://"):
        base_url = "ws://" + base_url.removeprefix("http://")
    elif not base_url.startswith(("ws://", "wss://")):
        base_url = "wss://" + base_url
    return f"{base_url}/ws/telephony/twilio/{call_id}"


async def _form_data(request: Request) -> dict[str, str]:
    body = (await request.body()).decode("utf-8")
    parsed = parse_qs(body, keep_blank_values=True)
    return {key: values[-1] if values else "" for key, values in parsed.items()}


@router.post("/api/telephony/twilio/incoming-call")
async def twilio_incoming_call(request: Request) -> Response:
    settings = get_settings()
    if not settings.twilio_webhook_public_base_url:
        raise HTTPException(status_code=503, detail="Twilio webhook public base URL is not configured.")

    form = await _form_data(request)
    call_id = form.get("CallSid")
    if not call_id:
        raise HTTPException(status_code=400, detail="Twilio CallSid is required.")

    stream_url = escape(_twilio_stream_url(settings.twilio_webhook_public_base_url, call_id))
    parameters = [('source_input_mode', 'twilio_call')]
    for name, value in (("From", form.get("From")), ("To", form.get("To")), ("FromCountry", form.get("FromCountry"))):
        if value:
            parameters.append((name, value))
    parameter_xml = "".join(
        f'<Parameter name="{escape(name)}" value="{escape(value)}" />' for name, value in parameters
    )
    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response><Connect>"
        f'<Stream url="{stream_url}">'
        f"{parameter_xml}"
        "</Stream>"
        "</Connect></Response>"
    )
    return Response(content=twiml, media_type="application/xml")


def _default_call_metadata(call_id: str) -> CallMetadata:
    settings = get_settings()
    return CallMetadata(
        provider=TelephonyProvider.TWILIO,
        call_id=call_id,
        from_number=settings.phone_test_number or None,
        to_number=settings.twilio_phone_number or None,
        country=settings.phone_test_country or None,
        codec=TelephonyCodec.MULAW,
        sample_rate=8000,
    )


def _twilio_stream_sid(message: dict) -> str | None:
    start = message.get("start") if isinstance(message.get("start"), dict) else {}
    stream_sid = start.get("streamSid") or message.get("streamSid")
    return str(stream_sid) if stream_sid else None


def _payload_response_text(payload: dict) -> str:
    response_text = payload.get("response_text")
    return response_text.strip() if isinstance(response_text, str) else ""


def _tts_profile_for_payload(payload: dict) -> TTSProfile:
    if payload.get("type") == "intake.followup":
        return TTSProfile.FOLLOWUP

    intake = payload.get("intake") if isinstance(payload.get("intake"), dict) else {}
    record = payload.get("record") if isinstance(payload.get("record"), dict) else {}
    case = record.get("case") if isinstance(record.get("case"), dict) else {}
    if payload.get("triage_level") == "RED" or case.get("triage_level") == "RED" or intake.get("action") == "escalate_human_review":
        return TTSProfile.RED

    transcript_source = str(payload.get("transcript_source") or "").lower()
    transcript = str(payload.get("transcript") or "").lower()
    if transcript_source == "fallback" or "unclear" in transcript_source or "เสียงไม่ชัด" in transcript:
        return TTSProfile.UNCLEAR

    return TTSProfile.NORMAL


def _with_tts_debug_metadata(payload: dict, settings, stream_sid: str | None) -> dict:
    if not _payload_response_text(payload):
        return payload
    profile = _tts_profile_for_payload(payload)
    updated = dict(payload)
    updated["tts"] = {
        "enabled": settings.enable_twilio_tts_response,
        "configured": settings.azure_speech_tts_configured,
        "voice": settings.azure_speech_voice,
        "audio_format": settings.tts_output_format,
        "profile": profile.value,
        "ssml_enabled": settings.tts_use_ssml,
        "stream_sid_present": bool(stream_sid),
    }
    return updated


async def _maybe_send_tts_response(
    websocket: WebSocket,
    *,
    payload: dict,
    settings,
    stream_sid: str | None,
    call_id: str,
    session_id: str,
) -> None:
    if not settings.enable_twilio_tts_response:
        return

    response_text = _payload_response_text(payload)
    if not response_text:
        return
    profile = _tts_profile_for_payload(payload)
    mark_name = f"narayana_tts_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

    await _send_tts_media(
        websocket,
        settings=settings,
        stream_sid=stream_sid,
        text=response_text,
        profile=profile,
        call_id=call_id,
        session_id=session_id,
        purpose="tts",
        mark_name=mark_name,
    )


async def _send_tts_media(
    websocket: WebSocket,
    *,
    settings,
    stream_sid: str | None,
    text: str,
    profile: TTSProfile | str,
    call_id: str,
    session_id: str,
    purpose: str,
    mark_name: str,
) -> None:
    if not stream_sid:
        logger.warning("%s.failed session_id=%s call_id=%s reason=missing_twilio_streamSid", purpose, session_id, call_id)
        return

    try:
        selected_profile = TTSProfile(profile)
    except ValueError:
        logger.warning(
            "%s.failed session_id=%s call_id=%s streamSid=%s reason=invalid_tts_profile:%s",
            purpose,
            session_id,
            call_id,
            stream_sid,
            profile,
        )
        selected_profile = TTSProfile.GREETING if purpose == "greeting" else TTSProfile.NORMAL

    service = AzureSpeechTTSService(settings)
    if not service.configured:
        logger.warning(
            "%s.failed session_id=%s call_id=%s streamSid=%s reason=azure_speech_tts_unconfigured missing_variables=%s",
            purpose,
            session_id,
            call_id,
            stream_sid,
            service.missing_variables(),
        )
        return

    logger.info(
        "%s.started session_id=%s call_id=%s streamSid=%s text_length=%s profile=%s",
        purpose,
        session_id,
        call_id,
        stream_sid,
        len(text),
        selected_profile.value,
    )
    try:
        result = await service.synthesize_twilio_mulaw(
            text,
            profile=selected_profile,
            session_id=session_id,
            call_id=call_id,
        )
    except Exception as exc:
        logger.warning(
            "%s.failed session_id=%s call_id=%s streamSid=%s reason=%s",
            purpose,
            session_id,
            call_id,
            stream_sid,
            exc,
        )
        return
    if not result.configured or not result.payloads:
        logger.warning(
            "%s.failed session_id=%s call_id=%s streamSid=%s warnings=%s",
            purpose,
            session_id,
            call_id,
            stream_sid,
            result.warnings,
        )
        return

    try:
        for payload_base64 in result.payloads:
            await websocket.send_json(build_twilio_media_event(stream_sid, payload_base64))

        await websocket.send_json(build_twilio_mark_event(stream_sid, mark_name))
    except Exception as exc:
        logger.warning(
            "%s.failed session_id=%s call_id=%s streamSid=%s reason=send_error:%s",
            purpose,
            session_id,
            call_id,
            stream_sid,
            exc,
        )
        return
    logger.info(
        "%s.completed session_id=%s call_id=%s streamSid=%s chunk_count=%s estimated_duration_ms=%s",
        purpose,
        session_id,
        call_id,
        stream_sid,
        result.payload_count,
        result.estimated_duration_ms,
    )


async def _send_initial_greeting(
    websocket: WebSocket,
    *,
    settings,
    stream_sid: str | None,
    call_id: str,
    session_id: str,
) -> None:
    if not settings.enable_twilio_initial_greeting:
        return
    await _send_tts_media(
        websocket,
        settings=settings,
        stream_sid=stream_sid,
        text=settings.twilio_initial_greeting_text,
        profile=settings.twilio_initial_greeting_profile,
        call_id=call_id,
        session_id=session_id,
        purpose="greeting",
        mark_name="narayana_initial_greeting",
    )


@router.websocket("/ws/telephony/twilio/{call_id}")
async def twilio_media_ws(websocket: WebSocket, call_id: str) -> None:
    await websocket.accept()
    settings = get_settings()
    session_id = f"twilio_{call_id}"
    stream_sid: str | None = None
    logger.info(
        "Twilio WebSocket started call_id=%s source_input_mode=%s",
        call_id,
        VoiceInputMode.TWILIO_CALL.value,
    )
    metadata = _default_call_metadata(call_id)
    initial_greeting_attempted = False
    processor = AudioSessionProcessor(
        settings=settings,
        session_id=session_id,
        source_input_mode=VoiceInputMode.TWILIO_CALL.value,
        call_metadata=metadata,
    )

    try:
        while True:
            try:
                message = await websocket.receive_json()
            except ValueError as exc:
                await websocket.send_json({"type": "error", "detail": f"Malformed Twilio media message: {exc}"})
                continue

            event = message.get("event")
            if event == "connected":
                continue

            if event == "start":
                stream_sid = _twilio_stream_sid(message)
                metadata = twilio_call_metadata(message, call_id, settings)
                processor = AudioSessionProcessor(
                    settings=settings,
                    session_id=session_id,
                    source_input_mode=VoiceInputMode.TWILIO_CALL.value,
                    call_metadata=metadata,
                )
                await websocket.send_json(
                    {
                        "type": "session.started",
                        "session_id": session_id,
                        "provider_mode": ProviderMode(settings.selected_provider).value,
                        "state": VadState.LISTENING.value,
                        "source_input_mode": VoiceInputMode.TWILIO_CALL.value,
                        "call_metadata": metadata.model_dump(mode="json"),
                    }
                )
                if not initial_greeting_attempted:
                    initial_greeting_attempted = True
                    await _send_initial_greeting(
                        websocket,
                        settings=settings,
                        stream_sid=stream_sid,
                        call_id=call_id,
                        session_id=session_id,
                    )
                continue

            if event == "media":
                try:
                    frame = normalize_twilio_media_message(
                        message,
                        session_id=session_id,
                        sample_rate_hz=metadata.sample_rate,
                        codec=metadata.codec,
                    )
                except TwilioMediaError as exc:
                    await websocket.send_json({"type": "error", "detail": str(exc)})
                    continue
                for payload in await processor.process_frame(frame):
                    payload = _with_tts_debug_metadata(payload, settings, stream_sid)
                    await websocket.send_json(payload)
                    await _maybe_send_tts_response(
                        websocket,
                        payload=payload,
                        settings=settings,
                        stream_sid=stream_sid,
                        call_id=call_id,
                        session_id=session_id,
                    )
                continue

            if event == "stop":
                await websocket.send_json({"type": "session.closed", "session_id": session_id})
                await websocket.close()
                return

            await websocket.send_json({"type": "error", "detail": f"Unsupported Twilio event: {event}"})
    except WebSocketDisconnect:
        return
