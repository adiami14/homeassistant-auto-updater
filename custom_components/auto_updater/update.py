"""Mock update entity for testing Auto Updater."""
from __future__ import annotations

import logging

from homeassistant.components.update import UpdateEntity, UpdateEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_TEST_MODE, DOMAIN

_LOGGER = logging.getLogger(__name__)

_MOCK_INSTALLED = "1.0.0"
_MOCK_LATEST = "2.0.0"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    cfg = {**entry.data, **entry.options}
    if cfg.get(CONF_TEST_MODE, False):
        async_add_entities([MockUpdateEntity(entry.entry_id)])


class MockUpdateEntity(UpdateEntity):
    """Fake update entity — only exists when test mode is enabled."""

    _attr_has_entity_name = True
    _attr_name = "Mock Test Update"
    _attr_title = "Auto Updater Test Add-on"
    _attr_release_summary = (
        "This is a fake update created by Auto Updater's test mode. "
        "Disable test mode in the integration options when done."
    )
    _attr_supported_features = UpdateEntityFeature.INSTALL

    def __init__(self, entry_id: str) -> None:
        self._attr_unique_id = f"{DOMAIN}_mock_update_{entry_id}"
        self._attr_installed_version = _MOCK_INSTALLED
        self._attr_latest_version = _MOCK_LATEST

    async def async_install(
        self, version: str | None, backup: bool, **kwargs
    ) -> None:
        """Simulate a successful install."""
        _LOGGER.info(
            "Auto Updater: mock update 'installed' %s → %s (test entity)",
            self._attr_installed_version,
            self._attr_latest_version,
        )
        self._attr_installed_version = self._attr_latest_version
        self.async_write_ha_state()
