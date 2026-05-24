"""Camera entities for Birdfy."""

from __future__ import annotations

import logging

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BirdfyConfigEntry
from .api import BirdfyError
from .const import CONF_LOCAL_SNAPSHOT_URL, CONF_LOCAL_STREAM_URL
from .coordinator import BirdfyCoordinator
from .entity import BirdfyEntity

LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BirdfyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Birdfy cameras."""
    coordinator = entry.runtime_data.coordinator
    has_manual_media = _option_url(entry, CONF_LOCAL_STREAM_URL) or _option_url(entry, CONF_LOCAL_SNAPSHOT_URL)
    async_add_entities(
        BirdfyCamera(coordinator, entry, device_id)
        for device_id, device in coordinator.data.devices.items()
        if has_manual_media
        or device.capabilities.supports_video
        or device.capabilities.supports_snapshot
        or device.snapshot_url
    )


class BirdfyCamera(BirdfyEntity, Camera):
    """Birdfy camera with still image and optional direct stream support."""

    _attr_translation_key = "camera"

    def __init__(
        self,
        coordinator: BirdfyCoordinator,
        entry: BirdfyConfigEntry,
        device_id: str,
    ) -> None:
        BirdfyEntity.__init__(self, coordinator, device_id, "camera")
        Camera.__init__(self)
        self._entry = entry
        self._stream_source: str | None = None
        self._stream_checked = False

    @property
    def supported_features(self) -> CameraEntityFeature:
        """Return supported camera features."""
        features = CameraEntityFeature(0)
        if self._stream_source:
            features |= CameraEntityFeature.STREAM
        return features

    async def async_camera_image(
        self,
        width: int | None = None,
        height: int | None = None,
    ) -> bytes | None:
        """Return a still image."""
        device = self.device
        snapshot_url = _option_url(self._entry, CONF_LOCAL_SNAPSHOT_URL) or (
            device.snapshot_url if device else None
        )
        if device is None or not snapshot_url:
            return None
        try:
            return await self.coordinator.client.fetch_image(snapshot_url)
        except BirdfyError as err:
            LOGGER.debug("Unable to fetch Birdfy camera image: %s", err)
            return None

    async def stream_source(self) -> str | None:
        """Return a stream source if the API exposes a direct URL."""
        device = self.device
        if device is None:
            return None
        manual_stream = _option_url(self._entry, CONF_LOCAL_STREAM_URL)
        if manual_stream:
            return manual_stream
        if self._stream_checked:
            return self._stream_source
        self._stream_checked = True
        try:
            self._stream_source = await self.coordinator.client.get_stream_source(device)
        except BirdfyError as err:
            LOGGER.debug("Unable to resolve Birdfy stream source: %s", err)
            self._stream_source = None
        if self._stream_source:
            self.async_write_ha_state()
        return self._stream_source


def _option_url(entry: BirdfyConfigEntry, key: str) -> str | None:
    value = entry.options.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else None
