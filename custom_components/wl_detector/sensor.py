"""Sensor platform for wl_detector."""
from __future__ import annotations

import httpx
import re
from datetime import timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.httpx_client import get_async_client

from .const import (
    DOMAIN,
    STATE_FULL_ACCESS,
    STATE_RUSSIA_ONLY,
    STATE_WHITELIST_ONLY,
    STATE_NO_INTERNET,
    CONF_GLOBAL_URLS,
    CONF_RUSSIA_URLS,
    CONF_WHITELIST_URLS,
)

SCAN_INTERVAL = timedelta(minutes=1)  # More frequent checks might be useful


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    client = get_async_client(hass)
    # Create and add the single sensor
    async_add_entities([InternetStateSensor(hass, entry, client)])


def _parse_urls(url_string: str) -> list[str]:
    """Parse a string of URLs separated by newlines or commas into a list."""
    if not url_string:
        return []
    # Split by comma or newline and strip whitespace from each URL
    return [url.strip() for url in re.split(r'[,]+', url_string) if url.strip()]


class InternetStateSensor(SensorEntity):
    """Representation of the Internet State Sensor."""

    _attr_has_entity_name = True
    _attr_name = "Internet State"
    _attr_icon = "mdi:network-check"

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: httpx.AsyncClient,
    ) -> None:
        """Initialize the sensor."""
        self._hass = hass
        self._entry = entry
        self._client = client
        self._attr_unique_id = f"{entry.entry_id}_internet_state"
        
        # Parse the URL lists from the config entry
        self._global_urls = _parse_urls(entry.data.get(CONF_GLOBAL_URLS, ""))
        self._russia_urls = _parse_urls(entry.data.get(CONF_RUSSIA_URLS, ""))
        self._whitelist_urls = _parse_urls(entry.data.get(CONF_WHITELIST_URLS, ""))

        self._attr_state = None # Initial state

    @property
    def device_info(self):
        """Return device information to group the entity."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "Internet State Detector",
            "manufacturer": "maxotto", # Using your codeowner name
        }

    async def _is_any_url_reachable(self, urls: list[str]) -> bool:
        """Check if any URL in the list is reachable."""
        for url in urls:
            try:
                response = await self._client.get(url, timeout=10, follow_redirects=True)
                # We consider any 2xx or 3xx status as "reachable"
                if 200 <= response.status_code < 400:
                    return True
            except httpx.RequestError:
                # Ignore connection errors and try the next URL
                continue
        return False

    async def async_update(self) -> None:
        """Fetch new state data for the sensor based on the check logic."""
        if await self._is_any_url_reachable(self._global_urls):
            self._attr_state = STATE_FULL_ACCESS
        elif await self._is_any_url_reachable(self._russia_urls):
            self._attr_state = STATE_RUSSIA_ONLY
        elif await self._is_any_url_reachable(self._whitelist_urls):
            self._attr_state = STATE_WHITELIST_ONLY
        else:
            self._attr_state = STATE_NO_INTERNET