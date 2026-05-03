from __future__ import annotations

from app.models.intake import CaseGroup, IntakeCollectedFields


GROUP_TEAMS: dict[CaseGroup, str] = {
    CaseGroup.RESCUE: "rescue",
    CaseGroup.MEDICAL: "medical",
    CaseGroup.FIRE: "fire",
    CaseGroup.FLOOD: "flood_response",
    CaseGroup.POLICE_PUBLIC_SAFETY: "police_public_safety",
    CaseGroup.TOURIST_SUPPORT: "tourist_support",
    CaseGroup.UTILITY_INFRASTRUCTURE: "utility_infrastructure",
    CaseGroup.SHELTER_SUPPLIES: "shelter_supplies",
    CaseGroup.MENTAL_HEALTH_SUPPORT: "mental_health_support",
    CaseGroup.UNKNOWN_HUMAN_REVIEW: "human_review",
}


def group_case(fields: IntakeCollectedFields, text: str = "") -> tuple[CaseGroup, str, str]:
    combined = " ".join(
        [
            text,
            fields.incident_type.value,
            fields.location_text,
            fields.injuries,
            " ".join(fields.immediate_needs),
            " ".join(fields.landmarks),
            " ".join(fields.urgency_signals),
        ]
    ).lower()

    if _has_any(combined, ("ฆ่าตัวตาย", "ทำร้ายตัวเอง", "อยากตาย", "self-harm", "suicide", "panic", "severe distress")):
        return _result(CaseGroup.MENTAL_HEALTH_SUPPORT, "Self-harm or severe distress requires mental-health support and human review.")

    if _has_any(combined, ("ไฟไหม้", "ควัน", "ไฟลุก", "burning", "fire", "smoke")):
        return _result(CaseGroup.FIRE, "Active fire or smoke evidence maps to fire response.")

    if _has_any(combined, ("อาชญากรรม", "ทำร้าย", "ทะเลาะ", "ปืน", "มีด", "crime", "violence", "assault", "public danger")):
        return _result(CaseGroup.POLICE_PUBLIC_SAFETY, "Crime, violence, or public danger maps to police/public safety.")

    if _has_any(combined, ("นักท่องเที่ยว", "tourist", "passport", "lost foreigner", "foreigner")):
        return _result(CaseGroup.TOURIST_SUPPORT, "Tourist or foreign visitor support is needed.")

    if _has_any(combined, ("ไฟฟ้า", "น้ำประปา", "ถนน", "สะพาน", "power", "water supply", "road", "bridge", "utility")):
        return _result(CaseGroup.UTILITY_INFRASTRUCTURE, "Utility, road, or infrastructure issue maps to infrastructure support.")

    if _has_any(combined, ("อาหาร", "น้ำดื่ม", "ที่พัก", "ศูนย์พักพิง", "food", "water", "shelter", "supplies")):
        return _result(CaseGroup.SHELTER_SUPPLIES, "Food, water, shelter, or supplies need maps to shelter/supplies support.")

    medical = _has_any(
        combined,
        (
            "หายใจลำบาก",
            "หมดสติ",
            "เลือดออก",
            "เจ็บหน้าอก",
            "บาดเจ็บ",
            "breathing difficulty",
            "unconscious",
            "bleeding",
            "chest pain",
            "injured",
            "medical",
        ),
    )
    flood = _has_any(combined, ("น้ำท่วม", "flood"))
    trapped = _has_any(combined, ("ติดอยู่", "ติดค้าง", "trapped", "cannot escape", "drowning", "จมน้ำ"))

    if flood and trapped:
        return _result(CaseGroup.RESCUE, "Flood with trapped or drowning risk maps to rescue response.")
    if medical:
        return _result(CaseGroup.MEDICAL, "Medical symptom or injury evidence maps to medical response.")
    if flood:
        return _result(CaseGroup.FLOOD, "Flood evidence without trapped people maps to flood response.")
    if trapped:
        return _result(CaseGroup.RESCUE, "Trapped person evidence maps to rescue response.")

    return _result(CaseGroup.UNKNOWN_HUMAN_REVIEW, "Insufficient evidence for a specific operational group.")


def recommended_team_for_group(group: CaseGroup) -> str:
    return GROUP_TEAMS[group]


def group_requires_human_review(group: CaseGroup) -> bool:
    return group in {CaseGroup.UNKNOWN_HUMAN_REVIEW, CaseGroup.MENTAL_HEALTH_SUPPORT}


def _result(group: CaseGroup, reason: str) -> tuple[CaseGroup, str, str]:
    return group, GROUP_TEAMS[group], reason


def _has_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(pattern.lower() in text for pattern in patterns)
