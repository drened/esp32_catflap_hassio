from __future__ import annotations

from datetime import timedelta

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DATA_HUB, DOMAIN
from .hub import CatFlapHub

ACTIVE_WINDOW = timedelta(seconds=30)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    hub: CatFlapHub = hass.data[DOMAIN][entry.entry_id][DATA_HUB]

    known_cat_entities: dict[str, CatInsideBinarySensor] = {}
    async_add_entities([CatFlapActivityBinarySensor(entry, hub)])

    def _add_missing_cat_entities() -> None:
        new_entities: list[CatInsideBinarySensor] = []
        for chip_id in hub.cats:
            if chip_id in known_cat_entities:
                continue
            entity = CatInsideBinarySensor(entry, hub, chip_id)
            known_cat_entities[chip_id] = entity
            new_entities.append(entity)
        if new_entities:
            async_add_entities(new_entities)

    _add_missing_cat_entities()

    @callback
    def _handle_dispatcher_update() -> None:
        _add_missing_cat_entities()

    entry.async_on_unload(
        async_dispatcher_connect(hass, hub.signal_state, _handle_dispatcher_update)
    )


class CatFlapBaseBinarySensor(BinarySensorEntity):
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, hub: CatFlapHub) -> None:
        self._entry = entry
        self._hub = hub
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "DIY",
            "model": "ESP32 Cat Flap",
        }

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, self._hub.signal_state, self._async_handle_state_update
            )
        )

    @callback
    def _async_handle_state_update(self) -> None:
        self.async_write_ha_state()


class CatFlapActivityBinarySensor(CatFlapBaseBinarySensor):
    def __init__(self, entry: ConfigEntry, hub: CatFlapHub) -> None:
        super().__init__(entry, hub)
        self._attr_name = f"{entry.title} Activity"
        self._attr_unique_id = f"{entry.entry_id}_activity"
        self._attr_icon = "mdi:cat"

    @property
    def is_on(self) -> bool:
        if not self._hub.last_event:
            return False
        last_at = dt_util.parse_datetime(self._hub.last_event.at)
        if last_at is None:
            return False
        return dt_util.utcnow() - last_at <= ACTIVE_WINDOW


class CatInsideBinarySensor(CatFlapBaseBinarySensor):
    def __init__(self, entry: ConfigEntry, hub: CatFlapHub, chip_id: str) -> None:
        super().__init__(entry, hub)
        self._chip_id = chip_id
        self._attr_unique_id = f"{entry.entry_id}_cat_inside_{chip_id}"
        self._attr_icon = "mdi:home-account"

    @property
    def name(self) -> str:
        cat = self._hub.cats.get(self._chip_id)
        label = cat.name if cat else self._chip_id
        return f"{self._entry.title} {label} Inside"

    @property
    def is_on(self) -> bool:
        cat = self._hub.cats.get(self._chip_id)
        return cat.inside if cat else False

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        cat = self._hub.cats.get(self._chip_id)
        return {
            "chip_id": self._chip_id,
            "cat_name": cat.name if cat else self._chip_id,
        }
