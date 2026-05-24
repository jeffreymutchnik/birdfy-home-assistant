"""Switch entities for Birdfy.

No write controls are exposed yet. The Birdfy app supports settings such as
motion detection, lights, siren, and privacy/sleep behavior, but public evidence
does not currently identify stable and safe write endpoints for Home Assistant.
"""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BirdfyConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BirdfyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Birdfy switches."""
    async_add_entities([])
