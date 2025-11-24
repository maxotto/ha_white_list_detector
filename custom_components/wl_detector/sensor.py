"Sensor platform for wl_detector."
from __future__ import annotations
import logging

import httpx
import re
from datetime import timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.helpers.entity import DeviceInfo # New import

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

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=1)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    _LOGGER.debug("Setting up sensor platform for wl_detector.")
    client = get_async_client(hass)
    async_add_entities([InternetStateSensor(hass, entry, client)])


def _parse_urls(url_string: str) -> list[str]:
    """Parse a string of URLs separated by newlines or commas into a list."""
    if not url_string:
        return []
    # Replace newlines with commas to handle both as delimiters
    normalized_string = url_string.replace('\n', ',')
    # Split by comma and strip whitespace from each URL
    return [url.strip() for url in normalized_string.split(',') if url.strip()]


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
        
        self._global_urls = _parse_urls(entry.data.get(CONF_GLOBAL_URLS, ""))
        self._russia_urls = _parse_urls(entry.data.get(CONF_RUSSIA_URLS, ""))
        self._whitelist_urls = _parse_urls(entry.data.get(CONF_WHITELIST_URLS, ""))
        _LOGGER.debug(
            "Sensor Initialized. URLs: Global=%s, Russia=%s, Whitelist=%s",
            self._global_urls,
            self._russia_urls,
            self._whitelist_urls,
        )

        self._attr_native_value = None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information to group the entity."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name="Internet State Detector",
            manufacturer="maxotto",
            model="Network Monitor",
            sw_version="0.3.0",
        )

    async def _is_any_url_reachable(self, urls: list[str]) -> bool:
        """Check if any URL in the list is reachable."""
        if not urls:
            return False
            
        for url in urls:
            _LOGGER.debug("Checking URL: %s", url)
            try:
                response = await self._client.get(url, timeout=10, follow_redirects=True)
                if 200 <= response.status_code < 400:
                    _LOGGER.debug("URL %s is reachable (status code %d).", url, response.status_code)
                    return True
                else:
                    _LOGGER.debug("URL %s returned non-success status: %d", url, response.status_code)
            except httpx.RequestError as err:
                _LOGGER.debug("Failed to connect to URL %s. Error: %s", url, err)
                continue
        _LOGGER.debug("No URLs in this list were reachable.")
        return False

    async def async_update(self) -> None:
        """Fetch new state data for the sensor based on the check logic."""
        _LOGGER.debug("!!! Starting new internet state check !!!")
        
        old_state = self._attr_native_value  # Store old state
        
        _LOGGER.debug("--- Checking Global URLs ---")
        if await self._is_any_url_reachable(self._global_urls):
            self._attr_native_value = STATE_FULL_ACCESS
        else:
            _LOGGER.debug("--- Checking Russia URLs ---")
            if await self._is_any_url_reachable(self._russia_urls):
                self._attr_native_value = STATE_RUSSIA_ONLY
            else:
                _LOGGER.debug("--- Checking Whitelist URLs ---")
                if await self._is_any_url_reachable(self._whitelist_urls):
                    self._attr_native_value = STATE_WHITELIST_ONLY
                else:
                    _LOGGER.debug("--- No URLs reachable at all ---")
                    self._attr_native_value = STATE_NO_INTERNET
        
        # Log state change
        if old_state != self._attr_native_value:
            _LOGGER.info(
                f"Internet status changed from '{old_state}' to '{self._attr_native_value}'"
            )
        _LOGGER.debug("!!! FINISHED. Internet state updated to: %s !!!", self._attr_native_value)