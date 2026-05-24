"""Config flow for Birdfy."""

from __future__ import annotations

import secrets
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    API2_BASE_URL,
    CAPI2_BASE_URL,
    CAPIV3_BASE_URL,
    DEFAULT_BASE_URL,
    BirdfyAuthError,
    BirdfyClient,
    BirdfyConnectionError,
)
from .const import (
    CONF_API2_BASE_URL,
    CONF_BASE_URL,
    CONF_CAPI2_BASE_URL,
    CONF_CAPIV3_BASE_URL,
    CONF_REFRESH_INTERVAL,
    CONF_TOKEN_DATA,
    CONF_UDID,
    DOMAIN,
)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
    }
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_REFRESH_INTERVAL, default=5): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
        vol.Optional(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
        vol.Optional(CONF_API2_BASE_URL, default=API2_BASE_URL): str,
        vol.Optional(CONF_CAPI2_BASE_URL, default=CAPI2_BASE_URL): str,
        vol.Optional(CONF_CAPIV3_BASE_URL, default=CAPIV3_BASE_URL): str,
    }
)


class BirdfyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for Birdfy."""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        self._reauth_entry: config_entries.ConfigEntry | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            udid = _new_udid()
            validation_input = {**user_input, CONF_UDID: udid}
            try:
                tokens = await self._async_validate_user_input(validation_input)
            except BirdfyAuthError:
                errors["base"] = "invalid_auth"
            except BirdfyConnectionError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(tokens.user_id)
                self._abort_if_unique_id_configured()
                data = {
                    CONF_USERNAME: user_input[CONF_USERNAME],
                    CONF_BASE_URL: user_input[CONF_BASE_URL],
                    CONF_TOKEN_DATA: tokens.as_dict(),
                    CONF_UDID: udid,
                }
                return self.async_create_entry(title=tokens.username or user_input[CONF_USERNAME], data=data)

        return self.async_show_form(step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors)

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Handle reauthentication."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Confirm reauthentication credentials."""
        errors: dict[str, str] = {}
        if user_input is not None:
            udid = _entry_udid(self._reauth_entry)
            validation_input = {**user_input, CONF_UDID: udid}
            try:
                tokens = await self._async_validate_user_input(validation_input)
            except BirdfyAuthError:
                errors["base"] = "invalid_auth"
            except BirdfyConnectionError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(tokens.user_id)
                self._abort_if_unique_id_mismatch(reason="wrong_account")
                return self.async_update_reload_and_abort(
                    self._reauth_entry,
                    data_updates={
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_BASE_URL: user_input[CONF_BASE_URL],
                        CONF_TOKEN_DATA: tokens.as_dict(),
                        CONF_UDID: udid,
                    },
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    async def _async_validate_user_input(self, user_input: dict[str, Any]):
        session = async_get_clientsession(self.hass)
        client = BirdfyClient(
            session,
            base_url=user_input.get(CONF_BASE_URL, DEFAULT_BASE_URL),
            udid=user_input.get(CONF_UDID),
        )
        return await client.login(user_input[CONF_USERNAME], user_input[CONF_PASSWORD])

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> BirdfyOptionsFlow:
        """Create the options flow."""
        return BirdfyOptionsFlow(config_entry)


class BirdfyOptionsFlow(config_entries.OptionsFlow):
    """Handle Birdfy options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = {
            CONF_REFRESH_INTERVAL: self._config_entry.options.get(CONF_REFRESH_INTERVAL, 5),
            CONF_BASE_URL: self._config_entry.options.get(
                CONF_BASE_URL, self._config_entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL)
            ),
            CONF_API2_BASE_URL: self._config_entry.options.get(CONF_API2_BASE_URL, API2_BASE_URL),
            CONF_CAPI2_BASE_URL: self._config_entry.options.get(CONF_CAPI2_BASE_URL, CAPI2_BASE_URL),
            CONF_CAPIV3_BASE_URL: self._config_entry.options.get(CONF_CAPIV3_BASE_URL, CAPIV3_BASE_URL),
        }
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(OPTIONS_SCHEMA, current),
        )


def _new_udid() -> str:
    """Return a stable per-config-entry Netvue client identifier."""
    return secrets.token_hex(16)


def _entry_udid(entry: config_entries.ConfigEntry | None) -> str:
    """Return the stored client identifier, or create one for legacy entries."""
    if entry is not None:
        udid = entry.data.get(CONF_UDID)
        if isinstance(udid, str) and udid:
            return udid
    return _new_udid()
