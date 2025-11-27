"Sensor platform for wl_detector."
from __future__ import annotations
import asyncio
import logging

import httpx
from datetime import timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.helpers.entity import DeviceInfo

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
    _LOGGER.warning("Setting up sensor platform for wl_detector.")
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

        # Combine data and options, with options taking precedence
        config = {**entry.data, **entry.options}

        self._global_urls = _parse_urls(config.get(CONF_GLOBAL_URLS, ""))
        self._russia_urls = _parse_urls(config.get(CONF_RUSSIA_URLS, ""))
        self._whitelist_urls = _parse_urls(config.get(CONF_WHITELIST_URLS, ""))

        _LOGGER.warning(
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
            sw_version="0.3.7",
        )

    async def _check_single_url(self, url: str, timeout: float = 5.0) -> bool:
        """Check a single URL using HEAD request, fallback to GET if HEAD is not supported."""
        _LOGGER.warning("Checking URL: %s", url)

        try:
            # First try HEAD request
            response = await self._client.head(url, timeout=httpx.Timeout(timeout, connect=timeout))
            # If HEAD returns status in 200-399 range, the URL is reachable
            if 200 <= response.status_code < 400:
                _LOGGER.warning("URL %s is reachable via HEAD (status code %d).", url, response.status_code)
                return True
        except httpx.RequestError:
            # If HEAD fails, try GET request as fallback
            try:
                response = await self._client.get(url, timeout=httpx.Timeout(timeout, connect=timeout))
                if 200 <= response.status_code < 400:
                    _LOGGER.warning("URL %s is reachable via GET (status code %d).", url, response.status_code)
                    return True
            except httpx.RequestError as err:
                _LOGGER.warning("Failed to connect to URL %s. Error: %s", url, err)

        return False

    async def _is_any_url_reachable(self, urls: list[str], timeout: float = 5.0) -> bool:
        """Check if any URL in the list is reachable using parallel requests."""
        if not urls:
            return False

        # Create tasks for all URL checks to run in parallel
        tasks = [self._check_single_url(url, timeout) for url in urls]

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check if any of the results is True (meaning URL is reachable)
        for result in results:
            if isinstance(result, bool) and result:
                return True
            elif isinstance(result, Exception):
                _LOGGER.warning("Exception during URL checking: %s", result)

        _LOGGER.warning("No URLs in this list were reachable.")
        return False

    async def async_update(self) -> None:
        """Fetch new state data for the sensor based on the check logic."""
        _LOGGER.warning("!!! Starting new internet state check !!!")

        old_state = self._attr_native_value  # Store old state

        _LOGGER.warning("--- Checking all URL lists in parallel ---")
        
        # Run checks for all lists in parallel
        global_check, russia_check, whitelist_check = await asyncio.gather(
            self._is_any_url_reachable(self._global_urls),
            self._is_any_url_reachable(self._russia_urls),
            self._is_any_url_reachable(self._whitelist_urls),
            return_exceptions=True
        )

        _LOGGER.warning(f"Check results: Global={global_check}, Russia={russia_check}, Whitelist={whitelist_check}")

        # Determine the new state based on the results, maintaining priority
        if global_check is True:
            self._attr_native_value = STATE_FULL_ACCESS
        elif russia_check is True:
            self._attr_native_value = STATE_RUSSIA_ONLY
        elif whitelist_check is True:
            self._attr_native_value = STATE_WHITELIST_ONLY
        else:
            self._attr_native_value = STATE_NO_INTERNET

        # Log state change
        if old_state != self._attr_native_value:
            _LOGGER.info(
                f"Internet status changed from '{old_state}' to '{self._attr_native_value}'"
            )
        _LOGGER.warning("!!! FINISHED. Internet state updated to: %s !!!", self._attr_native_value)
