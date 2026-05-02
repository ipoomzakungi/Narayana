from __future__ import annotations

import pytest

from app.models.triage import CaseStatus, IncidentType, TriageLevel, TriageResult
from app.services.safety_rules import apply_safety_rules, evaluate_safety_rules


def make_case(text: str, level: TriageLevel = TriageLevel.YELLOW, confidence: float = 0.9) -> TriageResult:
    return TriageResult(
        language="th",
        incident_type=IncidentType.MEDICAL,
        triage_level=level,
        confidence=confidence,
        location_text="Hat Yai",
        injuries=text,
        ai_summary=text,
        triage_reason=text,
    )


@pytest.mark.parametrize(
    ("text", "rule"),
    [
        ("elderly caller has breathing difficulty", "red.breathing_difficulty"),
        ("person is unconscious", "red.unconscious"),
        ("severe bleeding from leg", "red.severe_bleeding"),
        ("trapped on second floor", "red.trapped"),
        ("active drowning risk near canal", "red.drowning"),
        ("active fire exposure and smoke", "red.active_fire"),
        ("caller has chest pain", "red.chest_pain"),
        ("possible stroke symptoms", "red.stroke"),
        ("caller says cannot escape", "red.cannot_escape"),
    ],
)
def test_red_safety_flags_force_red(text: str, rule: str) -> None:
    result = apply_safety_rules(make_case(text, level=TriageLevel.GREEN))

    assert result.triage_level == TriageLevel.RED
    assert result.human_review_required is True
    assert rule in evaluate_safety_rules(result).matched_rules


def test_low_confidence_requires_review() -> None:
    result = apply_safety_rules(make_case("unclear situation", confidence=0.4))

    assert result.human_review_required is True
    assert "review.low_confidence" in evaluate_safety_rules(result).matched_rules


def test_missing_location_requires_review_and_missing_field() -> None:
    case = make_case("minor property issue")
    case.location_text = ""

    result = apply_safety_rules(case)

    assert result.human_review_required is True
    assert "location_text" in result.missing_fields


def test_unsafe_green_is_reviewed() -> None:
    result = apply_safety_rules(make_case("child has injury", level=TriageLevel.GREEN))

    assert result.human_review_required is True
    assert "review.unsafe_green" in evaluate_safety_rules(result).matched_rules


@pytest.mark.parametrize("status", [CaseStatus.DISPATCHED, CaseStatus.RESOLVED, CaseStatus.CLOSED])
def test_safety_rules_do_not_allow_auto_terminal_status(status: CaseStatus) -> None:
    case = make_case("needs review")
    case.status = status

    result = apply_safety_rules(case)

    assert result.status == CaseStatus.PENDING
    assert result.human_review_required is True
