"""LESCO CCMS bill custom integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LescoApi
from .const import CONF_REFERENCE, DOMAIN
from .coordinator import LescoCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """v1 had phone/password/reference; v2 keeps reference only."""
    if entry.version >= 2:
        return True
    ref = (entry.data or {}).get(CONF_REFERENCE)
    if not ref or not str(ref).strip():
        _LOGGER.error("Migration failed: missing reference in config entry %s", entry.entry_id)
        return False
    hass.config_entries.async_update_entry(
        entry,
        data={CONF_REFERENCE: str(ref).strip()},
        version=2,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from UI config."""
    session = async_get_clientsession(hass)
    api = LescoApi(session)
    coordinator = LescoCoordinator(hass, entry, api)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
