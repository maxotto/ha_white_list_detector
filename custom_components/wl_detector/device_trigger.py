"""Provides device triggers for wl_detector."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import state as state_trigger
from homeassistant.const import CONF_PLATFORM, ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.trigger import TriggerActionType, TriggerData
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    STATE_FULL_ACCESS,
    STATE_RUSSIA_ONLY,
    STATE_WHITELIST_ONLY,
    STATE_NO_INTERNET,
)

TRIGGER_TYPES = {
    "state_full_access": "Full access",
    "state_russia_only": "Russia only",
    "state_whitelist_only": "Whitelist only",
    "state_no_internet": "No internet",
}

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_PLATFORM): "device",
        vol.Required("device_id"): str,
        vol.Required("domain"): DOMAIN,
        vol.Required("type"): vol.In(TRIGGER_TYPES),
    }
)


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, str]]:
    """List device triggers for wl_detector devices."""
    triggers = []

    # Get all entities for this device
    device_registry = dr.async_get(hass)
    entity_registry = hass.helpers.entity_registry.async_get(hass)

    for entry in dr.async_get_entries_for_device(
        device_registry, device_id, include_disabled_entities=True
    ):
        if entry.domain == "sensor" and entry.platform == DOMAIN:
            for trigger_type, state_value in TRIGGER_TYPES.items():
                triggers.append(
                    TRIGGER_SCHEMA(
                        {
                            "device_id": device_id,
                            "domain": DOMAIN,
                            "type": trigger_type,
                            ATTR_ENTITY_ID: entry.entity_id,
                        }
                    )
                )
    return triggers


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_data: TriggerData,
) -> None:
    """Attach a trigger."""
    trigger_type = config["type"]
    entity_id = config[ATTR_ENTITY_ID]
    state_value = TRIGGER_TYPES[trigger_type]

    state_config = {
        state_trigger.CONF_PLATFORM: "state",
        state_trigger.CONF_ENTITY_ID: entity_id,
        state_trigger.CONF_TO: state_value,
    }

    return await state_trigger.async_attach_trigger(
        hass, state_config, action, trigger_data
    )
