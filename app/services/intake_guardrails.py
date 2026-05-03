from __future__ import annotations

from app.models.intake import CaseGroup, IntakeGuardrailResult, IntakeSessionState
from app.models.triage import TriageLevel


RED_PATTERNS: dict[str, tuple[str, ...]] = {
    "breathing_difficulty": (
        "หายใจลำบาก",
        "หายใจไม่ออก",
        "หอบ",
        "breathing difficulty",
        "cannot breathe",
        "can't breathe",
        "shortness of breath",
    ),
    "unconscious": ("หมดสติ", "ไม่รู้สึกตัว", "unconscious", "passed out"),
    "severe_bleeding": ("เลือดออกมาก", "เลือดไหลไม่หยุด", "severe bleeding", "heavy bleeding"),
    "trapped": ("ติดอยู่", "ติดค้าง", "ออกไม่ได้", "หนีไม่ได้", "trapped", "cannot escape", "can't escape"),
    "drowning": ("จมน้ำ", "กำลังจมน้ำ", "น้ำพัด", "drowning", "swept away"),
    "active_fire": ("ไฟไหม้", "ควันไฟ", "ติดไฟ", "ไฟลุก", "active fire", "smoke", "burning building"),
    "chest_pain": ("เจ็บหน้าอก", "chest pain"),
    "stroke_symptoms": ("หน้าเบี้ยว", "แขนอ่อนแรง", "พูดไม่ชัด", "stroke"),
    "self_harm_danger": ("ฆ่าตัวตาย", "ทำร้ายตัวเอง", "อยากตาย", "self-harm", "suicide", "kill myself"),
}

VULNERABLE_PATTERNS: dict[str, tuple[str, ...]] = {
    "elderly_vulnerable": ("คนแก่", "ผู้สูงอายุ", "elderly", "old person"),
    "child_vulnerable": ("เด็ก", "child", "baby", "infant"),
}


def evaluate_intake_guardrails(text: str, state: IntakeSessionState | None = None) -> IntakeGuardrailResult:
    combined = text
    if state:
        caller_text = [turn.text for turn in state.conversation_turns if turn.speaker.value == "caller"]
        combined = " ".join(caller_text + [text])
    normalized = combined.lower()

    reasons: list[str] = []
    urgency_signals: list[str] = []
    recommended_group: CaseGroup | None = None

    for signal, patterns in RED_PATTERNS.items():
        if any(pattern.lower() in normalized for pattern in patterns):
            urgency_signals.append(signal)
            reasons.append(f"forced_red:{signal}")

    for signal, patterns in VULNERABLE_PATTERNS.items():
        if any(pattern.lower() in normalized for pattern in patterns):
            urgency_signals.append(signal)
            reasons.append(f"human_review:{signal}")

    if "self_harm_danger" in urgency_signals:
        recommended_group = CaseGroup.MENTAL_HEALTH_SUPPORT
    elif any(signal in urgency_signals for signal in ("breathing_difficulty", "unconscious", "severe_bleeding", "chest_pain", "stroke_symptoms")):
        recommended_group = CaseGroup.MEDICAL
    elif "active_fire" in urgency_signals:
        recommended_group = CaseGroup.FIRE
    elif any(signal in urgency_signals for signal in ("trapped", "drowning")):
        recommended_group = CaseGroup.RESCUE

    force_red = any(reason.startswith("forced_red:") for reason in reasons)
    return IntakeGuardrailResult(
        forced_triage_level=TriageLevel.RED if force_red else None,
        forced_human_review=force_red or bool(reasons),
        guardrail_reasons=reasons,
        recommended_case_group=recommended_group,
        urgency_signals=urgency_signals,
    )


def response_mentions_forbidden_dispatch(text: str) -> bool:
    normalized = text.lower()
    forbidden = (
        "ส่งเจ้าหน้าที่แล้ว",
        "ส่งกู้ภัยแล้ว",
        "รถพยาบาลกำลังมา",
        "rescue has been dispatched",
        "ambulance is on the way",
        "dispatched",
    )
    return any(phrase in normalized for phrase in forbidden)
