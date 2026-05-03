from __future__ import annotations

from app.models.intake import CaseGroup
from app.models.triage import TriageLevel
from app.services.intake_guardrails import evaluate_intake_guardrails, response_mentions_forbidden_dispatch


def test_guardrails_detect_thai_flood_trapped_breathing_red() -> None:
    result = evaluate_intake_guardrails("น้ำท่วมอยู่ที่หาดใหญ่ มีคนแก่หายใจลำบาก ติดอยู่ชั้นสอง")

    assert result.forced_triage_level == TriageLevel.RED
    assert result.forced_human_review is True
    assert "breathing_difficulty" in result.urgency_signals
    assert "trapped" in result.urgency_signals
    assert result.recommended_case_group in {CaseGroup.MEDICAL, CaseGroup.RESCUE}


def test_guardrails_detect_fire_bleeding_unconscious_drowning_and_self_harm() -> None:
    samples = [
        "ไฟไหม้อาคาร มีควันเยอะ",
        "คนเจ็บเลือดออกมาก",
        "ผู้ป่วยหมดสติ",
        "เด็กกำลังจมน้ำ",
        "ผู้โทรบอกว่าอยากฆ่าตัวตาย",
    ]

    for sample in samples:
        result = evaluate_intake_guardrails(sample)
        assert result.forced_triage_level == TriageLevel.RED
        assert result.forced_human_review is True


def test_guardrails_do_not_force_red_for_safe_information_request() -> None:
    result = evaluate_intake_guardrails("ต้องการข้อมูลศูนย์พักพิง")

    assert result.forced_triage_level is None


def test_response_dispatch_claim_detection() -> None:
    assert response_mentions_forbidden_dispatch("ส่งเจ้าหน้าที่แล้วค่ะ") is True
    assert response_mentions_forbidden_dispatch("รับทราบค่ะ จะส่งข้อมูลให้เจ้าหน้าที่ตรวจสอบ") is False
