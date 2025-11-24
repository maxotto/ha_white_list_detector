"""Config flow for wl_detector."""
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_GLOBAL_URLS,
    CONF_RUSSIA_URLS,
    CONF_WHITELIST_URLS,
)

class WlDetectorConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for wl_detector."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        # Abort if an entry is already configured
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors = {}
        if user_input is not None:
            # For now, we accept the input. Validation could be added here.
            # The component will handle splitting the string of URLs.
            return self.async_create_entry(title="Internet State Detector", data=user_input)

        # Schema with textareas for URL lists
        data_schema = vol.Schema({
            vol.Required(CONF_GLOBAL_URLS, default="https://www.google.com"): selector.TextSelector(
                selector.TextSelectorConfig(multiline=True),
            ),
            vol.Required(CONF_RUSSIA_URLS, default="https://ya.ru"): selector.TextSelector(
                selector.TextSelectorConfig(multiline=True),
            ),
            vol.Required(CONF_WHITELIST_URLS, default="https://example.com"): selector.TextSelector(
                selector.TextSelectorConfig(multiline=True),
            ),
        })

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )