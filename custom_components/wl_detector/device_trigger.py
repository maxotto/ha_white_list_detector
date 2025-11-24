"""Provides device triggers for wl_detector."""
from __future__ import annotations

import voluptuous as vol
from typing import Any

from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import state as state_trigger
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_ENTITY_ID,
    CONF_PLATFORM,
    CONF_TYPE,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

# Типы триггеров
TRIGGER_TYPE_FULL_ACCESS = "full_access"
TRIGGER_TYPE_RUSSIA_ONLY = "russia_only"
TRIGGER_TYPE_WHITELIST_ONLY = "whitelist_only"
TRIGGER_TYPE_NO_INTERNET = "no_internet"
TRIGGER_TYPE_CONNECTION_CHANGED = "connection_changed"

TRIGGER_TYPES = {
    TRIGGER_TYPE_FULL_ACCESS,
    TRIGGER_TYPE_RUSSIA_ONLY,
    TRIGGER_TYPE_WHITELIST_ONLY,
    TRIGGER_TYPE_NO_INTERNET,
    TRIGGER_TYPE_CONNECTION_CHANGED,
}

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_ENTITY_ID): cv.entity_id,
        vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES),
    }
)


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, Any]]:
    """List device triggers for wl_detector devices."""
    registry = er.async_get(hass)
    triggers = []

    # Получаем все сущности для этого устройства
    for entry in er.async_entries_for_device(registry, device_id):
        # Only interested in sensor entities from this integration
        if entry.domain != "sensor" or entry.platform != DOMAIN:
            continue

        base_trigger = {
            CONF_PLATFORM: "device",
            CONF_DEVICE_ID: device_id,
            CONF_DOMAIN: DOMAIN,
            CONF_ENTITY_ID: entry.entity_id,
        }

        # Добавляем триггеры для каждого состояния
        triggers.append({
            **base_trigger,
            CONF_TYPE: TRIGGER_TYPE_FULL_ACCESS,
            "name": "Полный доступ к интернету",
        })
        
        triggers.append({
            **base_trigger,
            CONF_TYPE: TRIGGER_TYPE_RUSSIA_ONLY,
            "name": "Доступ только к российским сайтам",
        })
        
        triggers.append({
            **base_trigger,
            CONF_TYPE: TRIGGER_TYPE_WHITELIST_ONLY,
            "name": "Доступ только к белому списку",
        })
        
        triggers.append({
            **base_trigger,
            CONF_TYPE: TRIGGER_TYPE_NO_INTERNET,
            "name": "Нет доступа к интернету",
        })
        
        triggers.append({
            **base_trigger,
            CONF_TYPE: TRIGGER_TYPE_CONNECTION_CHANGED,
            "name": "Статус подключения изменился",
        })

    return triggers


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Attach a trigger."""
    trigger_type = config[CONF_TYPE]
    
    if trigger_type == TRIGGER_TYPE_CONNECTION_CHANGED:
        # Триггер на любое изменение состояния
        state_config = {
            CONF_PLATFORM: "state",
            CONF_ENTITY_ID: config[CONF_ENTITY_ID],
        }
    else:
        # Триггер на конкретное состояние
        from .const import (
            STATE_FULL_ACCESS,
            STATE_RUSSIA_ONLY,
            STATE_WHITELIST_ONLY,
            STATE_NO_INTERNET,
        )
        
        state_map = {
            TRIGGER_TYPE_FULL_ACCESS: STATE_FULL_ACCESS,
            TRIGGER_TYPE_RUSSIA_ONLY: STATE_RUSSIA_ONLY,
            TRIGGER_TYPE_WHITELIST_ONLY: STATE_WHITELIST_ONLY,
            TRIGGER_TYPE_NO_INTERNET: STATE_NO_INTERNET,
        }
        
        state_config = {
            CONF_PLATFORM: "state",
            CONF_ENTITY_ID: config[CONF_ENTITY_ID],
            "to": state_map[trigger_type],
        }

    state_config = await state_trigger.async_validate_trigger_config(hass, state_config)
    return await state_trigger.async_attach_trigger(
        hass, state_config, action, trigger_info, platform_type="device"
    )