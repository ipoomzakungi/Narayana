from __future__ import annotations

import logging
from typing import Any

from app.core.config import Settings
from app.models.intake import ConversationSpeaker
from app.services.intake_session_store import IntakeSessionStore

SENSITIVE_KEY_PARTS = ("key", "token", "secret", "authorization", "password", "auth")
AUDIO_KEY_PARTS = ("payload", "audio_base64", "audio_payload", "base64")


def safe_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    if not metadata:
        return {}
    return {str(key): _redact_value(str(key), value) for key, value in metadata.items()}


def log_call_event(
    logger: logging.Logger,
    event_type: str,
    *,
    session_id: str,
    call_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    level: int = logging.INFO,
) -> None:
    safe = safe_metadata(metadata)
    details = " ".join(f"{key}={value}" for key, value in safe.items())
    message = f"{event_type} session_id={session_id}"
    if call_id:
        message += f" call_id={call_id}"
    if details:
        message += f" {details}"
    logger.log(level, message)


def append_audit_event(
    store: IntakeSessionStore,
    settings: Settings,
    session_id: str,
    *,
    event_type: str,
    speaker: ConversationSpeaker | None = None,
    text: str | None = None,
    tts_profile: str | None = None,
    tts_status: str | None = None,
    triage_level=None,
    case_group: str | None = None,
    recommended_team: str | None = None,
    guardrail_warnings: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    if not settings.call_audit_enabled:
        return
    if store.snapshot(session_id) is None:
        return
    store.append_timeline_event(
        session_id,
        event_type=event_type,
        speaker=speaker,
        text=text,
        tts_profile=tts_profile,
        tts_status=tts_status,
        triage_level=triage_level,
        case_group=case_group,
        recommended_team=recommended_team,
        guardrail_warnings=guardrail_warnings,
        metadata=safe_metadata(metadata),
        log_transcripts=settings.call_audit_log_transcripts,
        max_sessions=settings.call_audit_max_sessions,
    )


def _redact_value(key: str, value: Any) -> Any:
    normalized_key = key.lower()
    if any(part in normalized_key for part in SENSITIVE_KEY_PARTS):
        return "[REDACTED]"
    if any(part in normalized_key for part in AUDIO_KEY_PARTS):
        return "[AUDIO_REDACTED]"
    if isinstance(value, dict):
        return {str(child_key): _redact_value(str(child_key), child_value) for child_key, child_value in value.items()}
    if isinstance(value, list):
        return [_redact_value(key, item) for item in value]
    return value
