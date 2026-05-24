"""Image entities for Birdfy."""

from __future__ import annotations

from datetime import UTC, datetime

from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BirdfyConfigEntry
from .coordinator import BirdfyCoordinator
from .entity import BirdfyEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BirdfyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Birdfy image entities."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(BirdfyLatestEventImage(coordinator, device_id) for device_id in coordinator.data.devices)


class BirdfyLatestEventImage(BirdfyEntity, ImageEntity):
    """Latest Birdfy event image."""

    _attr_translation_key = "latest_event_image"

    def __init__(self, coordinator: BirdfyCoordinator, device_id: str) -> None:
        ImageEntity.__init__(self, coordinator.hass)
        BirdfyEntity.__init__(self, coordinator, device_id, "latest_event_image")

    @property
    def image_last_updated(self) -> datetime | None:
        """Return when the event image last changed."""
        event = self._latest_event
        return event.occurred_at if event and event.image_url else None

    @property
    def image_url(self) -> str | None:
        """Return image URL for the frontend cache."""
        event = self._latest_event
        return event.image_url if event else None

    @property
    def _latest_event(self):
        if not self.coordinator.data:
            return None
        events = [
            event
            for event in self.coordinator.data.events.values()
            if event.device_id == self.device_id and event.image_url
        ]
        if not events:
            return None
        return max(events, key=lambda event: event.occurred_at or datetime.min.replace(tzinfo=UTC))
