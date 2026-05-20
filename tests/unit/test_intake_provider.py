from __future__ import annotations

import pytest

from app.core.config import Settings
from app.models.intake import ConversationSpeaker, ConversationTurn, IntakeAction, IntakeSessionState
from app.services.azure_openai_intake_provider import AzureOpenAIIntakeProvider, build_intake_system_prompt
from app.services.azure_openai_intake_provider import _extract_fields
from app.services.intake_guardrails import evaluate_intake_guardrails


@pytest.mark.asyncio
async def test_provider_fallback_asks_one_concise_thai_question_without_credentials() -> None:
    settings = Settings(use_mock_services=True, assistant_response_max_chars=180)
    provider = AzureOpenAIIntakeProvider(settings)
    state = IntakeSessionState(session_id="session_1")
    transcript = "น้ำท่วมอยู่ที่หาดใหญ่"
    state.conversation_turns.append(ConversationTurn(speaker=ConversationSpeaker.CALLER, text=transcript, turn_index=0))

    decision = await provider.decide(state, transcript, evaluate_intake_guardrails(transcript, state))

    assert decision.action == IntakeAction.ASK_FOLLOWUP
    assert decision.updated_fields.location_text == "หาดใหญ่"
    assert decision.updated_fields.incident_type == "flood"
    assert decision.response_text.endswith("คะ?")
    assert len(decision.response_text) <= 180
    assert "injuries" in decision.missing_fields


@pytest.mark.asyncio
async def test_provider_fallback_creates_red_decision_for_high_risk_sample() -> None:
    settings = Settings(use_mock_services=True)
    provider = AzureOpenAIIntakeProvider(settings)
    state = IntakeSessionState(session_id="session_1")
    transcript = "น้ำท่วมอยู่ที่หาดใหญ่ มีคนแก่หายใจลำบาก ติดอยู่ชั้นสอง"
    state.conversation_turns.append(ConversationTurn(speaker=ConversationSpeaker.CALLER, text=transcript, turn_index=0))

    decision = await provider.decide(state, transcript, evaluate_intake_guardrails(transcript, state))

    assert decision.action == IntakeAction.ESCALATE_HUMAN_REVIEW
    assert decision.triage_level == "RED"
    assert decision.case_group == "rescue"
    assert decision.human_review_required is True
    assert "ขอให้เจ้าหน้าที่ตรวจสอบทันที" in decision.response_text


def test_build_intake_system_prompt_contains_scope_and_safety_rules() -> None:
    prompt = build_intake_system_prompt(Settings(assistant_display_name="ระบบช่วยรับแจ้งเหตุ"))

    assert "ระบบช่วยรับแจ้งเหตุ" in prompt
    assert "crisis_intake_only" in prompt
    assert "Do not chit-chat" in prompt
    assert "coding" in prompt
    assert "Never say rescue has been dispatched" in prompt
    assert "Do not diagnose" in prompt
    assert "Ask only one question" in prompt
    assert "JSON only" in prompt


def test_fallback_location_extractor_does_not_treat_thai_particle_as_location() -> None:
    fields = _extract_fields("สวัสดี สวัสดีที่รัก", "th")

    assert fields.location_text == ""


@pytest.mark.asyncio
async def test_food_recommendation_is_off_topic_not_case_data() -> None:
    settings = Settings(use_mock_services=True)
    provider = AzureOpenAIIntakeProvider(settings)
    state = IntakeSessionState(session_id="session_food")
    transcript = "มีอะไรน่าทานบ้างครับ"

    decision = await provider.decide(state, transcript, evaluate_intake_guardrails(transcript, state))

    assert decision.updated_fields.location_text == ""
    assert decision.updated_fields.incident_type == "unknown"
