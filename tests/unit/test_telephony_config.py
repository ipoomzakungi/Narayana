from __future__ import annotations

from app.core.config import Settings
from app.core.config import reset_settings_cache
from app.main import create_app


def test_telephony_defaults_keep_local_mic_and_no_provider() -> None:
    settings = Settings()

    assert settings.voice_input_mode == "local_mic"
    assert settings.telephony_provider == "none"
    assert settings.enable_multi_turn_intake is False
    assert settings.assistant_language == "th"
    assert settings.assistant_max_followups == 3
    assert settings.assistant_name == "Narayana"
    assert settings.assistant_display_name == "ระบบช่วยรับแจ้งเหตุ"
    assert settings.assistant_system_prompt_version == "v1"
    assert settings.assistant_scope == "crisis_intake_only"
    assert "emergency" in settings.assistant_allowed_topics
    assert settings.assistant_decline_off_topic is True
    assert settings.turn_silence_threshold_ms == 750
    assert settings.turn_pre_speech_padding_ms == 200
    assert settings.vad_energy_threshold == 0.02
    assert settings.min_speech_ms == 300
    assert settings.call_audit_enabled is True
    assert settings.call_audit_log_transcripts is True
    assert settings.call_audit_max_sessions == 50
    assert settings.call_no_reply_seconds == 15
    assert settings.call_no_reply_prompt_seconds == 15
    assert settings.call_max_no_reply_prompts == 2
    assert settings.call_max_off_topic_redirects == 2
    assert settings.call_end_on_repeated_off_topic is True
    assert settings.call_end_on_no_reply is True
    assert settings.twilio_force_hangup_enabled is False
    assert settings.enable_twilio_tts_response is False
    assert settings.enable_twilio_initial_greeting is False
    assert settings.twilio_initial_greeting_text == (
        "สวัสดีค่ะ นี่คือระบบช่วยรับแจ้งเหตุ กรุณาเล่าสถานการณ์และสถานที่สั้น ๆ ได้เลยค่ะ"
    )
    assert settings.twilio_initial_greeting_profile == "greeting"
    assert settings.twilio_initial_greeting_fallback_say is False
    assert settings.azure_speech_voice == "th-TH-PremwadeeNeural"
    assert settings.tts_max_chars == 220
    assert settings.tts_output_format == "mulaw_8khz"
    assert settings.tts_use_ssml is True
    assert settings.tts_rate_normal == "0%"
    assert settings.tts_rate_followup == "-5%"
    assert settings.tts_rate_greeting == "-5%"
    assert settings.tts_rate_red == "-12%"
    assert settings.tts_rate_unclear == "-8%"
    assert settings.tts_rate_closing == "-8%"
    assert settings.tts_pitch_normal == "0%"
    assert settings.tts_pitch_greeting == "0%"
    assert settings.tts_pitch_red == "-2%"
    assert settings.tts_pitch_closing == "0%"
    assert settings.tts_volume == "medium"
    assert settings.twilio_configured is False
    assert settings.acs_configured is False
    assert settings.azure_speech_tts_configured is False
    assert settings.enable_realtime_voice is False
    assert settings.realtime_provider == "none"
    assert settings.normalized_realtime_provider == "none"
    assert settings.normalized_realtime_input_audio_format == "pcm16"
    assert settings.effective_realtime_input_audio_format == "pcm16"
    assert settings.realtime_twilio_audio_passthrough is False
    assert settings.realtime_input_audio_passthrough_enabled is False
    assert settings.realtime_output_voice == "marin"
    assert settings.normalized_realtime_output_voice == "marin"
    assert settings.realtime_configured is False
    assert settings.azure_openai_realtime_configured is False
    assert settings.azure_voice_live_realtime_configured is False
    assert settings.missing_realtime_variables() == []
    assert settings.realtime_warnings() == []


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


def test_tts_settings_parse_from_env_without_requiring_azure(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_TWILIO_TTS_RESPONSE", "true")
    monkeypatch.setenv("ENABLE_TWILIO_INITIAL_GREETING", "true")
    monkeypatch.setenv("TWILIO_INITIAL_GREETING_TEXT", "สวัสดีค่ะ แจ้งเหตุได้เลยค่ะ")
    monkeypatch.setenv("TWILIO_INITIAL_GREETING_PROFILE", "greeting")
    monkeypatch.setenv("TWILIO_INITIAL_GREETING_FALLBACK_SAY", "true")
    monkeypatch.setenv("AZURE_SPEECH_VOICE", "th-TH-TestVoice")
    monkeypatch.setenv("TTS_MAX_CHARS", "120")
    monkeypatch.setenv("TTS_OUTPUT_FORMAT", "mulaw_8khz")
    monkeypatch.setenv("TTS_USE_SSML", "false")
    monkeypatch.setenv("TTS_RATE_FOLLOWUP", "-9%")
    monkeypatch.setenv("TTS_RATE_GREETING", "-6%")
    monkeypatch.setenv("TTS_RATE_RED", "-15%")
    monkeypatch.setenv("TTS_RATE_CLOSING", "-10%")
    monkeypatch.setenv("TTS_PITCH_GREETING", "-1%")
    monkeypatch.setenv("TTS_PITCH_CLOSING", "-2%")
    monkeypatch.setenv("TTS_VOLUME", "soft")
    monkeypatch.setenv("ASSISTANT_DISPLAY_NAME", "ศูนย์รับแจ้งเหตุ")
    monkeypatch.setenv("ASSISTANT_SYSTEM_PROMPT_VERSION", "v2")
    monkeypatch.setenv("ASSISTANT_ALLOWED_TOPICS", "emergency,fire")
    monkeypatch.setenv("ASSISTANT_DECLINE_OFF_TOPIC", "false")
    monkeypatch.setenv("CALL_NO_REPLY_SECONDS", "4")
    monkeypatch.setenv("CALL_NO_REPLY_PROMPT_SECONDS", "8")
    monkeypatch.setenv("CALL_MAX_NO_REPLY_PROMPTS", "1")
    monkeypatch.setenv("CALL_MAX_OFF_TOPIC_REDIRECTS", "1")
    monkeypatch.setenv("CALL_END_ON_REPEATED_OFF_TOPIC", "false")
    monkeypatch.setenv("CALL_END_ON_NO_REPLY", "false")
    monkeypatch.setenv("TURN_SILENCE_THRESHOLD_MS", "500")
    monkeypatch.setenv("TURN_PRE_SPEECH_PADDING_MS", "180")
    monkeypatch.setenv("VAD_ENERGY_THRESHOLD", "0.015")
    monkeypatch.setenv("MIN_SPEECH_MS", "320")
    monkeypatch.setenv("CALL_AUDIT_ENABLED", "false")
    monkeypatch.setenv("CALL_AUDIT_LOG_TRANSCRIPTS", "false")
    monkeypatch.setenv("CALL_AUDIT_MAX_SESSIONS", "12")
    monkeypatch.setenv("TWILIO_FORCE_HANGUP_ENABLED", "true")
    monkeypatch.setenv("ENABLE_REALTIME_VOICE", "true")
    monkeypatch.setenv("REALTIME_PROVIDER", "azure_openai_realtime")
    monkeypatch.setenv("AZURE_REALTIME_ENDPOINT", "https://aoai.example.openai.azure.com")
    monkeypatch.setenv("AZURE_REALTIME_API_KEY", "realtime-key")
    monkeypatch.setenv("AZURE_REALTIME_DEPLOYMENT", "gpt-realtime")
    monkeypatch.setenv("AZURE_REALTIME_API_VERSION", "2025-04-01-preview")
    monkeypatch.setenv("REALTIME_INPUT_AUDIO_FORMAT", "g711_ulaw")
    monkeypatch.setenv("REALTIME_TWILIO_AUDIO_PASSTHROUGH", "true")
    monkeypatch.setenv("REALTIME_OUTPUT_VOICE", "coral")
    reset_settings_cache()

    settings = Settings.from_env()

    assert settings.enable_twilio_tts_response is True
    assert settings.enable_twilio_initial_greeting is True
    assert settings.twilio_initial_greeting_text == "สวัสดีค่ะ แจ้งเหตุได้เลยค่ะ"
    assert settings.twilio_initial_greeting_profile == "greeting"
    assert settings.twilio_initial_greeting_fallback_say is True
    assert settings.azure_speech_voice == "th-TH-TestVoice"
    assert settings.tts_max_chars == 120
    assert settings.tts_output_format == "mulaw_8khz"
    assert settings.tts_use_ssml is False
    assert settings.tts_rate_followup == "-9%"
    assert settings.tts_rate_greeting == "-6%"
    assert settings.tts_rate_red == "-15%"
    assert settings.tts_rate_closing == "-10%"
    assert settings.tts_pitch_greeting == "-1%"
    assert settings.tts_pitch_closing == "-2%"
    assert settings.tts_volume == "soft"
    assert settings.assistant_display_name == "ศูนย์รับแจ้งเหตุ"
    assert settings.assistant_system_prompt_version == "v2"
    assert settings.assistant_allowed_topics == ("emergency", "fire")
    assert settings.assistant_decline_off_topic is False
    assert settings.call_no_reply_seconds == 4
    assert settings.call_no_reply_prompt_seconds == 8
    assert settings.call_max_no_reply_prompts == 1
    assert settings.call_max_off_topic_redirects == 1
    assert settings.call_end_on_repeated_off_topic is False
    assert settings.call_end_on_no_reply is False
    assert settings.turn_silence_threshold_ms == 500
    assert settings.turn_pre_speech_padding_ms == 180
    assert settings.vad_energy_threshold == 0.015
    assert settings.min_speech_ms == 320
    assert settings.call_audit_enabled is False
    assert settings.call_audit_log_transcripts is False
    assert settings.call_audit_max_sessions == 12
    assert settings.twilio_force_hangup_enabled is True
    assert settings.twilio_debug_payloads_enabled is False
    assert settings.enable_realtime_voice is True
    assert settings.normalized_realtime_provider == "azure_openai_realtime"
    assert settings.azure_openai_realtime_configured is True
    assert settings.realtime_configured is True
    assert settings.normalized_realtime_input_audio_format == "g711_ulaw"
    assert settings.effective_realtime_input_audio_format == "g711_ulaw"
    assert settings.realtime_input_audio_passthrough_enabled is True
    assert settings.normalized_realtime_output_voice == "coral"
    assert settings.azure_speech_tts_configured is False
    assert settings.missing_azure_speech_tts_variables() == ["AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION"]
    reset_settings_cache()


def test_invalid_realtime_output_voice_warns_and_falls_back() -> None:
    settings = Settings(realtime_output_voice="unsupported")

    assert settings.normalized_realtime_output_voice == "marin"
    assert "REALTIME_OUTPUT_VOICE is invalid" in " ".join(settings.realtime_warnings())


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
