from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_CHIP_ID,
    CONF_DIRECTION,
    CONF_ENTRY_ID,
    CONF_INSIDE,
    CONF_NAME,
    CONF_SOURCE,
    DATA_HUB,
    DOMAIN,
    PLATFORMS,
    SERVICE_PROCESS_EVENT,
    SERVICE_REGISTER_CAT,
    SERVICE_REMOVE_CAT,
    SERVICE_SET_PRESENCE,
    VALID_DIRECTIONS,
)
from .hub import CatFlapHub

PROCESS_EVENT_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_ENTRY_ID): str,
        vol.Required(CONF_CHIP_ID): cv.string,
        vol.Required(CONF_DIRECTION): vol.In(VALID_DIRECTIONS),
        vol.Optional(CONF_SOURCE): cv.string,
    }
)

REGISTER_CAT_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_ENTRY_ID): str,
        vol.Required(CONF_CHIP_ID): cv.string,
        vol.Required(CONF_NAME): cv.string,
        vol.Optional(CONF_INSIDE, default=False): cv.boolean,
    }
)

REMOVE_CAT_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_ENTRY_ID): str,
        vol.Required(CONF_CHIP_ID): cv.string,
    }
)

SET_PRESENCE_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_ENTRY_ID): str,
        vol.Required(CONF_CHIP_ID): cv.string,
        vol.Required(CONF_INSIDE): cv.boolean,
    }
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})

    if not hass.services.has_service(DOMAIN, SERVICE_PROCESS_EVENT):
        await _async_register_services(hass)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hub = CatFlapHub(hass, entry)
    await hub.async_load()
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {DATA_HUB: hub}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    hass.data[DOMAIN].pop(entry.entry_id)
    return True


async def _async_register_services(hass: HomeAssistant) -> None:
    async def _process_event(service_call) -> None:
        hub = _resolve_hub(hass, service_call.data.get(CONF_ENTRY_ID))
        await hub.async_process_event(
            chip_id=service_call.data[CONF_CHIP_ID],
            direction=service_call.data[CONF_DIRECTION],
            source=service_call.data.get(CONF_SOURCE),
        )

    async def _register_cat(service_call) -> None:
        hub = _resolve_hub(hass, service_call.data.get(CONF_ENTRY_ID))
        await hub.async_register_cat(
            chip_id=service_call.data[CONF_CHIP_ID],
            name=service_call.data[CONF_NAME],
            inside=service_call.data[CONF_INSIDE],
        )

    async def _remove_cat(service_call) -> None:
        hub = _resolve_hub(hass, service_call.data.get(CONF_ENTRY_ID))
        removed = await hub.async_remove_cat(chip_id=service_call.data[CONF_CHIP_ID])
        if not removed:
            raise HomeAssistantError("Unknown chip_id")

    async def _set_presence(service_call) -> None:
        hub = _resolve_hub(hass, service_call.data.get(CONF_ENTRY_ID))
        updated = await hub.async_set_presence(
            chip_id=service_call.data[CONF_CHIP_ID],
            inside=service_call.data[CONF_INSIDE],
        )
        if not updated:
            raise HomeAssistantError("Unknown chip_id")

    hass.services.async_register(
        DOMAIN,
        SERVICE_PROCESS_EVENT,
        _process_event,
        schema=PROCESS_EVENT_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REGISTER_CAT,
        _register_cat,
        schema=REGISTER_CAT_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_CAT,
        _remove_cat,
        schema=REMOVE_CAT_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_PRESENCE,
        _set_presence,
        schema=SET_PRESENCE_SCHEMA,
    )


def _resolve_hub(hass: HomeAssistant, entry_id: str | None) -> CatFlapHub:
    entries: dict = hass.data.get(DOMAIN, {})
    if not entries:
        raise HomeAssistantError("No cat flap config entries loaded")

    if entry_id:
        bucket = entries.get(entry_id)
        if not bucket:
            raise HomeAssistantError(f"Unknown entry_id: {entry_id}")
        return bucket[DATA_HUB]

    if len(entries) == 1:
        only_entry_id = next(iter(entries))
        return entries[only_entry_id][DATA_HUB]

    raise HomeAssistantError("Multiple entries configured. Provide entry_id.")
