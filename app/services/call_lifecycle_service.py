from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.core.config import Settings

NO_REPLY_PROMPT_TEXT = "ยังอยู่ในสายไหมคะ หากต้องการแจ้งเหตุ กรุณาเล่าสถานการณ์สั้น ๆ ได้เลยค่ะ"
NO_REPLY_FINAL_CLOSE_TEXT = "หากไม่มีการตอบกลับ ระบบจะสิ้นสุดสายนี้นะคะ"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class CallLifecycleState:
    session_id: str
    call_id: str
    greeting_sent_at: datetime | None = None
    last_caller_speech_at: datetime | None = None
    last_no_reply_prompt_at: datetime | None = None
    no_reply_prompt_count: int = 0
    call_end_recommended: bool = False
    call_end_reason: str = ""


class CallLifecycleService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return self.settings.enable_twilio_initial_greeting or self.settings.enable_twilio_tts_response

    def track_greeting_sent(self, state: CallLifecycleState, when: datetime | None = None) -> None:
        state.greeting_sent_at = when or utc_now()

    def track_caller_speech(self, state: CallLifecycleState, when: datetime | None = None) -> None:
        state.last_caller_speech_at = when or utc_now()
        state.call_end_recommended = False
        state.call_end_reason = ""

    def build_no_reply_prompt(self) -> str:
        return NO_REPLY_PROMPT_TEXT

    def build_final_close_prompt(self) -> str:
        return NO_REPLY_FINAL_CLOSE_TEXT

    def should_prompt_no_reply(self, state: CallLifecycleState, now: datetime | None = None) -> bool:
        if not self.enabled or not self.settings.call_end_on_no_reply or not state.greeting_sent_at:
            return False
        if state.call_end_recommended or state.no_reply_prompt_count >= self.settings.call_max_no_reply_prompts:
            return False
        return self._seconds_since_reference(state, now or utc_now()) >= self._required_wait_seconds(state)

    def should_close_for_no_reply(self, state: CallLifecycleState, now: datetime | None = None) -> bool:
        if not self.enabled or not self.settings.call_end_on_no_reply or not state.greeting_sent_at:
            return False
        if state.no_reply_prompt_count < self.settings.call_max_no_reply_prompts:
            return False
        return self._seconds_since_reference(state, now or utc_now()) >= self.settings.call_no_reply_prompt_seconds

    def should_close_for_off_topic(self, off_topic_count: int) -> bool:
        return self.settings.call_end_on_repeated_off_topic and off_topic_count > self.settings.call_max_off_topic_redirects

    def record_no_reply_prompt(self, state: CallLifecycleState, when: datetime | None = None) -> str:
        state.no_reply_prompt_count += 1
        state.last_no_reply_prompt_at = when or utc_now()
        return self.build_no_reply_prompt()

    def record_no_reply_close(self, state: CallLifecycleState) -> str:
        state.call_end_recommended = True
        state.call_end_reason = "no_reply"
        return self.build_final_close_prompt()

    def next_timeout_seconds(self, state: CallLifecycleState, now: datetime | None = None) -> float | None:
        if not self.enabled or not self.settings.call_end_on_no_reply or not state.greeting_sent_at:
            return None
        if state.call_end_recommended:
            return None
        now = now or utc_now()
        if state.no_reply_prompt_count >= self.settings.call_max_no_reply_prompts:
            required = self.settings.call_no_reply_prompt_seconds
        else:
            required = self._required_wait_seconds(state)
        remaining = required - self._seconds_since_reference(state, now)
        return max(0.01, remaining)

    def _required_wait_seconds(self, state: CallLifecycleState) -> float:
        if state.no_reply_prompt_count == 0:
            return self.settings.call_no_reply_seconds
        return self.settings.call_no_reply_prompt_seconds

    def _seconds_since_reference(self, state: CallLifecycleState, now: datetime) -> float:
        references = [
            value for value in (state.greeting_sent_at, state.last_caller_speech_at, state.last_no_reply_prompt_at) if value
        ]
        reference = max(references) if references else None
        if reference is None:
            return 0.0
        return max(0.0, (now - reference).total_seconds())
