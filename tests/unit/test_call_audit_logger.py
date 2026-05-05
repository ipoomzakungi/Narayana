from __future__ import annotations

import logging

from app.core.config import Settings
from app.models.intake import ConversationSpeaker
from app.services.call_audit_logger import append_audit_event, log_call_event, safe_metadata
from app.services.intake_session_store import IntakeSessionStore


def test_safe_metadata_redacts_secrets_and_audio_payloads() -> None:
    safe = safe_metadata(
        {
            "AZURE_SPEECH_KEY": "secret",
            "nested": {"twilio_auth_token": "token", "payload": "abcd"},
            "streamSid": "MZ123",
        }
    )

    assert safe["AZURE_SPEECH_KEY"] == "[REDACTED]"
    assert safe["nested"]["twilio_auth_token"] == "[REDACTED]"
    assert safe["nested"]["payload"] == "[AUDIO_REDACTED]"
    assert safe["streamSid"] == "MZ123"


def test_log_call_event_uses_safe_metadata(caplog) -> None:
    logger = logging.getLogger("test.call_audit")

    with caplog.at_level(logging.INFO, logger="test.call_audit"):
        log_call_event(
            logger,
            "call.started",
            session_id="twilio_CA123",
            call_id="CA123",
            metadata={"payload": "abcd", "sequence": 1},
        )

    assert "call.started session_id=twilio_CA123 call_id=CA123" in caplog.text
    assert "payload=[AUDIO_REDACTED]" in caplog.text
    assert "abcd" not in caplog.text


def test_append_audit_event_honors_transcript_redaction() -> None:
    store = IntakeSessionStore()
    store.get_or_create("session_1")

    append_audit_event(
        store,
        Settings(call_audit_log_transcripts=False),
        "session_1",
        event_type="caller.turn.transcribed",
        speaker=ConversationSpeaker.CALLER,
        text="น้ำท่วมอยู่ที่หาดใหญ่",
        metadata={"audio_base64": "abcd"},
    )

    state = store.snapshot("session_1")
    assert state is not None
    assert state.timeline_events[0].text is None
    assert state.timeline_events[0].metadata["audio_base64"] == "[AUDIO_REDACTED]"
