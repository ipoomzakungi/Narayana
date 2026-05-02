from __future__ import annotations

import base64
import io
from pathlib import Path
from urllib.error import HTTPError
from urllib import parse

import pytest

from scripts import check_public_webhook
from scripts import twilio_outbound_call


class FakeResponse:
    def __init__(self, body: str, status: int = 200) -> None:
        self._body = body.encode("utf-8")
        self.status = status

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args) -> None:
        return None

    def read(self) -> bytes:
        return self._body

    def getcode(self) -> int:
        return self.status


def test_dockerfile_contract() -> None:
    text = Path("Dockerfile").read_text(encoding="utf-8")

    assert "FROM python:3.11-slim" in text
    assert "EXPOSE 8000" in text
    assert '"uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"' in text


def test_dockerignore_excludes_secrets_and_local_artifacts() -> None:
    text = Path(".dockerignore").read_text(encoding="utf-8")

    for pattern in [".env", ".env.*", ".data/", ".git/", "frontend/node_modules/", "frontend/.next/"]:
        assert pattern in text


def test_deploy_script_mentions_required_values_and_fallback_commands() -> None:
    text = Path("scripts/azure_container_apps_deploy.ps1").read_text(encoding="utf-8")

    for value in [
        "AZURE_RESOURCE_GROUP",
        "AZURE_LOCATION",
        "AZURE_CONTAINER_APP_NAME",
        "TWILIO_PHONE_NUMBER",
        "TWILIO_WEBHOOK_PUBLIC_BASE_URL",
    ]:
        assert value in text
    assert "az containerapp up" in text
    assert "az acr build" in text
    assert "az containerapp create" in text


def test_normalize_base_url_trims_trailing_slash() -> None:
    assert check_public_webhook.normalize_base_url("https://example.test/") == "https://example.test"


@pytest.mark.parametrize("value", ["", "example.test", "ftp://example.test"])
def test_normalize_base_url_rejects_malformed_values(value: str) -> None:
    with pytest.raises(check_public_webhook.ToolingError):
        check_public_webhook.normalize_base_url(value)


def test_base_url_from_env_prefers_twilio_and_falls_back_to_azure_url() -> None:
    assert (
        check_public_webhook.base_url_from_env(
            {
                "TWILIO_WEBHOOK_PUBLIC_BASE_URL": "https://twilio.example",
                "AZURE_CONTAINER_APP_URL": "https://azure.example",
            }
        )
        == "https://twilio.example"
    )
    assert check_public_webhook.base_url_from_env({"AZURE_CONTAINER_APP_URL": "https://azure.example/"}) == "https://azure.example"


def test_endpoint_url_construction() -> None:
    urls = check_public_webhook.endpoint_urls("https://example.test/")

    assert urls.health_url == "https://example.test/api/health/azure"
    assert urls.twilio_webhook_url == "https://example.test/api/telephony/twilio/incoming-call"


def test_twiml_parser_accepts_expected_media_path() -> None:
    xml = '<Response><Connect><Stream url="wss://example.test/ws/telephony/twilio/CA_TEST" /></Connect></Response>'

    assert check_public_webhook.twiml_has_media_stream(xml)


def test_twiml_parser_rejects_missing_media_path() -> None:
    xml = '<Response><Connect><Stream url="wss://example.test/ws/telephony/twilio/CA_OTHER" /></Connect></Response>'

    assert not check_public_webhook.twiml_has_media_stream(xml)


def test_public_webhook_check_uses_fake_call_sid_without_real_network() -> None:
    calls = []

    def opener(target, timeout=10):
        calls.append(target)
        if target.full_url.endswith("/api/health/azure"):
            return FakeResponse('{"selected_provider":"mock"}')
        return FakeResponse(
            '<Response><Connect><Stream url="wss://example.test/ws/telephony/twilio/CA_TEST" /></Connect></Response>'
        )

    result = check_public_webhook.run_check({"TWILIO_WEBHOOK_PUBLIC_BASE_URL": "https://example.test"}, opener=opener)

    assert result.health_ok is True
    assert result.twiml_ok is True
    assert len(calls) == 2
    assert calls[1].data is not None
    assert parse.parse_qs(calls[1].data.decode("utf-8"))["CallSid"] == ["CA_TEST"]


def test_outbound_config_reports_all_missing_values() -> None:
    with pytest.raises(twilio_outbound_call.ToolingError) as exc:
        twilio_outbound_call.config_from_env({})

    message = str(exc.value)
    for value in twilio_outbound_call.REQUIRED_ENV:
        assert value in message


def valid_outbound_env() -> dict[str, str]:
    return {
        "TWILIO_ACCOUNT_SID": "AC123",
        "TWILIO_AUTH_TOKEN": "secret",
        "TWILIO_PHONE_NUMBER": "+16082005400",
        "TWILIO_OUTBOUND_TO": "+66999999999",
        "TWILIO_WEBHOOK_PUBLIC_BASE_URL": "https://example.test/",
    }


def test_outbound_request_body_and_auth_header() -> None:
    config = twilio_outbound_call.config_from_env(valid_outbound_env())
    outbound_request = twilio_outbound_call.build_twilio_call_request(config)
    body = parse.parse_qs(outbound_request.data.decode("utf-8"))
    expected_token = base64.b64encode(b"AC123:secret").decode("ascii")

    assert outbound_request.full_url == "https://api.twilio.com/2010-04-01/Accounts/AC123/Calls.json"
    assert body["From"] == ["+16082005400"]
    assert body["To"] == ["+66999999999"]
    assert body["Url"] == ["https://example.test/api/telephony/twilio/incoming-call"]
    assert outbound_request.get_header("Authorization") == f"Basic {expected_token}"


def test_outbound_call_success_parses_call_sid_without_real_network() -> None:
    config = twilio_outbound_call.config_from_env(valid_outbound_env())

    def opener(target, timeout=20):
        assert target.full_url.endswith("/Calls.json")
        return FakeResponse('{"sid":"CA_OUTBOUND"}')

    assert twilio_outbound_call.create_outbound_call(config, opener=opener) == "CA_OUTBOUND"


def test_outbound_call_error_mentions_troubleshooting_without_real_network() -> None:
    config = twilio_outbound_call.config_from_env(valid_outbound_env())

    def opener(target, timeout=20):
        raise HTTPError(target.full_url, 400, "Bad Request", {}, io.BytesIO(b'{"message":"Geo permission blocked"}'))

    with pytest.raises(twilio_outbound_call.ToolingError) as exc:
        twilio_outbound_call.create_outbound_call(config, opener=opener)

    message = str(exc.value)
    assert "verified caller ID" in message
    assert "Geo Permissions" in message
