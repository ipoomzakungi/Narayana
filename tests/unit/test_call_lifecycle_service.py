from __future__ import annotations

from datetime import timedelta

from app.core.config import Settings
from app.models.intake import utc_now
from app.services.call_lifecycle_service import (
    NO_REPLY_FINAL_CLOSE_TEXT,
    NO_REPLY_PROMPT_TEXT,
    CallLifecycleService,
    CallLifecycleState,
)


def test_no_reply_prompt_after_greeting_threshold() -> None:
    service = CallLifecycleService(Settings(enable_twilio_initial_greeting=True, call_no_reply_seconds=10))
    state = CallLifecycleState(session_id="twilio_CA1", call_id="CA1")
    now = utc_now()
    service.track_greeting_sent(state, now - timedelta(seconds=11))

    assert service.should_prompt_no_reply(state, now) is True
    assert service.record_no_reply_prompt(state, now) == NO_REPLY_PROMPT_TEXT
    assert state.no_reply_prompt_count == 1


def test_no_reply_waits_while_assistant_playback_active() -> None:
    service = CallLifecycleService(Settings(enable_twilio_initial_greeting=True, call_no_reply_seconds=1))
    now = utc_now()
    state = CallLifecycleState(session_id="twilio_CA1", call_id="CA1")
    service.track_greeting_sent(state, now - timedelta(seconds=10))
    service.track_assistant_playback_started(
        state,
        mark_name="narayana_initial_greeting",
        purpose="greeting",
        estimated_duration_ms=30_000,
        when=now - timedelta(seconds=1),
    )

    assert service.should_prompt_no_reply(state, now) is False

    assert service.track_assistant_playback_completed(state, mark_name="narayana_initial_greeting", when=now) is True
    assert service.should_prompt_no_reply(state, now + timedelta(seconds=2)) is True


def test_playback_fallback_completion_allows_no_reply_prompt() -> None:
    service = CallLifecycleService(Settings(enable_twilio_initial_greeting=True, call_no_reply_seconds=0.01))
    now = utc_now()
    state = CallLifecycleState(session_id="twilio_CA1", call_id="CA1")
    service.track_greeting_sent(state, now - timedelta(seconds=1))
    service.track_assistant_playback_started(
        state,
        mark_name="narayana_initial_greeting",
        purpose="greeting",
        estimated_duration_ms=20,
        when=now - timedelta(seconds=1),
    )

    fallback_time = now + timedelta(seconds=0.02)
    assert service.should_prompt_no_reply(state, fallback_time) is False
    assert state.assistant_speaking is False
    assert service.should_prompt_no_reply(state, fallback_time + timedelta(seconds=0.02)) is True


def test_no_reply_final_close_after_max_prompts() -> None:
    service = CallLifecycleService(
        Settings(enable_twilio_initial_greeting=True, call_no_reply_prompt_seconds=5, call_max_no_reply_prompts=2)
    )
    now = utc_now()
    state = CallLifecycleState(
        session_id="twilio_CA1",
        call_id="CA1",
        greeting_sent_at=now - timedelta(seconds=30),
        last_no_reply_prompt_at=now - timedelta(seconds=6),
        no_reply_prompt_count=2,
    )

    assert service.should_close_for_no_reply(state, now) is True
    assert service.record_no_reply_close(state) == NO_REPLY_FINAL_CLOSE_TEXT
    assert state.call_end_recommended is True
    assert state.call_end_reason == "no_reply"


def test_caller_speech_resets_close_recommendation() -> None:
    service = CallLifecycleService(Settings(enable_twilio_initial_greeting=True))
    state = CallLifecycleState(session_id="twilio_CA1", call_id="CA1", call_end_recommended=True, call_end_reason="no_reply")

    service.track_caller_speech(state)

    assert state.last_caller_speech_at is not None
    assert state.call_end_recommended is False
    assert state.call_end_reason == ""


def test_lifecycle_disabled_without_tts_or_greeting() -> None:
    service = CallLifecycleService(Settings())
    state = CallLifecycleState(session_id="twilio_CA1", call_id="CA1", greeting_sent_at=utc_now())

    assert service.enabled is False
    assert service.should_prompt_no_reply(state) is False
    assert service.next_timeout_seconds(state) is None
