"""Diagnostics support for Birdfy."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import BirdfyConfigEntry
from .api import SENSITIVE_KEYS, redact_data
from .coordinator import redacted_device_payload

TO_REDACT = {*SENSITIVE_KEYS, "password", "token_data"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: BirdfyConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data.coordinator
    devices = list(coordinator.data.devices.values()) if coordinator.data else []
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "options": async_redact_data(dict(entry.options), TO_REDACT),
        "devices": [redacted_device_payload(device) for device in devices],
        "events_known": len(coordinator.data.events) if coordinator.data else 0,
        "client": redact_data(
            {
                "base_url": entry.data.get("base_url"),
                "authenticated": entry.runtime_data.client.authenticated,
            }
        ),
    }
