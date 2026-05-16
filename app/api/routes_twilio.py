from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
from urllib.parse import parse_qs
from xml.sax.saxutils import escape

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

from app.core.config import get_settings
from app.models.audio import VadState
from app.models.intake import ConversationSpeaker, IntakeAction, IntakeCollectedFields, IntakeRequest
from app.models.realtime import RealtimeAudioEvent, RealtimeAudioEventType
from app.models.telephony import CallMetadata, TelephonyCodec, TelephonyProvider, VoiceInputMode
from app.models.triage import IncidentType, ProviderMode
from app.models.tts import TTSProfile
from app.services.audio_session_processor import AudioSessionProcessor
from app.services.azure_speech_tts_service import AzureSpeechTTSService
from app.services.call_audit_logger import append_audit_event, append_realtime_audit_event, log_call_event
from app.services.call_lifecycle_service import CallLifecycleService, CallLifecycleState
from app.services.intake_guardrails import evaluate_intake_guardrails
from app.services.intake_orchestrator import IntakeOrchestrator
from app.services.intake_session_store import get_intake_session_store
from app.services.realtime_voice_provider import (
    RealtimeProviderSelection,
    RealtimeVoiceProvider,
    build_realtime_instructions,
    get_realtime_provider,
)
from app.services.twilio_audio_service import (
    TwilioMediaError,
    build_twilio_clear_event,
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


def _twilio_mark_name(message: dict) -> str | None:
    mark = message.get("mark") if isinstance(message.get("mark"), dict) else {}
    name = mark.get("name")
    return str(name) if name else None


def _payload_response_text(payload: dict) -> str:
    response_text = payload.get("response_text")
    return response_text.strip() if isinstance(response_text, str) else ""


def _tts_profile_for_payload(payload: dict) -> TTSProfile:
    if payload.get("type") == "call.ending":
        return TTSProfile.CLOSING
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


def _realtime_debug_payload(selection: RealtimeProviderSelection) -> dict:
    return selection.debug_payload()


def _realtime_event_payload(
    event_type: str,
    *,
    session_id: str,
    call_id: str,
    provider: str,
    text: str | None = None,
    latency_ms: int | None = None,
    warnings: list[str] | None = None,
    fallback_reason: str | None = None,
    metadata: dict | None = None,
) -> dict:
    return {
        "type": f"realtime.{event_type}",
        "session_id": session_id,
        "call_id": call_id,
        "provider": provider,
        "text": text,
        "latency_ms": latency_ms,
        "warnings": warnings or [],
        "fallback_reason": fallback_reason,
        "metadata": metadata or {},
    }


def _log_realtime(
    *,
    settings,
    event_type: str,
    session_id: str,
    call_id: str,
    provider: str,
    speaker: ConversationSpeaker | None = None,
    text: str | None = None,
    latency_ms: int | None = None,
    warnings: list[str] | None = None,
    fallback_reason: str | None = None,
    metadata: dict | None = None,
) -> None:
    event_name = f"realtime.{event_type}"
    event_metadata = {
        "provider": provider,
        "latency_ms": latency_ms,
        "warnings": warnings or [],
        "fallback_reason": fallback_reason,
        **(metadata or {}),
    }
    log_call_event(logger, event_name, session_id=session_id, call_id=call_id, metadata=event_metadata)
    append_realtime_audit_event(
        get_intake_session_store(settings.assistant_max_followups),
        settings,
        session_id,
        event_type=event_name,
        provider=provider,
        call_id=call_id,
        speaker=speaker,
        text=text,
        latency_ms=latency_ms,
        warnings=warnings,
        fallback_reason=fallback_reason,
        metadata=metadata,
    )


async def _send_realtime_fallback(
    websocket: WebSocket,
    *,
    settings,
    session_id: str,
    call_id: str,
    provider: str,
    reason: str,
    warnings: list[str] | None = None,
    latency_ms: int | None = None,
) -> None:
    _record_realtime_fallback_state(settings=settings, session_id=session_id, reason=reason)
    _log_realtime(
        settings=settings,
        event_type="fallback",
        session_id=session_id,
        call_id=call_id,
        provider=provider,
        latency_ms=latency_ms,
        warnings=warnings,
        fallback_reason=reason,
    )
    await websocket.send_json(
        _realtime_event_payload(
            "fallback",
            session_id=session_id,
            call_id=call_id,
            provider=provider,
            latency_ms=latency_ms,
            warnings=warnings,
            fallback_reason=reason,
        )
    )


async def _drain_realtime_events(
    websocket: WebSocket,
    *,
    settings,
    provider: RealtimeVoiceProvider,
    stream_sid: str | None,
    session_id: str,
    call_id: str,
    max_events: int = 8,
) -> bool:
    for _ in range(max_events):
        try:
            event = await asyncio.wait_for(provider.receive_audio_event(), timeout=0.001)
        except asyncio.TimeoutError:
            return False
        except Exception as exc:
            _log_realtime(
                settings=settings,
                event_type="error",
                session_id=session_id,
                call_id=call_id,
                provider=provider.mode.value,
                warnings=[f"Realtime provider receive failed: {exc}"],
                fallback_reason="provider_error",
            )
            await _send_realtime_fallback(
                websocket,
                settings=settings,
                session_id=session_id,
                call_id=call_id,
                provider=provider.mode.value,
                reason="provider_error",
                warnings=[f"Realtime provider receive failed: {exc}"],
            )
            return True
        if event is None:
            return False
        fallback = await _handle_realtime_event(
            websocket,
            settings=settings,
            event=event,
            stream_sid=stream_sid,
            session_id=session_id,
            call_id=call_id,
        )
        if fallback:
            return True
    return False


def _realtime_model_or_deployment(settings, provider: str) -> str:
    if provider == "azure_voice_live":
        return settings.azure_voice_live_model
    return settings.azure_realtime_deployment


def _caller_tone(text: str) -> str:
    normalized = text.lower()
    if any(term in normalized for term in ("ช่วยด้วย", "กลัว", "panic", "scared", "screaming")):
        return "distressed"
    if any(term in normalized for term in ("ด่วน", "เร็ว", "urgent", "hurry")):
        return "urgent"
    return "unknown"


def _ensure_realtime_state(
    *,
    settings,
    session_id: str,
    call_id: str,
    provider: str,
    call_started_at: datetime | None = None,
    caller_phone: str | None = None,
) -> None:
    store = get_intake_session_store(settings.assistant_max_followups)
    state = store.get_or_create(
        session_id,
        call_id=call_id,
        source_input_mode=VoiceInputMode.TWILIO_CALL.value,
        max_followups=settings.assistant_max_followups,
    )
    state.realtime_provider = provider
    state.realtime_model_or_deployment = _realtime_model_or_deployment(settings, provider)
    if call_started_at and state.call_started_at is None:
        state.call_started_at = call_started_at
    if caller_phone and not state.collected_fields.caller_phone_optional:
        state.collected_fields.caller_phone_optional = caller_phone
    store.save(state)


def _record_realtime_fallback_state(*, settings, session_id: str, reason: str) -> None:
    store = get_intake_session_store(settings.assistant_max_followups)
    state = store.snapshot(session_id)
    if state is None:
        return
    state.fallback_reason = reason
    store.save(state)


def _append_realtime_transcript_turn(
    *,
    settings,
    session_id: str,
    call_id: str,
    provider: str,
    speaker: ConversationSpeaker,
    text: str,
    is_delta: bool,
    metadata: dict | None = None,
) -> None:
    clean = text.strip()
    if not clean:
        return
    store = get_intake_session_store(settings.assistant_max_followups)
    state = store.get_or_create(
        session_id,
        call_id=call_id,
        source_input_mode=VoiceInputMode.TWILIO_CALL.value,
        max_followups=settings.assistant_max_followups,
    )
    state.realtime_provider = provider
    state.realtime_model_or_deployment = _realtime_model_or_deployment(settings, provider)
    if speaker == ConversationSpeaker.CALLER:
        state.caller_tone = _caller_tone(clean)
    turn = {
        "speaker": speaker.value,
        "text": clean,
        "is_delta": is_delta,
        "provider": provider,
        "metadata": metadata or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    state.realtime_transcript_turns.append(turn)
    store.save(state)


def _merge_realtime_extraction_into_state(*, settings, session_id: str, arguments: dict) -> None:
    store = get_intake_session_store(settings.assistant_max_followups)
    state = store.snapshot(session_id)
    if state is None:
        return
    fields = state.collected_fields.model_copy(deep=True)
    language = arguments.get("language")
    if isinstance(language, str) and language.strip():
        fields.language = language
    incident_type = arguments.get("incident_type")
    if isinstance(incident_type, str):
        try:
            fields.incident_type = IncidentType(incident_type)
        except ValueError:
            fields.incident_type = IncidentType.UNKNOWN
    location = arguments.get("location")
    if isinstance(location, str) and location.strip():
        fields.location_text = location.strip()
    people_affected = arguments.get("people_affected")
    if isinstance(people_affected, int) and people_affected >= 0:
        fields.people_affected = people_affected
    injuries = arguments.get("injuries")
    if isinstance(injuries, str) and injuries.strip():
        fields.injuries = injuries.strip()
    needs = arguments.get("immediate_needs")
    if isinstance(needs, list):
        fields.immediate_needs = [str(item).strip() for item in needs if str(item).strip()]
    caller_phone = arguments.get("caller_phone")
    if isinstance(caller_phone, str) and caller_phone.strip():
        fields.caller_phone_optional = caller_phone.strip()
    missing = arguments.get("missing_fields")
    if isinstance(missing, list):
        fields.missing_fields = [str(item).strip() for item in missing if str(item).strip()]
    state.collected_fields = IntakeCollectedFields.model_validate(fields.model_dump())
    caller_tone = arguments.get("caller_tone")
    if isinstance(caller_tone, str) and caller_tone.strip():
        state.caller_tone = caller_tone.strip()
    action = arguments.get("recommended_operator_action")
    if isinstance(action, str) and action.strip():
        state.recommended_operator_action = action.strip()
    store.save(state)


def _transcript_from_realtime_extraction(arguments: dict) -> str:
    parts = [
        str(arguments.get("situation") or "").strip(),
        f"incident {arguments.get('incident_type')}" if arguments.get("incident_type") else "",
        f"ที่ {arguments.get('location')}" if arguments.get("location") else "",
        f"{arguments.get('people_affected')} คน" if arguments.get("people_affected") is not None else "",
        str(arguments.get("injuries") or "").strip(),
        " ".join(str(item) for item in arguments.get("immediate_needs") or []),
    ]
    return " ".join(part for part in parts if part).strip() or "ข้อมูลจาก realtime structured extraction"


async def _process_realtime_intake_text(
    *,
    websocket: WebSocket,
    settings,
    session_id: str,
    call_id: str,
    text: str,
    stream_sid: str | None,
    lifecycle_service: CallLifecycleService | None = None,
    lifecycle_state: CallLifecycleState | None = None,
) -> None:
    clean = text.strip()
    if not clean:
        return
    store = get_intake_session_store(settings.assistant_max_followups)
    state = store.snapshot(session_id)
    response = await IntakeOrchestrator(settings).process_transcript(
        IntakeRequest(
            session_id=session_id,
            transcript=clean,
            language_hint=settings.assistant_language,
            source_input_mode=VoiceInputMode.TWILIO_CALL.value,
            call_id=call_id,
            caller_phone_optional=state.collected_fields.caller_phone_optional if state else None,
        )
    )
    payload = _intake_response_payload(response, transcript=clean)
    await websocket.send_json(payload)
    if response.action != IntakeAction.ASK_FOLLOWUP and response.created_case is not None:
        store = get_intake_session_store(settings.assistant_max_followups)
        store.mark_final(session_id, response.created_case.case.case_id, response.partial_state.status)
    await _maybe_send_tts_response(
        websocket,
        payload=payload,
        settings=settings,
        stream_sid=stream_sid,
        call_id=call_id,
        session_id=session_id,
        lifecycle_service=lifecycle_service,
        lifecycle_state=lifecycle_state,
    )


def _intake_response_payload(response, *, transcript: str) -> dict:
    payload: dict = {
        "type": "intake.followup" if response.action == IntakeAction.ASK_FOLLOWUP else "triage.case.created",
        "session_id": response.session_id,
        "transcript": transcript,
        "provider_mode": ProviderMode.AZURE_OPENAI_REALTIME.value
        if response.partial_state.realtime_provider == ProviderMode.AZURE_OPENAI_REALTIME.value
        else (response.partial_state.realtime_provider or "realtime"),
        "transcript_source": "realtime",
        "response_text": response.response_text,
        "warnings": response.guardrail_warnings,
        "action": response.action.value,
        "case_group": response.case_group.value,
        "recommended_team": response.recommended_team,
        "triage_level": response.triage_level.value,
        "human_review_required": response.human_review_required,
        "missing_fields": response.missing_fields,
        "reason": response.reason,
        "guardrail_warnings": response.guardrail_warnings,
        "partial_state": response.partial_state.model_dump(mode="json"),
        "source_input_mode": VoiceInputMode.TWILIO_CALL.value,
    }
    if response.created_case is not None:
        payload["record"] = response.created_case.model_dump(mode="json")
        payload["intake"] = {
            "action": response.action.value,
            "case_group": response.case_group.value,
            "recommended_team": response.recommended_team,
            "missing_fields": response.missing_fields,
            "reason": response.reason,
            "guardrail_warnings": response.guardrail_warnings,
            "partial_state": response.partial_state.model_dump(mode="json"),
        }
    return payload


async def _finalize_realtime_call(
    *,
    websocket: WebSocket,
    settings,
    session_id: str,
    call_id: str,
    stream_sid: str | None,
) -> None:
    store = get_intake_session_store(settings.assistant_max_followups)
    state = store.snapshot(session_id)
    if state is None:
        return
    state.call_ended_at = datetime.now(timezone.utc)
    store.save(state)
    if state.final_case_id:
        return
    final_caller_turns = [
        turn.get("text", "")
        for turn in state.realtime_transcript_turns
        if turn.get("speaker") == ConversationSpeaker.CALLER.value and not turn.get("is_delta")
    ]
    if not final_caller_turns:
        final_caller_turns = [
            turn.get("text", "")
            for turn in state.realtime_transcript_turns
            if turn.get("speaker") == ConversationSpeaker.CALLER.value
        ]
    caller_text = " ".join(final_caller_turns).strip()
    if not caller_text:
        return
    guardrails = evaluate_intake_guardrails(caller_text, state)
    if not guardrails.forced_human_review and not guardrails.forced_triage_level:
        return
    await _process_realtime_intake_text(
        websocket=websocket,
        settings=settings,
        session_id=session_id,
        call_id=call_id,
        text=caller_text,
        stream_sid=stream_sid,
    )


async def _handle_realtime_event(
    websocket: WebSocket,
    *,
    settings,
    event: RealtimeAudioEvent,
    stream_sid: str | None,
    session_id: str,
    call_id: str,
) -> bool:
    provider = event.provider.value
    if event.event_type == RealtimeAudioEventType.ERROR:
        _log_realtime(
            settings=settings,
            event_type="error",
            session_id=session_id,
            call_id=call_id,
            provider=provider,
            latency_ms=event.latency_ms,
            warnings=event.warnings,
            fallback_reason=event.fallback_reason or "provider_error",
            metadata=event.metadata,
        )
        await _send_realtime_fallback(
            websocket,
            settings=settings,
            session_id=session_id,
            call_id=call_id,
            provider=provider,
            reason=event.fallback_reason or "provider_error",
            warnings=event.warnings,
            latency_ms=event.latency_ms,
        )
        return True

    event_type = event.event_type.value
    speaker = None
    if event.event_type in {
        RealtimeAudioEventType.CALLER_TRANSCRIPT_DELTA,
        RealtimeAudioEventType.CALLER_TRANSCRIPT_COMPLETED,
    }:
        speaker = ConversationSpeaker.CALLER
    elif event.event_type in {
        RealtimeAudioEventType.ASSISTANT_TRANSCRIPT_DELTA,
        RealtimeAudioEventType.ASSISTANT_TRANSCRIPT_COMPLETED,
    }:
        speaker = ConversationSpeaker.ASSISTANT
    _log_realtime(
        settings=settings,
        event_type=event_type,
        session_id=session_id,
        call_id=call_id,
        provider=provider,
        speaker=speaker,
        text=event.text,
        latency_ms=event.latency_ms,
        warnings=event.warnings,
        metadata=event.metadata,
    )
    await websocket.send_json(
        _realtime_event_payload(
            event_type,
            session_id=session_id,
            call_id=call_id,
            provider=provider,
            text=event.text,
            latency_ms=event.latency_ms,
            warnings=event.warnings,
            metadata=event.metadata,
        )
    )
    if speaker is not None and event.text:
        is_delta = event.event_type in {
            RealtimeAudioEventType.CALLER_TRANSCRIPT_DELTA,
            RealtimeAudioEventType.ASSISTANT_TRANSCRIPT_DELTA,
        }
        _append_realtime_transcript_turn(
            settings=settings,
            session_id=session_id,
            call_id=call_id,
            provider=provider,
            speaker=speaker,
            text=event.text,
            is_delta=is_delta,
            metadata=event.metadata,
        )
        if event.event_type == RealtimeAudioEventType.CALLER_TRANSCRIPT_COMPLETED:
            await _process_realtime_intake_text(
                websocket=websocket,
                settings=settings,
                session_id=session_id,
                call_id=call_id,
                text=event.text,
                stream_sid=stream_sid,
            )
    if event.event_type == RealtimeAudioEventType.STRUCTURED_EXTRACTION:
        arguments = event.metadata.get("tool_arguments") if isinstance(event.metadata, dict) else {}
        if isinstance(arguments, dict):
            _merge_realtime_extraction_into_state(settings=settings, session_id=session_id, arguments=arguments)
            await _process_realtime_intake_text(
                websocket=websocket,
                settings=settings,
                session_id=session_id,
                call_id=call_id,
                text=_transcript_from_realtime_extraction(arguments),
                stream_sid=stream_sid,
            )
    if event.event_type == RealtimeAudioEventType.OUTPUT_AUDIO_RECEIVED and event.audio_base64:
        if not stream_sid:
            await _send_realtime_fallback(
                websocket,
                settings=settings,
                session_id=session_id,
                call_id=call_id,
                provider=provider,
                reason="missing_twilio_streamSid",
                warnings=["Realtime output could not be sent because Twilio streamSid is missing."],
            )
            return True
        await websocket.send_json(build_twilio_media_event(stream_sid, event.audio_base64))
    return False


async def _maybe_send_tts_response(
    websocket: WebSocket,
    *,
    payload: dict,
    settings,
    stream_sid: str | None,
    call_id: str,
    session_id: str,
    lifecycle_service: CallLifecycleService | None = None,
    lifecycle_state: CallLifecycleState | None = None,
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
        lifecycle_service=lifecycle_service,
        lifecycle_state=lifecycle_state,
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
    lifecycle_service: CallLifecycleService | None = None,
    lifecycle_state: CallLifecycleState | None = None,
) -> bool:
    if not stream_sid:
        logger.warning("%s.failed session_id=%s call_id=%s reason=missing_twilio_streamSid", purpose, session_id, call_id)
        return False

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
        return False

    event_type = "greeting.started" if purpose == "greeting" else "tts.started"
    log_call_event(
        logger,
        event_type,
        session_id=session_id,
        call_id=call_id,
        metadata={"streamSid": stream_sid, "text_length": len(text), "profile": selected_profile.value, "purpose": purpose},
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
        return False
    if not result.configured or not result.payloads:
        logger.warning(
            "%s.failed session_id=%s call_id=%s streamSid=%s warnings=%s",
            purpose,
            session_id,
            call_id,
            stream_sid,
            result.warnings,
        )
        return False

    try:
        if lifecycle_service and lifecycle_state:
            lifecycle_service.track_assistant_playback_started(
                lifecycle_state,
                mark_name=mark_name,
                purpose=purpose,
                estimated_duration_ms=result.estimated_duration_ms,
            )
        store = get_intake_session_store(settings.assistant_max_followups)
        append_audit_event(
            store,
            settings,
            session_id,
            event_type=event_type,
            speaker=ConversationSpeaker.ASSISTANT,
            text=text,
            tts_profile=selected_profile.value,
            tts_status="started",
            metadata={"streamSid": stream_sid, "mark_name": mark_name, "chunk_count": result.payload_count, "purpose": purpose},
        )
        for payload_base64 in result.payloads:
            if lifecycle_state and lifecycle_state.active_mark_name != mark_name:
                break
            await websocket.send_json(build_twilio_media_event(stream_sid, payload_base64))

        if not lifecycle_state or lifecycle_state.active_mark_name == mark_name:
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
        return False
    logger.info(
        "%s.sent session_id=%s call_id=%s streamSid=%s chunk_count=%s estimated_duration_ms=%s",
        purpose,
        session_id,
        call_id,
        stream_sid,
        result.payload_count,
        result.estimated_duration_ms,
    )
    return True


async def _send_initial_greeting(
    websocket: WebSocket,
    *,
    settings,
    stream_sid: str | None,
    call_id: str,
    session_id: str,
    lifecycle_service: CallLifecycleService | None = None,
    lifecycle_state: CallLifecycleState | None = None,
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
        lifecycle_service=lifecycle_service,
        lifecycle_state=lifecycle_state,
    )


async def _handle_barge_in(
    websocket: WebSocket,
    *,
    settings,
    lifecycle_service: CallLifecycleService,
    lifecycle_state: CallLifecycleState,
    stream_sid: str | None,
    call_id: str,
    session_id: str,
    metadata: dict | None = None,
) -> None:
    if not lifecycle_state.assistant_speaking:
        return
    event_metadata = {
        "streamSid": stream_sid,
        "active_mark_name": lifecycle_state.active_mark_name,
        **(metadata or {}),
    }
    log_call_event(logger, "barge_in.detected", session_id=session_id, call_id=call_id, metadata=event_metadata)
    store = get_intake_session_store(settings.assistant_max_followups)
    append_audit_event(store, settings, session_id, event_type="barge_in.detected", metadata=event_metadata)
    lifecycle_service.track_assistant_playback_interrupted(lifecycle_state)
    if not stream_sid:
        return
    try:
        await websocket.send_json(build_twilio_clear_event(stream_sid))
    except Exception as exc:
        logger.warning("barge_in.clear_failed session_id=%s call_id=%s reason=%s", session_id, call_id, exc)
        return
    log_call_event(logger, "barge_in.clear_sent", session_id=session_id, call_id=call_id, metadata=event_metadata)
    append_audit_event(
        store,
        settings,
        session_id,
        event_type="barge_in.clear_sent",
        metadata={**event_metadata, "clear_sent": True},
    )


def _scope_debug_fields(state) -> dict:
    return {
        "off_topic_count": getattr(state, "off_topic_count", 0),
        "redirect_count": getattr(state, "redirect_count", 0),
        "no_reply_prompt_count": getattr(state, "no_reply_prompt_count", 0),
        "call_end_recommended": getattr(state, "call_end_recommended", False),
        "call_end_reason": getattr(state, "call_end_reason", ""),
        "last_assistant_redirect": getattr(state, "last_assistant_redirect", ""),
        "guardrail_warnings": getattr(state, "guardrail_warnings", []),
    }


async def _send_no_reply_prompt(
    websocket: WebSocket,
    *,
    settings,
    lifecycle_service: CallLifecycleService,
    lifecycle_state: CallLifecycleState,
    stream_sid: str | None,
    call_id: str,
    session_id: str,
) -> bool:
    store = get_intake_session_store(settings.assistant_max_followups)
    state = store.get_or_create(
        session_id,
        call_id=call_id,
        source_input_mode=VoiceInputMode.TWILIO_CALL.value,
        max_followups=settings.assistant_max_followups,
    )

    if lifecycle_service.should_close_for_no_reply(lifecycle_state):
        response_text = lifecycle_service.record_no_reply_close(lifecycle_state)
        state = store.mark_call_end_recommended(session_id, "no_reply", response_text)
        state.no_reply_prompt_count = lifecycle_state.no_reply_prompt_count
        store.save(state)
        payload = {
            "type": "call.ending",
            "session_id": session_id,
            "response_text": response_text,
            **_scope_debug_fields(state),
        }
        log_call_event(logger, "call.closed", session_id=session_id, call_id=call_id, metadata={"reason": "no_reply"})
        append_audit_event(
            store,
            settings,
            session_id,
            event_type="call.closed",
            speaker=ConversationSpeaker.ASSISTANT,
            text=response_text,
            metadata={"reason": "no_reply"},
        )
        await websocket.send_json(payload)
        await _send_tts_media(
            websocket,
            settings=settings,
            stream_sid=stream_sid,
            text=response_text,
            profile=TTSProfile.CLOSING,
            call_id=call_id,
            session_id=session_id,
            purpose="call.no_reply_close",
            mark_name="narayana_no_reply_close",
            lifecycle_service=lifecycle_service,
            lifecycle_state=lifecycle_state,
        )
        await websocket.close()
        return True

    if lifecycle_service.should_prompt_no_reply(lifecycle_state):
        response_text = lifecycle_service.record_no_reply_prompt(lifecycle_state)
        state = store.record_no_reply_prompt(session_id, response_text)
        payload = {
            "type": "call.no_reply_prompt",
            "session_id": session_id,
            "response_text": response_text,
            **_scope_debug_fields(state),
        }
        log_call_event(
            logger,
            "no_reply.prompt",
            session_id=session_id,
            call_id=call_id,
            metadata={"no_reply_prompt_count": lifecycle_state.no_reply_prompt_count},
        )
        append_audit_event(
            store,
            settings,
            session_id,
            event_type="no_reply.prompt",
            speaker=ConversationSpeaker.ASSISTANT,
            text=response_text,
            metadata={"no_reply_prompt_count": lifecycle_state.no_reply_prompt_count},
        )
        await websocket.send_json(payload)
        await _send_tts_media(
            websocket,
            settings=settings,
            stream_sid=stream_sid,
            text=response_text,
            profile=TTSProfile.FOLLOWUP,
            call_id=call_id,
            session_id=session_id,
            purpose="call.no_reply_prompt",
            mark_name=f"narayana_no_reply_{lifecycle_state.no_reply_prompt_count}",
            lifecycle_service=lifecycle_service,
            lifecycle_state=lifecycle_state,
        )
    return False


@router.websocket("/ws/telephony/twilio/{call_id}")
async def twilio_media_ws(websocket: WebSocket, call_id: str) -> None:
    await websocket.accept()
    settings = get_settings()
    session_id = f"twilio_{call_id}"
    stream_sid: str | None = None
    log_call_event(
        logger,
        "call.started",
        session_id=session_id,
        call_id=call_id,
        metadata={"source_input_mode": VoiceInputMode.TWILIO_CALL.value},
    )
    metadata = _default_call_metadata(call_id)
    initial_greeting_attempted = False
    lifecycle_service = CallLifecycleService(settings)
    lifecycle_state = CallLifecycleState(session_id=session_id, call_id=call_id)
    realtime_selection = get_realtime_provider(settings)
    realtime_provider: RealtimeVoiceProvider | None = None
    realtime_active = False
    processor = AudioSessionProcessor(
        settings=settings,
        session_id=session_id,
        source_input_mode=VoiceInputMode.TWILIO_CALL.value,
        call_metadata=metadata,
    )

    try:
        while True:
            try:
                timeout_seconds = lifecycle_service.next_timeout_seconds(lifecycle_state)
                if timeout_seconds is None:
                    message = await websocket.receive_json()
                else:
                    message = await asyncio.wait_for(websocket.receive_json(), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                should_close = await _send_no_reply_prompt(
                    websocket,
                    settings=settings,
                    lifecycle_service=lifecycle_service,
                    lifecycle_state=lifecycle_state,
                    stream_sid=stream_sid,
                    call_id=call_id,
                    session_id=session_id,
                )
                if should_close:
                    return
                continue
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
                lifecycle_state = CallLifecycleState(session_id=session_id, call_id=metadata.call_id)
                if realtime_selection.enabled:
                    _ensure_realtime_state(
                        settings=settings,
                        session_id=session_id,
                        call_id=call_id,
                        provider=realtime_selection.provider_mode.value,
                        call_started_at=metadata.started_at,
                        caller_phone=metadata.from_number,
                    )
                await websocket.send_json(
                    {
                        "type": "session.started",
                        "session_id": session_id,
                        "provider_mode": ProviderMode(settings.selected_provider).value,
                        "state": VadState.LISTENING.value,
                        "source_input_mode": VoiceInputMode.TWILIO_CALL.value,
                        "call_metadata": metadata.model_dump(mode="json"),
                        "realtime": _realtime_debug_payload(realtime_selection),
                    }
                )
                realtime_selection = get_realtime_provider(settings)
                if realtime_selection.active_candidate and realtime_selection.provider is not None:
                    connection = await realtime_selection.provider.connect(
                        session_id=session_id,
                        call_id=call_id,
                        instructions=build_realtime_instructions(settings),
                    )
                    if connection.connected:
                        realtime_provider = realtime_selection.provider
                        realtime_active = True
                        _log_realtime(
                            settings=settings,
                            event_type="connected",
                            session_id=session_id,
                            call_id=call_id,
                            provider=connection.provider.value,
                            latency_ms=connection.latency_ms,
                            warnings=connection.warnings,
                        )
                        await websocket.send_json(
                            _realtime_event_payload(
                                "connected",
                                session_id=session_id,
                                call_id=call_id,
                                provider=connection.provider.value,
                                latency_ms=connection.latency_ms,
                                warnings=connection.warnings,
                            )
                        )
                    else:
                        await _send_realtime_fallback(
                            websocket,
                            settings=settings,
                            session_id=session_id,
                            call_id=call_id,
                            provider=connection.provider.value,
                            reason=connection.fallback_reason or "connect_failed",
                            warnings=connection.warnings,
                            latency_ms=connection.latency_ms,
                        )
                elif realtime_selection.enabled:
                    await _send_realtime_fallback(
                        websocket,
                        settings=settings,
                        session_id=session_id,
                        call_id=call_id,
                        provider=realtime_selection.provider_mode.value,
                        reason=realtime_selection.fallback_reason or "not_configured",
                        warnings=realtime_selection.warnings,
                    )
                if not initial_greeting_attempted:
                    initial_greeting_attempted = True
                    await _send_initial_greeting(
                        websocket,
                        settings=settings,
                        stream_sid=stream_sid,
                        call_id=call_id,
                        session_id=session_id,
                        lifecycle_service=lifecycle_service,
                        lifecycle_state=lifecycle_state,
                    )
                if lifecycle_service.enabled:
                    lifecycle_service.track_greeting_sent(lifecycle_state)
                    if not lifecycle_state.assistant_speaking:
                        lifecycle_service.track_assistant_playback_completed(lifecycle_state)
                    store = get_intake_session_store(settings.assistant_max_followups)
                    state = store.get_or_create(
                        session_id,
                        call_id=metadata.call_id,
                        source_input_mode=VoiceInputMode.TWILIO_CALL.value,
                        max_followups=settings.assistant_max_followups,
                    )
                    state.greeting_sent_at = lifecycle_state.greeting_sent_at
                    store.save(state)
                continue

            if event == "mark":
                mark_name = _twilio_mark_name(message)
                completed = lifecycle_service.track_assistant_playback_completed(lifecycle_state, mark_name=mark_name)
                event_type = "greeting.completed" if mark_name == "narayana_initial_greeting" else "tts.completed"
                store = get_intake_session_store(settings.assistant_max_followups)
                if completed:
                    log_call_event(
                        logger,
                        event_type,
                        session_id=session_id,
                        call_id=call_id,
                        metadata={"streamSid": stream_sid, "mark_name": mark_name},
                    )
                    append_audit_event(
                        store,
                        settings,
                        session_id,
                        event_type=event_type,
                        tts_status="completed",
                        metadata={"streamSid": stream_sid, "mark_name": mark_name},
                    )
                    await websocket.send_json(
                        {
                            "type": "assistant.playback.completed",
                            "session_id": session_id,
                            "call_id": call_id,
                            "stream_sid": stream_sid,
                            "mark_name": mark_name,
                        }
                    )
                else:
                    logger.warning(
                        "tts.mark_unmatched session_id=%s call_id=%s streamSid=%s mark_name=%s active_mark_name=%s",
                        session_id,
                        call_id,
                        stream_sid,
                        mark_name,
                        lifecycle_state.active_mark_name,
                    )
                continue

            if event == "media":
                lifecycle_service.maybe_complete_expired_playback(lifecycle_state)
                try:
                    frame = normalize_twilio_media_message(
                        message,
                        session_id=session_id,
                        sample_rate_hz=metadata.sample_rate,
                        codec=metadata.codec,
                        assistant_is_speaking=lifecycle_state.assistant_speaking,
                    )
                except TwilioMediaError as exc:
                    await websocket.send_json({"type": "error", "detail": str(exc)})
                    continue
                if realtime_active and realtime_provider is not None:
                    send_result = await realtime_provider.send_audio_frame(frame)
                    if send_result.sent:
                        _log_realtime(
                            settings=settings,
                            event_type="audio.input.sent",
                            session_id=session_id,
                            call_id=call_id,
                            provider=send_result.provider.value,
                            latency_ms=send_result.latency_ms,
                            warnings=send_result.warnings,
                            metadata={"sequence": frame.sequence},
                        )
                        await websocket.send_json(
                            _realtime_event_payload(
                                "audio.input.sent",
                                session_id=session_id,
                                call_id=call_id,
                                provider=send_result.provider.value,
                                latency_ms=send_result.latency_ms,
                                warnings=send_result.warnings,
                                metadata={"sequence": frame.sequence},
                            )
                        )
                        fallback_to_current = await _drain_realtime_events(
                            websocket,
                            settings=settings,
                            provider=realtime_provider,
                            stream_sid=stream_sid,
                            session_id=session_id,
                            call_id=call_id,
                        )
                        if not fallback_to_current:
                            continue
                    else:
                        await _send_realtime_fallback(
                            websocket,
                            settings=settings,
                            session_id=session_id,
                            call_id=call_id,
                            provider=send_result.provider.value,
                            reason=send_result.fallback_reason or "stream_failed",
                            warnings=send_result.warnings,
                            latency_ms=send_result.latency_ms,
                        )
                    realtime_active = False
                    await realtime_provider.close()
                    realtime_provider = None
                processed_payloads = await processor.process_frame(frame)
                if any(
                    payload.get("type") == "debug.event"
                    and payload.get("event", {}).get("event_type") == "barge_in.detected"
                    for payload in processed_payloads
                ):
                    await _handle_barge_in(
                        websocket,
                        settings=settings,
                        lifecycle_service=lifecycle_service,
                        lifecycle_state=lifecycle_state,
                        stream_sid=stream_sid,
                        call_id=call_id,
                        session_id=session_id,
                        metadata={"sequence": frame.sequence},
                    )
                if any(payload.get("type") in {"intake.followup", "triage.case.created"} for payload in processed_payloads):
                    lifecycle_service.track_caller_speech(lifecycle_state)
                for payload in processed_payloads:
                    payload = _with_tts_debug_metadata(payload, settings, stream_sid)
                    await websocket.send_json(payload)
                    await _maybe_send_tts_response(
                        websocket,
                        payload=payload,
                        settings=settings,
                        stream_sid=stream_sid,
                        call_id=call_id,
                        session_id=session_id,
                        lifecycle_service=lifecycle_service,
                        lifecycle_state=lifecycle_state,
                    )
                continue

            if event == "stop":
                log_call_event(logger, "call.closed", session_id=session_id, call_id=call_id, metadata={"reason": "twilio_stop"})
                if realtime_selection.enabled:
                    await _finalize_realtime_call(
                        websocket=websocket,
                        settings=settings,
                        session_id=session_id,
                        call_id=call_id,
                        stream_sid=stream_sid,
                    )
                if realtime_provider is not None:
                    await realtime_provider.close()
                await websocket.send_json({"type": "session.closed", "session_id": session_id})
                await websocket.close()
                return

            await websocket.send_json({"type": "error", "detail": f"Unsupported Twilio event: {event}"})
    except WebSocketDisconnect:
        if realtime_provider is not None:
            await realtime_provider.close()
        return
