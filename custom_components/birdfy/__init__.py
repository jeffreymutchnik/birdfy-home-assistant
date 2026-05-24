"""Birdfy / Netvue Smart Bird Feeder integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    API2_BASE_URL,
    CAPI2_BASE_URL,
    CAPIV3_BASE_URL,
    DEFAULT_BASE_URL,
    BirdfyAuthError,
    BirdfyClient,
    BirdfyConnectionError,
    BirdfyTokens,
)
from .const import (
    CONF_API2_BASE_URL,
    CONF_BASE_URL,
    CONF_CAPI2_BASE_URL,
    CONF_CAPIV3_BASE_URL,
    CONF_REFRESH_INTERVAL,
    CONF_TOKEN_DATA,
    DOMAIN,
    PLATFORMS,
    STARTUP_MESSAGE,
)
from .coordinator import BirdfyCoordinator, BirdfyEventCoordinator, BirdfyRuntimeData

LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA: vol.Schema = cv.config_entry_only_config_schema(DOMAIN)

type BirdfyConfigEntry = ConfigEntry[BirdfyRuntimeData]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the integration."""
    LOGGER.info(STARTUP_MESSAGE)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: BirdfyConfigEntry) -> bool:
    """Set up Birdfy from a config entry."""
    session = async_get_clientsession(hass)
    token_data = entry.data.get(CONF_TOKEN_DATA)
    tokens = BirdfyTokens.from_dict(token_data) if isinstance(token_data, dict) else None

    async def _async_store_tokens(new_tokens: BirdfyTokens) -> None:
        data = dict(entry.data)
        data[CONF_TOKEN_DATA] = new_tokens.as_dict()
        hass.config_entries.async_update_entry(entry, data=data)

    client = BirdfyClient(
        session,
        tokens=tokens,
        base_url=entry.options.get(CONF_BASE_URL, entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL)),
        api2_base_url=entry.options.get(CONF_API2_BASE_URL, entry.data.get(CONF_API2_BASE_URL, API2_BASE_URL)),
        capi2_base_url=entry.options.get(CONF_CAPI2_BASE_URL, entry.data.get(CONF_CAPI2_BASE_URL, CAPI2_BASE_URL)),
        capiv3_base_url=entry.options.get(CONF_CAPIV3_BASE_URL, entry.data.get(CONF_CAPIV3_BASE_URL, CAPIV3_BASE_URL)),
        request_interval=0.25,
        token_update_callback=_async_store_tokens,
    )

    if tokens is None and CONF_USERNAME in entry.data and CONF_PASSWORD in entry.data:
        try:
            await client.login(entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
        except BirdfyAuthError as err:
            raise ConfigEntryAuthFailed("Birdfy rejected the configured credentials") from err
        except BirdfyConnectionError as err:
            raise ConfigEntryNotReady("Unable to connect to Birdfy cloud API") from err

    coordinator = BirdfyCoordinator(hass, entry, client)
    coordinator.update_interval = timedelta(minutes=entry.options.get(CONF_REFRESH_INTERVAL, 5))
    event_coordinator = BirdfyEventCoordinator(hass, entry, client, coordinator)
    entry.runtime_data = BirdfyRuntimeData(client, coordinator, event_coordinator)

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryAuthFailed:
        raise
    except Exception as err:
        raise ConfigEntryNotReady(f"Unable to update Birdfy devices: {err}") from err

    await event_coordinator.async_config_entry_first_refresh()
    # Event entities listen through dispatcher signals, so keep this coordinator
    # subscribed explicitly to allow DataUpdateCoordinator to schedule polling.
    entry.async_on_unload(event_coordinator.async_add_listener(lambda: None))
    await hass.config_entries.async_forward_entry_setups(
        entry,
        [Platform(platform) for platform in PLATFORMS],
    )
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BirdfyConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(
        entry,
        [Platform(platform) for platform in PLATFORMS],
    )


async def async_reload_entry(hass: HomeAssistant, entry: BirdfyConfigEntry) -> None:
    """Reload Birdfy when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
