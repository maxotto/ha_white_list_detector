"""Config flow for wl_detector."""
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigEntry, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_GLOBAL_URLS,
    CONF_RUSSIA_URLS,
    CONF_WHITELIST_URLS,
)


class WlDetectorOptionsFlowHandler(OptionsFlow):
    """Handle an options flow for wl_detector."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get current values or fall back to original data
        global_urls = self.config_entry.options.get(
            CONF_GLOBAL_URLS, self.config_entry.data.get(CONF_GLOBAL_URLS, "")
        )
        russia_urls = self.config_entry.options.get(
            CONF_RUSSIA_URLS, self
            .config_entry.data.get(CONF_RUSSIA_URLS, "")
        )
        whitelist_urls = self.config_entry.options.get(
            CONF_WHITELIST_URLS,
            self.config_entry.data.get(CONF_WHITELIST_URLS, ""),
        )

        options_schema = vol.Schema({
            vol.Required(CONF_GLOBAL_URLS, default=global_urls): selector.TextSelector(
                selector.TextSelectorConfig(multiline=True),
            ),
            vol.Required(CONF_RUSSIA_URLS, default=russia_urls): selector.TextSelector(
                selector.TextSelectorConfig(multiline=True),
            ),
            vol.Required(
                CONF_WHITELIST_URLS, default=whitelist_urls
            ): selector.TextSelector(
                selector.TextSelectorConfig(multiline=True),
            ),
        })

        return self.async_show_form(
            step_id="init", data_schema=options_schema
        )


class WlDetectorConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for wl_detector."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> WlDetectorOptionsFlowHandler:
        """Get the options flow for this handler."""
        return WlDetectorOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors = {}
        if user_input is not None:
            return self.async_create_entry(title="Internet State Detector", data=user_input)

        data_schema = vol.Schema({
            vol.Required(CONF_GLOBAL_URLS, default="https://www.google.com"): selector.TextSelector(
                selector.TextSelectorConfig(multiline=True),
            ),
            vol.Required(CONF_RUSSIA_URLS, default="https://kp40.ru"): selector.TextSelector(
                selector.TextSelectorConfig(multiline=True),
            ),
            vol.Required(CONF_WHITELIST_URLS, default="http://dzen.ru/"): selector.TextSelector(
                selector.TextSelectorConfig(multiline=True),
            ),
        })

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )
