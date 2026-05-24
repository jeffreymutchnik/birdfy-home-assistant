"""Event entities for Birdfy."""

from __future__ import annotations

from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BirdfyConfigEntry
from .api import BirdfyEvent
from .const import EVENT_TYPES, SIGNAL_EVENT
from .coordinator import BirdfyCoordinator
from .entity import BirdfyEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BirdfyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Birdfy event entities."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        BirdfyEventEntity(coordinator, entry.entry_id, device_id) for device_id in coordinator.data.devices
    )


class BirdfyEventEntity(BirdfyEntity, EventEntity):
    """Birdfy event entity."""

    _attr_translation_key = "activity"
    _attr_event_types = EVENT_TYPES

    def __init__(self, coordinator: BirdfyCoordinator, entry_id: str, device_id: str) -> None:
        super().__init__(coordinator, device_id, "activity")
        self.entry_id = entry_id

    async def async_added_to_hass(self) -> None:
        """Subscribe to event coordinator signals."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_EVENT}_{self.entry_id}",
                self._async_handle_birdfy_event,
            )
        )

    @callback
    def _async_handle_birdfy_event(self, event: BirdfyEvent) -> None:
        """Handle a new Birdfy event."""
        if event.device_id != self.device_id or event.event_type not in EVENT_TYPES:
            return
        attributes: dict[str, Any] = {}
        if event.species:
            attributes["species"] = event.species
        if event.clip_url:
            attributes["has_clip"] = True
        if event.image_url:
            attributes["has_image"] = True
        self._trigger_event(event.event_type, attributes)
        self.async_write_ha_state()
