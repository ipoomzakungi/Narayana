from __future__ import annotations

import json

from app.core.config import Settings
from app.models.triage import IncidentType, TriageLevel, TriageResult


TRIAGE_JSON_SCHEMA = {
    "name": "crisis_triage_result",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "language": {"type": "string"},
            "incident_type": {
                "type": "string",
                "enum": ["flood", "fire", "medical", "accident", "earthquake", "public_safety", "unknown"],
            },
            "triage_level": {"type": "string", "enum": ["RED", "YELLOW", "GREEN"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "location_text": {"type": "string"},
            "people_affected": {"type": ["integer", "null"], "minimum": 0},
            "injuries": {"type": "string"},
            "immediate_needs": {"type": "array", "items": {"type": "string"}},
            "caller_phone_optional": {"type": ["string", "null"]},
            "ai_summary": {"type": "string"},
            "triage_reason": {"type": "string"},
            "human_review_required": {"type": "boolean"},
            "missing_fields": {"type": "array", "items": {"type": "string"}},
            "status": {"type": "string", "enum": ["pending", "contacted", "dispatched", "resolved", "closed"]},
        },
        "required": [
            "language",
            "incident_type",
            "triage_level",
            "confidence",
            "location_text",
            "people_affected",
            "injuries",
            "immediate_needs",
            "caller_phone_optional",
            "ai_summary",
            "triage_reason",
            "human_review_required",
            "missing_fields",
            "status",
        ],
    },
}


class AzureOpenAITriageProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def triage_transcript(self, transcript: str, language_hint: str = "th") -> TriageResult:
        if not self.settings.azure_openai_configured:
            return self._fallback(transcript, language_hint, "Azure OpenAI credentials are incomplete.")

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
                            "Extract crisis triage JSON only. Use Thai evidence when present. "
                            "Set status to pending. Do not dispatch, close, reject, or downgrade emergency cases."
                        ),
                    },
                    {"role": "user", "content": transcript},
                ],
                response_format={"type": "json_schema", "json_schema": TRIAGE_JSON_SCHEMA},
            )
            content = response.choices[0].message.content or "{}"
            return TriageResult.model_validate(json.loads(content))
        except Exception as exc:
            return self._fallback(transcript, language_hint, f"Azure OpenAI triage failed: {exc}")

    def _fallback(self, transcript: str, language_hint: str, reason: str) -> TriageResult:
        return TriageResult(
            language=language_hint,
            incident_type=IncidentType.UNKNOWN,
            triage_level=TriageLevel.YELLOW,
            confidence=0.35,
            location_text="",
            people_affected=None,
            injuries="unknown",
            immediate_needs=["human_review"],
            ai_summary=f"Provider fallback used for transcript: {transcript[:120]}",
            triage_reason=reason,
            human_review_required=True,
            missing_fields=["location_text", "incident_type"],
        )
