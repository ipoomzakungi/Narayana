from __future__ import annotations

import json
import re

from app.core.config import Settings
from app.models.intake import (
    CaseGroup,
    IntakeAction,
    IntakeCollectedFields,
    IntakeDecision,
    IntakeGuardrailResult,
    IntakeSessionState,
)
from app.models.triage import IncidentType, TriageLevel
from app.services.case_grouping_service import group_case, group_requires_human_review


INTAKE_JSON_SCHEMA = {
    "name": "crisis_intake_decision",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "action": {"type": "string", "enum": ["ask_followup", "create_case", "escalate_human_review"]},
            "language": {"type": "string"},
            "updated_fields": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "language": {"type": "string"},
                    "incident_type": {
                        "type": "string",
                        "enum": ["flood", "fire", "medical", "accident", "earthquake", "public_safety", "unknown"],
                    },
                    "location_text": {"type": "string"},
                    "people_affected": {"type": ["integer", "null"], "minimum": 0},
                    "injuries": {"type": "string"},
                    "immediate_needs": {"type": "array", "items": {"type": "string"}},
                    "caller_phone_optional": {"type": ["string", "null"]},
                    "landmarks": {"type": "array", "items": {"type": "string"}},
                    "urgency_signals": {"type": "array", "items": {"type": "string"}},
                    "missing_fields": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "language",
                    "incident_type",
                    "location_text",
                    "people_affected",
                    "injuries",
                    "immediate_needs",
                    "caller_phone_optional",
                    "landmarks",
                    "urgency_signals",
                    "missing_fields",
                ],
            },
            "case_group": {
                "type": "string",
                "enum": [
                    "rescue",
                    "medical",
                    "fire",
                    "flood",
                    "police_public_safety",
                    "tourist_support",
                    "utility_infrastructure",
                    "shelter_supplies",
                    "mental_health_support",
                    "unknown_human_review",
                ],
            },
            "recommended_team": {"type": "string"},
            "triage_level": {"type": "string", "enum": ["RED", "YELLOW", "GREEN"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "human_review_required": {"type": "boolean"},
            "missing_fields": {"type": "array", "items": {"type": "string"}},
            "response_text": {"type": "string"},
            "reason": {"type": "string"},
            "guardrail_warnings": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "action",
            "language",
            "updated_fields",
            "case_group",
            "recommended_team",
            "triage_level",
            "confidence",
            "human_review_required",
            "missing_fields",
            "response_text",
            "reason",
            "guardrail_warnings",
        ],
    },
}


class AzureOpenAIIntakeProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def decide(
        self,
        state: IntakeSessionState,
        latest_transcript: str,
        guardrails: IntakeGuardrailResult,
    ) -> IntakeDecision:
        if not self.settings.azure_openai_configured or self.settings.use_mock_services:
            return self._fallback_decision(state, latest_transcript, guardrails)

        try:
            from openai import AsyncAzureOpenAI

            client = AsyncAzureOpenAI(
                azure_endpoint=self.settings.azure_openai_endpoint,
                api_key=self.settings.azure_openai_api_key,
                api_version=self.settings.azure_openai_api_version,
            )
            response = await client.chat.completions.create(
                model=self.settings.azure_openai_deployment,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are Narayana, a crisis intake and triage assistant. Thai first. "
                            "Use full conversation context. Ask only one short calm Thai question when needed. "
                            "Never say rescue has been dispatched. Never diagnose. "
                            "If high risk, create or escalate immediately. "
                            "Keep response_text <= 180 Thai characters and follow-up questions <= 120 Thai characters."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "session_state": state.model_dump(mode="json"),
                                "latest_transcript": latest_transcript,
                                "guardrails": guardrails.model_dump(mode="json"),
                            },
                            ensure_ascii=False,
                        ),
                    },
                ],
                response_format={"type": "json_schema", "json_schema": INTAKE_JSON_SCHEMA},
            )
            content = response.choices[0].message.content or "{}"
            return IntakeDecision.model_validate(json.loads(content))
        except Exception as exc:
            decision = self._fallback_decision(state, latest_transcript, guardrails)
            decision.guardrail_warnings.append(f"azure_openai_intake_fallback:{exc}")
            return decision

    def _fallback_decision(
        self,
        state: IntakeSessionState,
        latest_transcript: str,
        guardrails: IntakeGuardrailResult,
    ) -> IntakeDecision:
        combined = " ".join(turn.text for turn in state.conversation_turns if turn.speaker.value == "caller")
        fields = state.collected_fields.model_copy(deep=True)
        extracted = _extract_fields(combined or latest_transcript, self.settings.assistant_language)
        fields = _merge_fields(fields, extracted)
        fields.urgency_signals = _merge_unique(fields.urgency_signals, guardrails.urgency_signals)
        missing_fields = _critical_missing_fields(fields, combined)
        fields.missing_fields = missing_fields

        group, team, group_reason = group_case(fields, combined)
        if guardrails.recommended_case_group and group == CaseGroup.UNKNOWN_HUMAN_REVIEW:
            group = guardrails.recommended_case_group
            team = group.value

        forced_red = guardrails.forced_triage_level == TriageLevel.RED
        if forced_red:
            action = IntakeAction.ESCALATE_HUMAN_REVIEW
            triage_level = TriageLevel.RED
            confidence = 0.9 if fields.location_text else 0.78
            response_text = "รับทราบค่ะ ขอให้เจ้าหน้าที่ตรวจสอบทันที กรุณาอยู่ในที่ปลอดภัยถ้าทำได้"
            reason = "High-risk safety evidence requires immediate human review."
        elif state.followup_count >= state.max_followups:
            action = IntakeAction.ESCALATE_HUMAN_REVIEW
            triage_level = TriageLevel.YELLOW
            confidence = 0.45
            response_text = "รับทราบค่ะ ข้อมูลยังไม่ครบ จะส่งให้เจ้าหน้าที่ตรวจสอบต่อค่ะ"
            reason = "Maximum follow-up count reached with missing critical fields."
        elif missing_fields:
            action = IntakeAction.ASK_FOLLOWUP
            triage_level = TriageLevel.YELLOW if fields.incident_type != IncidentType.UNKNOWN else TriageLevel.GREEN
            confidence = 0.68 if fields.location_text or fields.incident_type != IncidentType.UNKNOWN else 0.45
            response_text = _followup_question(missing_fields[0])
            reason = "Critical intake fields are still missing."
        else:
            action = IntakeAction.CREATE_CASE
            triage_level = TriageLevel.YELLOW if fields.incident_type != IncidentType.UNKNOWN else TriageLevel.GREEN
            confidence = 0.82
            response_text = "รับทราบค่ะ จะส่งข้อมูลให้เจ้าหน้าที่ตรวจสอบต่อค่ะ"
            reason = "Required crisis intake fields are sufficiently collected."

        human_review = (
            guardrails.forced_human_review
            or group_requires_human_review(group)
            or confidence < self.settings.low_confidence_threshold
            or not fields.location_text
            or triage_level == TriageLevel.RED
        )
        warnings = list(guardrails.guardrail_reasons)
        if group == CaseGroup.MENTAL_HEALTH_SUPPORT and "human_review:mental_health_support" not in warnings:
            warnings.append("human_review:mental_health_support")

        reason = f"{reason} {group_reason}".strip()
        return IntakeDecision(
            action=action,
            language=fields.language,
            updated_fields=fields,
            case_group=group,
            recommended_team=team,
            triage_level=triage_level,
            confidence=confidence,
            human_review_required=human_review,
            missing_fields=missing_fields,
            response_text=_limit(response_text, self.settings.assistant_response_max_chars),
            reason=reason,
            guardrail_warnings=warnings,
        )


def _extract_fields(text: str, language_hint: str) -> IntakeCollectedFields:
    normalized = text.lower()
    fields = IntakeCollectedFields(language=language_hint)

    if "น้ำท่วม" in text or "flood" in normalized:
        fields.incident_type = IncidentType.FLOOD
        fields.immediate_needs.append("flood_response")
    elif any(pattern in normalized for pattern in ("ไฟไหม้", "fire", "smoke", "burning")):
        fields.incident_type = IncidentType.FIRE
        fields.immediate_needs.append("fire")
    elif any(pattern in normalized for pattern in ("บาดเจ็บ", "หายใจ", "หมดสติ", "เลือด", "medical", "injured")):
        fields.incident_type = IncidentType.MEDICAL
    elif any(pattern in normalized for pattern in ("อุบัติเหตุ", "accident", "crash")):
        fields.incident_type = IncidentType.ACCIDENT
    elif any(pattern in normalized for pattern in ("ทำร้าย", "อาชญากรรม", "crime", "violence", "assault")):
        fields.incident_type = IncidentType.PUBLIC_SAFETY

    fields.location_text = _extract_location(text)
    fields.people_affected = _extract_people_affected(text)
    fields.injuries = _extract_injuries(text)
    fields.immediate_needs = _merge_unique(fields.immediate_needs, _extract_needs(text))
    fields.landmarks = _extract_landmarks(text)
    return fields


def _merge_fields(current: IntakeCollectedFields, new_fields: IntakeCollectedFields) -> IntakeCollectedFields:
    merged = current.model_copy(deep=True)
    merged.language = new_fields.language or merged.language
    if new_fields.incident_type != IncidentType.UNKNOWN:
        merged.incident_type = new_fields.incident_type
    if new_fields.location_text:
        merged.location_text = new_fields.location_text
    if new_fields.people_affected is not None:
        merged.people_affected = new_fields.people_affected
    if new_fields.injuries:
        merged.injuries = new_fields.injuries
    if new_fields.caller_phone_optional:
        merged.caller_phone_optional = new_fields.caller_phone_optional
    merged.immediate_needs = _merge_unique(merged.immediate_needs, new_fields.immediate_needs)
    merged.landmarks = _merge_unique(merged.landmarks, new_fields.landmarks)
    merged.urgency_signals = _merge_unique(merged.urgency_signals, new_fields.urgency_signals)
    return merged


def _critical_missing_fields(fields: IntakeCollectedFields, text: str) -> list[str]:
    missing: list[str] = []
    if not fields.location_text:
        missing.append("location_text")
    if not _has_any(text.lower(), ("ปลอดภัย", "safe", "ไม่มีใครบาดเจ็บ", "no injury")) and not fields.injuries:
        missing.append("injuries")
    if "ติดอยู่" not in text and "trapped" not in text.lower() and "trapped_people" not in missing and fields.people_affected is None:
        missing.append("people_affected")
    return missing


def _followup_question(missing_field: str) -> str:
    questions = {
        "location_text": "ตอนนี้อยู่จุดไหนหรือใกล้สถานที่สำคัญอะไรคะ?",
        "injuries": "มีใครบาดเจ็บ หายใจลำบาก หรือหมดสติไหมคะ?",
        "people_affected": "ตอนนี้มีคนได้รับผลกระทบกี่คนคะ?",
        "caller_phone_optional": "มีเบอร์ที่เจ้าหน้าที่ติดต่อกลับได้ไหมคะ?",
    }
    return questions.get(missing_field, "ขอข้อมูลเพิ่มเติมสั้นๆ ได้ไหมคะ?")


def _extract_location(text: str) -> str:
    known_locations = {
        "หาดใหญ่": "หาดใหญ่",
        "hat yai": "Hat Yai",
        "กรุงเทพ": "กรุงเทพ",
        "bangkok": "Bangkok",
        "เชียงใหม่": "เชียงใหม่",
        "chiang mai": "Chiang Mai",
    }
    normalized = text.lower()
    for pattern, location in known_locations.items():
        if pattern in normalized or pattern in text:
            return location

    match = re.search(r"(?:อยู่ที่|ที่|near|at)\s*([^\s,\.]+(?:\s+[^\s,\.]+)?)", text, flags=re.IGNORECASE)
    if match:
        location = match.group(1).strip()
        if location and location not in {"มี", "คน", "ไฟ", "น้ำ"}:
            return location
    return ""


def _extract_people_affected(text: str) -> int | None:
    match = re.search(r"(\d+)\s*(?:คน|people|persons)", text, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    thai_numbers = {"หนึ่งคน": 1, "สองคน": 2, "สามคน": 3, "สี่คน": 4, "ห้าคน": 5}
    for pattern, value in thai_numbers.items():
        if pattern in text:
            return value
    return None


def _extract_injuries(text: str) -> str:
    normalized = text.lower()
    injuries: list[str] = []
    if _has_any(normalized, ("หายใจลำบาก", "หายใจไม่ออก", "breathing difficulty", "cannot breathe", "can't breathe")):
        injuries.append("breathing difficulty")
    if _has_any(normalized, ("คนแก่", "ผู้สูงอายุ", "elderly")):
        injuries.append("elderly/vulnerable person")
    if _has_any(normalized, ("หมดสติ", "unconscious")):
        injuries.append("unconscious person")
    if _has_any(normalized, ("เลือดออกมาก", "severe bleeding", "heavy bleeding")):
        injuries.append("severe bleeding")
    if _has_any(normalized, ("บาดเจ็บ", "injured", "injury")):
        injuries.append("injury reported")
    if _has_any(normalized, ("ฆ่าตัวตาย", "ทำร้ายตัวเอง", "self-harm", "suicide")):
        injuries.append("self-harm danger")
    return ", ".join(_merge_unique([], injuries))


def _extract_needs(text: str) -> list[str]:
    normalized = text.lower()
    needs: list[str] = []
    if _has_any(normalized, ("ติดอยู่", "trapped", "จมน้ำ", "drowning")):
        needs.append("rescue")
    if _has_any(normalized, ("หายใจ", "หมดสติ", "เลือด", "medical", "breathing", "unconscious", "bleeding")):
        needs.append("medical")
    if _has_any(normalized, ("ไฟไหม้", "fire", "smoke")):
        needs.append("fire")
    if _has_any(normalized, ("อาหาร", "น้ำดื่ม", "ที่พัก", "food", "water", "shelter")):
        needs.append("shelter_supplies")
    return needs


def _extract_landmarks(text: str) -> list[str]:
    match = re.search(r"(?:ใกล้|near)\s*([^\s,\.]+(?:\s+[^\s,\.]+)?)", text, flags=re.IGNORECASE)
    return [match.group(1).strip()] if match else []


def _has_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(pattern.lower() in text for pattern in patterns)


def _merge_unique(current: list[str], new_values: list[str]) -> list[str]:
    result = list(current)
    for value in new_values:
        clean = value.strip()
        if clean and clean not in result:
            result.append(clean)
    return result


def _limit(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip()
