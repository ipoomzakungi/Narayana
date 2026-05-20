from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.config import Settings
from app.models.intake import IntakeSessionState
from app.services.intake_guardrails import RED_PATTERNS, VULNERABLE_PATTERNS

OFF_TOPIC_REDIRECT_TEXT = (
    "ขออภัยค่ะ ระบบนี้ใช้สำหรับรับแจ้งเหตุหรือขอความช่วยเหลือเท่านั้น "
    "หากต้องการแจ้งเหตุ กรุณาบอกสถานการณ์และสถานที่ค่ะ"
)
OFF_TOPIC_FINAL_TEXT = "ขออภัยค่ะ หากไม่มีเหตุที่ต้องการแจ้ง ระบบจะสิ้นสุดสายนี้นะคะ"

OFF_TOPIC_PATTERNS: dict[str, tuple[str, ...]] = {
    "joke_entertainment": ("เล่าเรื่องตลก", "มุกตลก", "joke", "funny", "เพลง", "movie", "เกม"),
    "food_recommendation": (
        "อะไรน่าทาน",
        "อะไรหน้าทาน",
        "อะไรแน่ทาน",
        "อะไรน่ากิน",
        "น่าทานไหม",
        "หน้าทานไหม",
        "แน่ทานไหม",
        "กินอะไรดี",
        "ร้านอาหาร",
        "what to eat",
        "food recommendation",
    ),
    "weather_news": ("พยากรณ์อากาศ", "ข่าววันนี้", "weather", "news", "forecast"),
    "coding_math": ("เขียนโค้ด", "สอนโค้ด", "coding", "programming", "python", "javascript", "math problem"),
    "finance_politics": ("หุ้น", "คริปโต", "การเมือง", "stock", "crypto", "finance", "politics"),
    "flirting_chitchat": ("จีบ", "เป็นแฟน", "คุยเล่น", "เหงา", "flirt", "chat with me", "are you single"),
    "bot_testing": ("ทดสอบบอท", "ลองคุย", "คุณคือใคร", "test bot", "testing the bot"),
}

IN_SCOPE_PATTERNS: tuple[str, ...] = (
    "ช่วยด้วย",
    "ขอความช่วยเหลือ",
    "แจ้งเหตุ",
    "ฉุกเฉิน",
    "น้ำท่วม",
    "ไฟไหม้",
    "ควัน",
    "อุบัติเหตุ",
    "บาดเจ็บ",
    "โรงพยาบาล",
    "หลงทาง",
    "นักท่องเที่ยว",
    "ถนนขาด",
    "ไฟดับ",
    "น้ำไม่ไหล",
    "อาหาร",
    "น้ำดื่ม",
    "ที่พัก",
    "emergency",
    "help",
    "flood",
    "fire",
    "accident",
    "injured",
    "lost",
    "tourist",
    "shelter",
)

UNCLEAR_PATTERNS: tuple[str, ...] = ("เสียงไม่ชัด", "ไม่ชัด", "ฟังไม่ออก", "unclear", "noise")


class OffTopicResult(BaseModel):
    is_off_topic: bool = False
    is_emergency_signal: bool = False
    category: str = "in_scope"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    reason: str = ""
    matched_terms: list[str] = Field(default_factory=list)
    response_text: str = ""
    call_end_recommended: bool = False
    guardrail_warnings: list[str] = Field(default_factory=list)


def classify_scope(text: str, state: IntakeSessionState | None, settings: Settings) -> OffTopicResult:
    normalized = _normalize(text)
    emergency_terms = _matched_emergency_terms(normalized)
    if emergency_terms:
        warnings = ["scope:emergency_signal"]
        if state and (state.off_topic_count or state.call_end_recommended):
            warnings.append("scope:emergency_override")
        return OffTopicResult(
            is_emergency_signal=True,
            category="emergency",
            confidence=0.95,
            reason="Emergency or crisis signal overrides scope handling.",
            matched_terms=emergency_terms,
            guardrail_warnings=warnings,
        )

    if any(pattern in normalized for pattern in IN_SCOPE_PATTERNS):
        return OffTopicResult(
            category="in_scope",
            confidence=0.8,
            reason="Caller content is within crisis intake scope.",
            matched_terms=[pattern for pattern in IN_SCOPE_PATTERNS if pattern in normalized],
        )

    off_topic_terms = _matched_off_topic_terms(normalized)
    if off_topic_terms and settings.assistant_decline_off_topic:
        next_count = (state.off_topic_count if state else 0) + 1
        call_end = settings.call_end_on_repeated_off_topic and next_count > settings.call_max_off_topic_redirects
        warning = "scope:repeated_off_topic_close_recommended" if call_end else (
            "scope:off_topic_final_warning" if next_count == settings.call_max_off_topic_redirects else "scope:off_topic_redirect"
        )
        return OffTopicResult(
            is_off_topic=True,
            category="off_topic",
            confidence=0.9,
            reason="Caller asked for content outside crisis intake scope.",
            matched_terms=off_topic_terms,
            response_text=OFF_TOPIC_FINAL_TEXT if next_count >= settings.call_max_off_topic_redirects else OFF_TOPIC_REDIRECT_TEXT,
            call_end_recommended=call_end,
            guardrail_warnings=[warning],
        )

    if _is_unclear_or_short_emergency_candidate(normalized):
        return OffTopicResult(
            category="unclear",
            confidence=0.45,
            reason="Short or unclear caller speech is not treated as off-topic.",
            matched_terms=[term for term in UNCLEAR_PATTERNS if term in normalized],
            guardrail_warnings=["scope:unclear_not_off_topic"],
        )

    return OffTopicResult(
        category="in_scope",
        confidence=0.55,
        reason="No clear off-topic request was detected.",
    )


def is_emergency_signal(text: str) -> bool:
    return bool(_matched_emergency_terms(_normalize(text)))


def is_off_topic(text: str) -> bool:
    normalized = _normalize(text)
    return bool(_matched_off_topic_terms(normalized)) and not is_emergency_signal(text)


def _matched_emergency_terms(normalized: str) -> list[str]:
    patterns: list[str] = list(IN_SCOPE_PATTERNS)
    for values in RED_PATTERNS.values():
        patterns.extend(values)
    for values in VULNERABLE_PATTERNS.values():
        patterns.extend(values)
    return _dedupe([pattern for pattern in patterns if pattern.lower() in normalized])


def _matched_off_topic_terms(normalized: str) -> list[str]:
    terms: list[str] = []
    for patterns in OFF_TOPIC_PATTERNS.values():
        terms.extend(pattern for pattern in patterns if pattern.lower() in normalized)
    return _dedupe(terms)


def _is_unclear_or_short_emergency_candidate(normalized: str) -> bool:
    if any(pattern in normalized for pattern in UNCLEAR_PATTERNS):
        return True
    return 0 < len(normalized.replace(" ", "")) <= 12


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result
