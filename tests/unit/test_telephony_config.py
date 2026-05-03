from __future__ import annotations

from app.core.config import Settings
from app.core.config import reset_settings_cache
from app.main import create_app


def test_telephony_defaults_keep_local_mic_and_no_provider() -> None:
    settings = Settings()

    assert settings.voice_input_mode == "local_mic"
    assert settings.telephony_provider == "none"
    assert settings.twilio_configured is False
    assert settings.acs_configured is False


def test_twilio_configured_requires_only_public_base_url_for_webhook() -> None:
    settings = Settings(twilio_webhook_public_base_url="https://example.ngrok-free.app")

    assert settings.twilio_configured is True


def test_acs_configured_requires_all_acs_values() -> None:
    assert Settings(acs_connection_string="Endpoint=example").acs_configured is False
    assert (
        Settings(
            acs_connection_string="Endpoint=example",
            acs_phone_number="+15551234567",
            acs_callback_public_base_url="https://example.ngrok-free.app",
        ).acs_configured
        is True
    )


def test_missing_phone_provider_credentials_do_not_affect_selected_voice_provider() -> None:
    settings = Settings(use_mock_services=True, voice_input_mode="twilio_call", telephony_provider="twilio")

    assert settings.selected_provider == "mock"
    assert settings.twilio_configured is False


def test_cors_allow_origins_parse_from_env(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "http://localhost:3000,https://narayana.example")
    reset_settings_cache()

    settings = Settings.from_env()

    assert settings.cors_allow_origins == ("http://localhost:3000", "https://narayana.example")
    reset_settings_cache()


def test_cors_rejects_wildcard_with_credentials(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "*")
    reset_settings_cache()

    try:
        try:
            Settings.from_env()
        except ValueError as exc:
            assert "must not contain '*'" in str(exc)
        else:
            raise AssertionError("Expected wildcard CORS origin to be rejected")
    finally:
        reset_settings_cache()


def test_default_cors_allows_localhost() -> None:
    app = create_app()
    cors_middleware = app.user_middleware[0]

    assert "http://localhost:3000" in cors_middleware.kwargs["allow_origins"]
    assert "http://127.0.0.1:3000" in cors_middleware.kwargs["allow_origins"]
