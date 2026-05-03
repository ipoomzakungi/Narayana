from __future__ import annotations

from dataclasses import dataclass
import os
from functools import lru_cache

DEFAULT_CORS_ALLOW_ORIGINS = ("http://localhost:3000", "http://127.0.0.1:3000")


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

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            azure_speech_key=os.getenv("AZURE_SPEECH_KEY", ""),
            azure_speech_region=os.getenv("AZURE_SPEECH_REGION", ""),
            azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
            azure_openai_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", ""),
            azure_openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", ""),
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
        )

    @property
    def azure_speech_configured(self) -> bool:
        return bool(self.azure_speech_key and self.azure_speech_region)

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
