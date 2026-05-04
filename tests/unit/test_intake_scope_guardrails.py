from __future__ import annotations

import pytest

from app.core.config import Settings
from app.models.intake import IntakeSessionState
from app.services.intake_scope_guardrails import classify_scope, is_emergency_signal, is_off_topic


@pytest.mark.parametrize(
    "text",
    [
        "เล่าเรื่องตลกให้ฟังหน่อย",
        "พยากรณ์อากาศวันนี้เป็นอย่างไร",
        "ช่วยเขียนโค้ด Python ให้หน่อย",
        "หุ้นตัวไหนดี",
        "คุยเล่นกับฉันหน่อย",
    ],
)
def test_off_topic_examples_are_classified(text: str) -> None:
    result = classify_scope(text, IntakeSessionState(session_id="s1"), Settings())

    assert result.is_off_topic is True
    assert result.category == "off_topic"
    assert result.response_text.startswith("ขออภัยค่ะ ระบบนี้ใช้สำหรับรับแจ้งเหตุ")
    assert result.call_end_recommended is False
    assert is_off_topic(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "ช่วยด้วย",
        "น้ำท่วม มีคนแก่หายใจลำบาก",
        "ติดอยู่ชั้นสอง",
        "ไฟไหม้มีควันเยอะ",
        "คนหมดสติ",
        "เลือดออกมาก",
        "อยากทำร้ายตัวเอง",
        "เด็กติดอยู่ในรถ",
    ],
)
def test_emergency_examples_override_off_topic(text: str) -> None:
    state = IntakeSessionState(
        session_id="s1",
        off_topic_count=2,
        call_end_recommended=True,
        call_end_reason="repeated_off_topic",
    )

    result = classify_scope(text, state, Settings())

    assert result.is_emergency_signal is True
    assert result.is_off_topic is False
    assert "scope:emergency_override" in result.guardrail_warnings
    assert is_emergency_signal(text) is True


@pytest.mark.parametrize("text", ["เสียงไม่ชัด", "ช่วย", "อยู่ไหน"])
def test_unclear_or_short_phrases_are_not_off_topic(text: str) -> None:
    result = classify_scope(text, IntakeSessionState(session_id="s1"), Settings())

    assert result.is_off_topic is False


def test_repeated_off_topic_sets_close_recommendation() -> None:
    state = IntakeSessionState(session_id="s1", off_topic_count=2)

    result = classify_scope("เล่าเรื่องตลกอีกเรื่อง", state, Settings(call_max_off_topic_redirects=2))

    assert result.is_off_topic is True
    assert result.call_end_recommended is True
    assert "scope:repeated_off_topic_close_recommended" in result.guardrail_warnings
