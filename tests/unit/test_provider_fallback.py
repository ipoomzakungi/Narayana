from __future__ import annotations

from app.core.config import Settings
from app.models.triage import ProviderMode
from app.services.azure_speech_provider import AzureSpeechOpenAIProvider
from app.services.azure_voice_live_provider import AzureVoiceLiveProvider
from app.services.mock_voice_provider import MockVoiceProvider
from app.services.voice_agent_provider import get_voice_provider


def test_use_mock_services_selects_mock_provider() -> None:
    provider = get_voice_provider(Settings(use_mock_services=True))

    assert isinstance(provider, MockVoiceProvider)


def test_missing_azure_credentials_falls_back_to_mock() -> None:
    provider = get_voice_provider(Settings(use_mock_services=False))

    assert isinstance(provider, MockVoiceProvider)


def test_complete_speech_openai_credentials_select_azure_when_mock_disabled() -> None:
    provider = get_voice_provider(
        Settings(
            use_mock_services=False,
            azure_speech_key="speech-key",
            azure_speech_region="southeastasia",
            azure_openai_endpoint="https://example.openai.azure.com",
            azure_openai_api_key="openai-key",
            azure_openai_deployment="gpt-4o-mini",
            azure_openai_api_version="2024-08-01-preview",
        )
    )

    assert isinstance(provider, AzureSpeechOpenAIProvider)


def test_voice_live_is_explicit_and_optional() -> None:
    provider = get_voice_provider(
        Settings(
            use_mock_services=False,
            azure_voice_live_endpoint="wss://example.azure.com/voice-live",
            azure_voice_live_model="voice-live",
        ),
        requested_mode=ProviderMode.AZURE_VOICE_LIVE,
    )

    assert isinstance(provider, AzureVoiceLiveProvider)


def test_health_helpers_do_not_expose_secret_values() -> None:
    settings = Settings(azure_speech_key="secret", azure_speech_region="southeastasia")

    assert settings.azure_speech_configured is True
    assert "secret" not in settings.missing_azure_variables()
    assert "AZURE_OPENAI_API_KEY" in settings.missing_azure_variables()
