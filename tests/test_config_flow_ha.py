# ruff: noqa: E402
"""Home Assistant config flow tests.

These tests require pytest-homeassistant-custom-component and are skipped in the
fast local suite when the Home Assistant test harness is not installed.
"""

from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip("homeassistant")
pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.birdfy.api import BirdfyAuthError, BirdfyConnectionError, BirdfyTokens
from custom_components.birdfy.config_flow import BirdfyConfigFlow
from custom_components.birdfy.const import (
    CONF_BASE_URL,
    CONF_REFRESH_INTERVAL,
    CONF_TOKEN_DATA,
    CONF_UDID,
    DOMAIN,
)
from custom_components.birdfy.coordinator import redacted_device_payload
from pybirdfy.client import BirdfyCapabilities, BirdfyDevice

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


@pytest.fixture(autouse=True)
def bypass_stream_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    """Config-flow tests do not need to initialize Home Assistant stream/PyAV."""

    async def async_process_deps_reqs(hass: Any, config: dict[str, Any], integration: Any) -> None:
        return None

    monkeypatch.setattr(config_entries, "async_process_deps_reqs", async_process_deps_reqs)


async def test_user_flow_creates_entry(hass: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """Successful credentials create a config entry without storing a password."""

    async def validate(self: BirdfyConfigFlow, user_input: dict[str, Any]) -> BirdfyTokens:
        assert isinstance(user_input[CONF_UDID], str)
        assert len(user_input[CONF_UDID]) == 32
        return BirdfyTokens(
            token="access-token",
            refresh_token="refresh-token",
            user_id="user-123",
            username=user_input[CONF_USERNAME],
            region="us",
        )

    monkeypatch.setattr(BirdfyConfigFlow, "_async_validate_user_input", validate)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            CONF_USERNAME: "fixture-user@example.invalid",
            CONF_PASSWORD: "secret-password",
            CONF_BASE_URL: "http://127.0.0.1:8765/v1/",
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "fixture-user@example.invalid"
    assert CONF_PASSWORD not in result["data"]
    assert result["data"][CONF_TOKEN_DATA]["token"] == "access-token"
    assert len(result["data"][CONF_UDID]) == 32


@pytest.mark.parametrize(
    ("exception", "error"),
    (
        (BirdfyAuthError, "invalid_auth"),
        (BirdfyConnectionError, "cannot_connect"),
    ),
)
async def test_user_flow_reports_actionable_errors(
    hass: Any,
    monkeypatch: pytest.MonkeyPatch,
    exception: type[Exception],
    error: str,
) -> None:
    """Credential and connection errors are mapped to UI form errors."""

    async def validate(self: BirdfyConfigFlow, user_input: dict[str, Any]) -> BirdfyTokens:
        raise exception("boom")

    monkeypatch.setattr(BirdfyConfigFlow, "_async_validate_user_input", validate)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            CONF_USERNAME: "fixture-user@example.invalid",
            CONF_PASSWORD: "secret-password",
            CONF_BASE_URL: "http://127.0.0.1:8765/v1/",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}


async def test_user_flow_rejects_duplicate_account(
    hass: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A second config flow for the same account is aborted."""

    entry = MockConfigEntry(domain=DOMAIN, unique_id="user-123", data={})
    entry.add_to_hass(hass)

    async def validate(self: BirdfyConfigFlow, user_input: dict[str, Any]) -> BirdfyTokens:
        return BirdfyTokens(
            token="access-token",
            refresh_token="refresh-token",
            user_id="user-123",
            username=user_input[CONF_USERNAME],
        )

    monkeypatch.setattr(BirdfyConfigFlow, "_async_validate_user_input", validate)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            CONF_USERNAME: "fixture-user@example.invalid",
            CONF_PASSWORD: "secret-password",
            CONF_BASE_URL: "http://127.0.0.1:8765/v1/",
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow_updates_refresh_interval(hass: Any) -> None:
    """Options flow stores polling and endpoint settings."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_BASE_URL: "http://127.0.0.1:8765/v1/",
            CONF_TOKEN_DATA: {
                "token": "access-token",
                "refresh_token": "refresh-token",
                "user_id": "user-123",
            },
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_REFRESH_INTERVAL: 3,
            CONF_BASE_URL: "http://127.0.0.1:8765/v1/",
            "api2_base_url": "https://api2.nvts.co/",
            "capi2_base_url": "https://capi2.nvts.co/",
            "capiv3_base_url": "https://capiv3.nvts.co/",
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_REFRESH_INTERVAL] == 3


async def test_redacted_device_payload_omits_private_identifiers() -> None:
    """Device diagnostics expose capability shape, not private IDs or URLs."""
    signed_url = "https://" + "signed.example.test" + "/snapshot" + ".jpg?token=secret"
    device = BirdfyDevice(
        identifier="REAL_DEVICE_ID",
        serial_number="REAL_SERIAL",
        name="Private Yard Camera",
        model="Birdfy",
        manufacturer="Birdfy",
        firmware="1.2.3",
        online=True,
        battery_level=88,
        signal_level=71,
        snapshot_url=signed_url,
        region="us",
        capabilities=BirdfyCapabilities(
            supports_video=True,
            supports_snapshot=True,
            supports_motion_detection=True,
            supports_local_storage=True,
        ),
        raw={
            "serialNumber": "REAL_SERIAL",
            "snapshotUrl": signed_url,
        },
        services={"cloud": {"enabled": True}},
    )

    payload = redacted_device_payload(device)
    encoded = str(payload)

    assert payload["has_name"] is True
    assert payload["has_snapshot_url"] is True
    assert payload["services_present"] is True
    assert payload["raw_payload_shape"]["top_level_keys"] == ["serialNumber", "snapshotUrl"]
    assert payload["raw_payload_shape"]["candidate_values"] == {}
    assert "REAL_DEVICE_ID" not in encoded
    assert "REAL_SERIAL" not in encoded
    assert "Private Yard Camera" not in encoded
    assert "signed.example.test" not in encoded
    assert "token=secret" not in encoded
