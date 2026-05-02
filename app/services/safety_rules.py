from __future__ import annotations

from copy import deepcopy

from app.models.triage import CaseStatus, SafetyRuleResult, TriageLevel, TriageResult


RED_PATTERNS: dict[str, tuple[str, ...]] = {
    "red.breathing_difficulty": ("หายใจลำบาก", "breathing difficulty", "can't breathe", "cannot breathe", "shortness of breath"),
    "red.unconscious": ("หมดสติ", "unconscious", "ไม่รู้สึกตัว"),
    "red.severe_bleeding": ("เลือดออกมาก", "severe bleeding", "heavy bleeding"),
    "red.trapped": ("ติดอยู่", "trapped", "ติดค้าง"),
    "red.drowning": ("จมน้ำ", "drowning", "น้ำพัด", "drowning risk"),
    "red.active_fire": ("ไฟไหม้", "active fire", "fire exposure", "smoke inhalation"),
    "red.chest_pain": ("เจ็บหน้าอก", "chest pain"),
    "red.stroke": ("stroke", "หน้าเบี้ยว", "แขนอ่อนแรง", "พูดไม่ชัด"),
    "red.cannot_escape": ("ออกไม่ได้", "cannot escape", "can't escape", "หนีไม่ได้"),
}

GREEN_REVIEW_PATTERNS = (
    "injury",
    "injured",
    "บาดเจ็บ",
    "trapped",
    "ติดอยู่",
    "elderly",
    "คนแก่",
    "child",
    "เด็ก",
    "medical",
    "หายใจ",
    "fire",
    "ไฟ",
    "flood",
    "น้ำท่วม",
    "drowning",
    "จมน้ำ",
)


def _combined_text(case: TriageResult) -> str:
    return " ".join(
        [
            case.incident_type.value,
            case.location_text,
            case.injuries,
            " ".join(case.immediate_needs),
            case.ai_summary,
            case.triage_reason,
        ]
    ).lower()


def evaluate_safety_rules(case: TriageResult, low_confidence_threshold: float = 0.75) -> SafetyRuleResult:
    text = _combined_text(case)
    matched: list[str] = []

    for rule_id, patterns in RED_PATTERNS.items():
        if any(pattern.lower() in text for pattern in patterns):
            matched.append(rule_id)

    if case.confidence < low_confidence_threshold:
        matched.append("review.low_confidence")

    if not case.location_text.strip():
        matched.append("review.missing_location")

    if "contradict" in text or "conflict" in text or "ขัดแย้ง" in text:
        matched.append("review.contradictory_facts")

    if case.triage_level == TriageLevel.GREEN and any(pattern in text for pattern in GREEN_REVIEW_PATTERNS):
        matched.append("review.unsafe_green")

    if case.status in {CaseStatus.DISPATCHED, CaseStatus.CLOSED, CaseStatus.RESOLVED}:
        matched.append("review.no_auto_terminal_status")

    force_red = any(rule.startswith("red.") for rule in matched)
    human_review = force_red or case.triage_level == TriageLevel.RED or bool(matched)

    if force_red:
        reason = "Forced RED because safety evidence includes: " + ", ".join(
            rule.replace("red.", "").replace("_", " ") for rule in matched if rule.startswith("red.")
        )
    elif matched:
        reason = "Human review required because: " + ", ".join(rule.replace("review.", "").replace("_", " ") for rule in matched)
    else:
        reason = "No deterministic safety escalation matched."

    return SafetyRuleResult(
        forced_triage_level=TriageLevel.RED if force_red else None,
        human_review_required=human_review,
        matched_rules=matched,
        reason=reason,
    )


def apply_safety_rules(case: TriageResult, low_confidence_threshold: float = 0.75) -> TriageResult:
    updated = deepcopy(case)
    result = evaluate_safety_rules(updated, low_confidence_threshold)

    if result.forced_triage_level:
        updated.triage_level = result.forced_triage_level

    updated.human_review_required = result.human_review_required

    if "review.missing_location" in result.matched_rules and "location_text" not in updated.missing_fields:
        updated.missing_fields.append("location_text")

    if updated.status in {CaseStatus.DISPATCHED, CaseStatus.CLOSED, CaseStatus.RESOLVED}:
        updated.status = CaseStatus.PENDING

    if result.matched_rules and result.reason not in updated.triage_reason:
        updated.triage_reason = f"{updated.triage_reason} Safety rules: {result.reason}"

    updated.touch()
    return updated
