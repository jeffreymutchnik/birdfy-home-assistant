"""Repairs for Birdfy."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN


async def async_create_unsupported_control_issue(hass: HomeAssistant, issue_id: str) -> None:
    """Create a repair issue for unsupported write controls."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="unsupported_control",
    )
