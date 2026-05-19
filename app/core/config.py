from __future__ import annotations

from dataclasses import dataclass
import os
from functools import lru_cache

DEFAULT_CORS_ALLOW_ORIGINS = ("http://localhost:3000", "http://127.0.0.1:3000")
DEFAULT_ASSISTANT_DISPLAY_NAME = "ระบบช่วยรับแจ้งเหตุ"
DEFAULT_TWILIO_INITIAL_GREETING = (
    "สวัสดีค่ะ นี่คือระบบช่วยรับแจ้งเหตุ กรุณาเล่าสถานการณ์และสถานที่สั้น ๆ ได้เลยค่ะ"
)
DEFAULT_ASSISTANT_ALLOWED_TOPICS = (
    "emergency",
    "medical",
    "flood",
    "fire",
    "accident",
    "public_safety",
    "tourist_support",
    "mental_health_crisis",
    "utility_infrastructure",
    "shelter_supplies",
)
SUPPORTED_REALTIME_OUTPUT_VOICES = (
    "alloy",
    "ash",
    "ballad",
    "cedar",
    "coral",
    "echo",
    "marin",
    "sage",
    "shimmer",
    "verse",
)


def _truthy(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _csv(value: str | None, default: tuple[str, ...] = ()) -> tuple[str, ...]:
    if value is None or not value.strip():
        return default
    values = tuple(item.strip().rstrip("/") for item in value.split(",") if item.strip())
    if "*" in values:
        raise ValueError("CORS_ALLOW_ORIGINS must not contain '*' while credentials are enabled.")
    return values or default


@dataclass(frozen=True)
class Settings:
    azure_speech_key: str = ""
    azure_speech_region: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = ""
    azure_openai_api_version: str = ""
    enable_realtime_voice: bool = False
    realtime_provider: str = "none"
    azure_realtime_endpoint: str = ""
    azure_realtime_api_key: str = ""
    azure_realtime_deployment: str = ""
    azure_realtime_api_version: str = ""
    realtime_input_audio_format: str = "pcm16"
    realtime_twilio_audio_passthrough: bool = False
    realtime_input_transcription_enabled: bool = False
    realtime_output_voice: str = "marin"
    realtime_vad_threshold: float = 0.55
    realtime_vad_prefix_padding_ms: int = 200
    realtime_vad_silence_duration_ms: int = 300
    debug_realtime_deltas: bool = False
    azure_voice_live_endpoint: str = ""
    azure_voice_live_model: str = ""
    cosmos_db_endpoint: str = ""
    cosmos_db_key: str = ""
    cosmos_db_database: str = ""
    cosmos_db_container: str = ""
    use_mock_services: bool = True
    case_store_path: str = ".data/cases.json"
    audio_store_path: str = ".data/audio"
    low_confidence_threshold: float = 0.75
    voice_input_mode: str = "local_mic"
    telephony_provider: str = "none"
    phone_test_country: str = ""
    phone_test_number: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    twilio_webhook_public_base_url: str = ""
    cors_allow_origins: tuple[str, ...] = DEFAULT_CORS_ALLOW_ORIGINS
    acs_connection_string: str = ""
    acs_phone_number: str = ""
    acs_callback_public_base_url: str = ""
    enable_multi_turn_intake: bool = False
    assistant_language: str = "th"
    assistant_tone: str = "calm_concise"
    assistant_max_followups: int = 3
    assistant_question_style: str = "single_short_question"
    assistant_name: str = "Narayana"
    assistant_display_name: str = DEFAULT_ASSISTANT_DISPLAY_NAME
    assistant_system_prompt_version: str = "v1"
    assistant_scope: str = "crisis_intake_only"
    assistant_allowed_topics: tuple[str, ...] = DEFAULT_ASSISTANT_ALLOWED_TOPICS
    assistant_decline_off_topic: bool = True
    assistant_response_max_chars: int = 180
    turn_silence_threshold_ms: int = 750
    turn_pre_speech_padding_ms: int = 200
    vad_energy_threshold: float = 0.02
    min_speech_ms: int = 300
    call_audit_enabled: bool = True
    call_audit_log_transcripts: bool = True
    call_audit_max_sessions: int = 50
    call_no_reply_seconds: float = 15.0
    call_no_reply_prompt_seconds: float = 15.0
    call_max_no_reply_prompts: int = 2
    call_max_off_topic_redirects: int = 2
    call_end_on_repeated_off_topic: bool = True
    call_end_on_no_reply: bool = True
    twilio_force_hangup_enabled: bool = False
    twilio_debug_payloads_enabled: bool = True
    enable_twilio_tts_response: bool = False
    enable_twilio_initial_greeting: bool = False
    twilio_initial_greeting_text: str = DEFAULT_TWILIO_INITIAL_GREETING
    twilio_initial_greeting_profile: str = "greeting"
    twilio_initial_greeting_fallback_say: bool = False
    azure_speech_voice: str = "th-TH-PremwadeeNeural"
    tts_max_chars: int = 220
    tts_output_format: str = "mulaw_8khz"
    tts_use_ssml: bool = True
    tts_rate_normal: str = "0%"
    tts_rate_followup: str = "-5%"
    tts_rate_greeting: str = "-5%"
    tts_rate_red: str = "-12%"
    tts_rate_unclear: str = "-8%"
    tts_rate_closing: str = "-8%"
    tts_pitch_normal: str = "0%"
    tts_pitch_greeting: str = "0%"
    tts_pitch_red: str = "-2%"
    tts_pitch_closing: str = "0%"
    tts_volume: str = "medium"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            azure_speech_key=os.getenv("AZURE_SPEECH_KEY", ""),
            azure_speech_region=os.getenv("AZURE_SPEECH_REGION", ""),
            azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
            azure_openai_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", ""),
            azure_openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", ""),
            enable_realtime_voice=_truthy(os.getenv("ENABLE_REALTIME_VOICE"), default=False),
            realtime_provider=os.getenv("REALTIME_PROVIDER", "none"),
            azure_realtime_endpoint=os.getenv("AZURE_REALTIME_ENDPOINT", ""),
            azure_realtime_api_key=os.getenv("AZURE_REALTIME_API_KEY", ""),
            azure_realtime_deployment=os.getenv("AZURE_REALTIME_DEPLOYMENT", ""),
            azure_realtime_api_version=os.getenv("AZURE_REALTIME_API_VERSION", ""),
            realtime_input_audio_format=os.getenv("REALTIME_INPUT_AUDIO_FORMAT", "pcm16"),
            realtime_twilio_audio_passthrough=_truthy(
                os.getenv("REALTIME_TWILIO_AUDIO_PASSTHROUGH"),
                default=False,
            ),
            realtime_input_transcription_enabled=_truthy(
                os.getenv("REALTIME_INPUT_TRANSCRIPTION_ENABLED"),
                default=False,
            ),
            realtime_output_voice=os.getenv("REALTIME_OUTPUT_VOICE", "marin"),
            realtime_vad_threshold=float(os.getenv("REALTIME_VAD_THRESHOLD", "0.55")),
            realtime_vad_prefix_padding_ms=int(os.getenv("REALTIME_VAD_PREFIX_PADDING_MS", "200")),
            realtime_vad_silence_duration_ms=int(os.getenv("REALTIME_VAD_SILENCE_DURATION_MS", "300")),
            debug_realtime_deltas=_truthy(os.getenv("DEBUG_REALTIME_DELTAS"), default=False),
            azure_voice_live_endpoint=os.getenv("AZURE_VOICE_LIVE_ENDPOINT", ""),
            azure_voice_live_model=os.getenv("AZURE_VOICE_LIVE_MODEL", ""),
            cosmos_db_endpoint=os.getenv("COSMOS_DB_ENDPOINT", ""),
            cosmos_db_key=os.getenv("COSMOS_DB_KEY", ""),
            cosmos_db_database=os.getenv("COSMOS_DB_DATABASE", ""),
            cosmos_db_container=os.getenv("COSMOS_DB_CONTAINER", ""),
            use_mock_services=_truthy(os.getenv("USE_MOCK_SERVICES"), default=True),
            case_store_path=os.getenv("CASE_STORE_PATH", ".data/cases.json"),
            audio_store_path=os.getenv("AUDIO_STORE_PATH", ".data/audio"),
            low_confidence_threshold=float(os.getenv("LOW_CONFIDENCE_THRESHOLD", "0.75")),
            voice_input_mode=os.getenv("VOICE_INPUT_MODE", "local_mic"),
            telephony_provider=os.getenv("TELEPHONY_PROVIDER", "none"),
            phone_test_country=os.getenv("PHONE_TEST_COUNTRY", ""),
            phone_test_number=os.getenv("PHONE_TEST_NUMBER", ""),
            twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
            twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
            twilio_phone_number=os.getenv("TWILIO_PHONE_NUMBER", ""),
            twilio_webhook_public_base_url=os.getenv("TWILIO_WEBHOOK_PUBLIC_BASE_URL", ""),
            cors_allow_origins=_csv(os.getenv("CORS_ALLOW_ORIGINS"), DEFAULT_CORS_ALLOW_ORIGINS),
            acs_connection_string=os.getenv("ACS_CONNECTION_STRING", ""),
            acs_phone_number=os.getenv("ACS_PHONE_NUMBER", ""),
            acs_callback_public_base_url=os.getenv("ACS_CALLBACK_PUBLIC_BASE_URL", ""),
            enable_multi_turn_intake=_truthy(os.getenv("ENABLE_MULTI_TURN_INTAKE"), default=False),
            assistant_language=os.getenv("ASSISTANT_LANGUAGE", "th"),
            assistant_tone=os.getenv("ASSISTANT_TONE", "calm_concise"),
            assistant_max_followups=int(os.getenv("ASSISTANT_MAX_FOLLOWUPS", "3")),
            assistant_question_style=os.getenv("ASSISTANT_QUESTION_STYLE", "single_short_question"),
            assistant_name=os.getenv("ASSISTANT_NAME", "Narayana"),
            assistant_display_name=os.getenv("ASSISTANT_DISPLAY_NAME", DEFAULT_ASSISTANT_DISPLAY_NAME),
            assistant_system_prompt_version=os.getenv("ASSISTANT_SYSTEM_PROMPT_VERSION", "v1"),
            assistant_scope=os.getenv("ASSISTANT_SCOPE", "crisis_intake_only"),
            assistant_allowed_topics=_csv(os.getenv("ASSISTANT_ALLOWED_TOPICS"), DEFAULT_ASSISTANT_ALLOWED_TOPICS),
            assistant_decline_off_topic=_truthy(os.getenv("ASSISTANT_DECLINE_OFF_TOPIC"), default=True),
            assistant_response_max_chars=int(os.getenv("ASSISTANT_RESPONSE_MAX_CHARS", "180")),
            turn_silence_threshold_ms=int(os.getenv("TURN_SILENCE_THRESHOLD_MS", "750")),
            turn_pre_speech_padding_ms=int(os.getenv("TURN_PRE_SPEECH_PADDING_MS", "200")),
            vad_energy_threshold=float(os.getenv("VAD_ENERGY_THRESHOLD", "0.02")),
            min_speech_ms=int(os.getenv("MIN_SPEECH_MS", "300")),
            call_audit_enabled=_truthy(os.getenv("CALL_AUDIT_ENABLED"), default=True),
            call_audit_log_transcripts=_truthy(os.getenv("CALL_AUDIT_LOG_TRANSCRIPTS"), default=True),
            call_audit_max_sessions=int(os.getenv("CALL_AUDIT_MAX_SESSIONS", "50")),
            call_no_reply_seconds=float(os.getenv("CALL_NO_REPLY_SECONDS", "15")),
            call_no_reply_prompt_seconds=float(os.getenv("CALL_NO_REPLY_PROMPT_SECONDS", "15")),
            call_max_no_reply_prompts=int(os.getenv("CALL_MAX_NO_REPLY_PROMPTS", "2")),
            call_max_off_topic_redirects=int(os.getenv("CALL_MAX_OFF_TOPIC_REDIRECTS", "2")),
            call_end_on_repeated_off_topic=_truthy(os.getenv("CALL_END_ON_REPEATED_OFF_TOPIC"), default=True),
            call_end_on_no_reply=_truthy(os.getenv("CALL_END_ON_NO_REPLY"), default=True),
            twilio_force_hangup_enabled=_truthy(os.getenv("TWILIO_FORCE_HANGUP_ENABLED"), default=False),
            twilio_debug_payloads_enabled=_truthy(os.getenv("TWILIO_DEBUG_PAYLOADS_ENABLED"), default=False),
            enable_twilio_tts_response=_truthy(os.getenv("ENABLE_TWILIO_TTS_RESPONSE"), default=False),
            enable_twilio_initial_greeting=_truthy(os.getenv("ENABLE_TWILIO_INITIAL_GREETING"), default=False),
            twilio_initial_greeting_text=os.getenv("TWILIO_INITIAL_GREETING_TEXT", DEFAULT_TWILIO_INITIAL_GREETING),
            twilio_initial_greeting_profile=os.getenv("TWILIO_INITIAL_GREETING_PROFILE", "greeting"),
            twilio_initial_greeting_fallback_say=_truthy(
                os.getenv("TWILIO_INITIAL_GREETING_FALLBACK_SAY"),
                default=False,
            ),
            azure_speech_voice=os.getenv("AZURE_SPEECH_VOICE", "th-TH-PremwadeeNeural"),
            tts_max_chars=int(os.getenv("TTS_MAX_CHARS", "220")),
            tts_output_format=os.getenv("TTS_OUTPUT_FORMAT", "mulaw_8khz"),
            tts_use_ssml=_truthy(os.getenv("TTS_USE_SSML"), default=True),
            tts_rate_normal=os.getenv("TTS_RATE_NORMAL", "0%"),
            tts_rate_followup=os.getenv("TTS_RATE_FOLLOWUP", "-5%"),
            tts_rate_greeting=os.getenv("TTS_RATE_GREETING", "-5%"),
            tts_rate_red=os.getenv("TTS_RATE_RED", "-12%"),
            tts_rate_unclear=os.getenv("TTS_RATE_UNCLEAR", "-8%"),
            tts_rate_closing=os.getenv("TTS_RATE_CLOSING", "-8%"),
            tts_pitch_normal=os.getenv("TTS_PITCH_NORMAL", "0%"),
            tts_pitch_greeting=os.getenv("TTS_PITCH_GREETING", "0%"),
            tts_pitch_red=os.getenv("TTS_PITCH_RED", "-2%"),
            tts_pitch_closing=os.getenv("TTS_PITCH_CLOSING", "0%"),
            tts_volume=os.getenv("TTS_VOLUME", "medium"),
        )

    @property
    def azure_speech_configured(self) -> bool:
        return bool(self.azure_speech_key and self.azure_speech_region)

    @property
    def azure_speech_tts_configured(self) -> bool:
        return self.azure_speech_configured

    def missing_azure_speech_tts_variables(self) -> list[str]:
        checks = {
            "AZURE_SPEECH_KEY": self.azure_speech_key,
            "AZURE_SPEECH_REGION": self.azure_speech_region,
        }
        return [name for name, value in checks.items() if not value]

    @property
    def azure_openai_configured(self) -> bool:
        return bool(
            self.azure_openai_endpoint
            and self.azure_openai_api_key
            and self.azure_openai_deployment
            and self.azure_openai_api_version
        )

    @property
    def azure_speech_openai_configured(self) -> bool:
        return self.azure_speech_configured and self.azure_openai_configured

    @property
    def azure_voice_live_configured(self) -> bool:
        return bool(self.azure_voice_live_endpoint and self.azure_voice_live_model)

    @property
    def normalized_realtime_provider(self) -> str:
        provider = self.realtime_provider.strip().lower() or "none"
        if provider in {"none", "azure_voice_live", "azure_openai_realtime"}:
            return provider
        return "none"

    @property
    def normalized_realtime_input_audio_format(self) -> str:
        audio_format = self.realtime_input_audio_format.strip().lower() or "pcm16"
        if audio_format in {"pcm16", "g711_ulaw"}:
            return audio_format
        return "pcm16"

    @property
    def effective_realtime_input_audio_format(self) -> str:
        if self.normalized_realtime_input_audio_format == "g711_ulaw" and self.realtime_twilio_audio_passthrough:
            return "g711_ulaw"
        return "pcm16"

    @property
    def realtime_input_audio_passthrough_enabled(self) -> bool:
        return self.effective_realtime_input_audio_format == "g711_ulaw"

    @property
    def normalized_realtime_output_voice(self) -> str:
        voice = self.realtime_output_voice.strip().lower() or "marin"
        if voice in SUPPORTED_REALTIME_OUTPUT_VOICES:
            return voice
        return "marin"

    @property
    def azure_openai_realtime_configured(self) -> bool:
        return bool(
            self.azure_realtime_endpoint
            and self.azure_realtime_api_key
            and self.azure_realtime_deployment
            and self.azure_realtime_api_version
        )

    @property
    def azure_voice_live_realtime_configured(self) -> bool:
        return bool(self.azure_voice_live_endpoint and self.azure_voice_live_model and self.azure_realtime_api_key)

    @property
    def realtime_configured(self) -> bool:
        if not self.enable_realtime_voice:
            return False
        if self.normalized_realtime_provider == "azure_openai_realtime":
            return self.azure_openai_realtime_configured
        if self.normalized_realtime_provider == "azure_voice_live":
            return self.azure_voice_live_realtime_configured
        return False

    def missing_realtime_variables(self) -> list[str]:
        if not self.enable_realtime_voice or self.normalized_realtime_provider == "none":
            return []
        if self.normalized_realtime_provider == "azure_openai_realtime":
            checks = {
                "AZURE_REALTIME_ENDPOINT": self.azure_realtime_endpoint,
                "AZURE_REALTIME_API_KEY": self.azure_realtime_api_key,
                "AZURE_REALTIME_DEPLOYMENT": self.azure_realtime_deployment,
                "AZURE_REALTIME_API_VERSION": self.azure_realtime_api_version,
            }
        elif self.normalized_realtime_provider == "azure_voice_live":
            checks = {
                "AZURE_REALTIME_API_KEY": self.azure_realtime_api_key,
                "AZURE_VOICE_LIVE_ENDPOINT": self.azure_voice_live_endpoint,
                "AZURE_VOICE_LIVE_MODEL": self.azure_voice_live_model,
            }
        else:
            return ["REALTIME_PROVIDER"]
        return [name for name, value in checks.items() if not value]

    def realtime_warnings(self) -> list[str]:
        warnings: list[str] = []
        if self.realtime_provider.strip().lower() != self.normalized_realtime_provider:
            warnings.append("REALTIME_PROVIDER is invalid; realtime voice is disabled.")
        if self.realtime_input_audio_format.strip().lower() != self.normalized_realtime_input_audio_format:
            warnings.append("REALTIME_INPUT_AUDIO_FORMAT is invalid; realtime input audio falls back to pcm16.")
        if self.realtime_output_voice.strip().lower() != self.normalized_realtime_output_voice:
            warnings.append("REALTIME_OUTPUT_VOICE is invalid; realtime output voice falls back to marin.")
        if (
            self.normalized_realtime_input_audio_format == "g711_ulaw"
            and not self.realtime_twilio_audio_passthrough
        ):
            warnings.append(
                "REALTIME_INPUT_AUDIO_FORMAT=g711_ulaw requires "
                "REALTIME_TWILIO_AUDIO_PASSTHROUGH=true; realtime input audio falls back to pcm16."
            )
        if not self.enable_realtime_voice:
            return warnings
        if self.normalized_realtime_provider == "none":
            warnings.append("ENABLE_REALTIME_VOICE is true but REALTIME_PROVIDER is none.")
        missing = self.missing_realtime_variables()
        if missing:
            warnings.append(f"Realtime provider is not configured; missing: {', '.join(missing)}.")
        return warnings

    @property
    def cosmos_configured(self) -> bool:
        return bool(
            self.cosmos_db_endpoint
            and self.cosmos_db_key
            and self.cosmos_db_database
            and self.cosmos_db_container
        )

    @property
    def twilio_configured(self) -> bool:
        return bool(self.twilio_webhook_public_base_url)

    @property
    def acs_configured(self) -> bool:
        return bool(self.acs_connection_string and self.acs_phone_number and self.acs_callback_public_base_url)

    @property
    def selected_provider(self) -> str:
        if self.use_mock_services:
            return "mock"
        if self.azure_speech_openai_configured:
            return "azure_speech_openai"
        if self.azure_voice_live_configured:
            return "azure_voice_live"
        return "mock"

    def missing_azure_variables(self) -> list[str]:
        checks = {
            "AZURE_SPEECH_KEY": self.azure_speech_key,
            "AZURE_SPEECH_REGION": self.azure_speech_region,
            "AZURE_OPENAI_ENDPOINT": self.azure_openai_endpoint,
            "AZURE_OPENAI_API_KEY": self.azure_openai_api_key,
            "AZURE_OPENAI_DEPLOYMENT": self.azure_openai_deployment,
            "AZURE_OPENAI_API_VERSION": self.azure_openai_api_version,
        }
        return [name for name, value in checks.items() if not value]


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
