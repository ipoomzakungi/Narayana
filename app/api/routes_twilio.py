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


def _with_tts_debug_metadata(payload: dict, settings, stream_sid: str | None) -> dict:
    if not _payload_response_text(payload):
        return payload
    updated = dict(payload)
    updated["tts"] = {
        "enabled": settings.enable_twilio_tts_response,
        "configured": settings.azure_speech_tts_configured,
        "voice": settings.azure_speech_voice,
        "audio_format": settings.tts_output_format,
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
    if not stream_sid:
        logger.warning("tts.failed session_id=%s call_id=%s reason=missing_twilio_streamSid", session_id, call_id)
        return

    service = AzureSpeechTTSService(settings)
    if not service.configured:
        logger.warning(
            "tts.failed session_id=%s call_id=%s streamSid=%s reason=azure_speech_tts_unconfigured missing_variables=%s",
            session_id,
            call_id,
            stream_sid,
            service.missing_variables(),
        )
        return

    logger.info(
        "tts.started session_id=%s call_id=%s streamSid=%s text_length=%s",
        session_id,
        call_id,
        stream_sid,
        len(response_text),
    )
    try:
        result = await service.synthesize_twilio_mulaw(response_text, session_id=session_id, call_id=call_id)
    except Exception as exc:
        logger.warning(
            "tts.failed session_id=%s call_id=%s streamSid=%s reason=%s",
            session_id,
            call_id,
            stream_sid,
            exc,
        )
        return
    if not result.configured or not result.payloads:
        logger.warning(
            "tts.failed session_id=%s call_id=%s streamSid=%s warnings=%s",
            session_id,
            call_id,
            stream_sid,
            result.warnings,
        )
        return

    for payload_base64 in result.payloads:
        await websocket.send_json(build_twilio_media_event(stream_sid, payload_base64))

    mark_name = f"narayana_tts_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    await websocket.send_json(build_twilio_mark_event(stream_sid, mark_name))
    logger.info(
        "tts.completed session_id=%s call_id=%s streamSid=%s chunk_count=%s estimated_duration_ms=%s",
        session_id,
        call_id,
        stream_sid,
        result.payload_count,
        result.estimated_duration_ms,
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
