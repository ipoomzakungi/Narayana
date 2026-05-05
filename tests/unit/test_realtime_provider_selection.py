from __future__ import annotations

from app.core.config import Settings
from app.models.realtime import RealtimeProviderMode
from app.services.realtime_voice_provider import get_realtime_provider


def test_realtime_provider_disabled_by_default() -> None:
    selection = get_realtime_provider(Settings())

    assert selection.enabled is False
    assert selection.provider_mode == RealtimeProviderMode.NONE
    assert selection.provider is None
    assert selection.fallback_reason == "disabled"
    assert selection.debug_payload()["provider"] == "none"


def test_realtime_provider_missing_config_falls_back() -> None:
    selection = get_realtime_provider(
        Settings(enable_realtime_voice=True, realtime_provider="azure_openai_realtime")
    )

    assert selection.enabled is True
    assert selection.provider_mode == RealtimeProviderMode.AZURE_OPENAI_REALTIME
    assert selection.provider is None
    assert selection.configured is False
    assert selection.fallback_reason == "not_configured"
    assert "AZURE_REALTIME_ENDPOINT" in selection.warnings[0]


def test_openai_realtime_provider_selected_when_configured() -> None:
    selection = get_realtime_provider(
        Settings(
            enable_realtime_voice=True,
            realtime_provider="azure_openai_realtime",
            azure_realtime_endpoint="https://aoai.example.openai.azure.com",
            azure_realtime_api_key="key",
            azure_realtime_deployment="gpt-realtime",
            azure_realtime_api_version="2025-04-01-preview",
        )
    )

    assert selection.active_candidate is True
    assert selection.provider is not None
    assert selection.provider.mode == RealtimeProviderMode.AZURE_OPENAI_REALTIME


def test_voice_live_realtime_provider_selected_when_configured() -> None:
    selection = get_realtime_provider(
        Settings(
            enable_realtime_voice=True,
            realtime_provider="azure_voice_live",
            azure_realtime_api_key="key",
            azure_voice_live_endpoint="wss://voice.example/voice-live/realtime?api-version=2025-10-01",
            azure_voice_live_model="gpt-realtime",
        )
    )

    assert selection.active_candidate is True
    assert selection.provider is not None
    assert selection.provider.mode == RealtimeProviderMode.AZURE_VOICE_LIVE
