from __future__ import annotations

from datetime import timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import DATA_HUB, DOMAIN
from .hub import CatFlapHub


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    hub: CatFlapHub = hass.data[DOMAIN][entry.entry_id][DATA_HUB]
    outside_entities: dict[str, CatOutsideTodaySensor] = {}
    async_add_entities(
        [
            CatFlapDirectionSensor(entry, hub),
            CatFlapLastChipSensor(entry, hub),
            CatFlapKnownCatSensor(entry, hub),
            CatFlapLastSeenSensor(entry, hub),
            CatFlapCatCountSensor(entry, hub),
        ]
    )

    def _add_missing_cat_entities() -> None:
        new_entities: list[CatOutsideTodaySensor] = []
        for chip_id in hub.cats:
            if chip_id in outside_entities:
                continue
            entity = CatOutsideTodaySensor(entry, hub, chip_id)
            outside_entities[chip_id] = entity
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


class CatFlapBaseSensor(SensorEntity):
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


class CatFlapDirectionSensor(CatFlapBaseSensor):
    def __init__(self, entry: ConfigEntry, hub: CatFlapHub) -> None:
        super().__init__(entry, hub)
        self._attr_name = f"{entry.title} Last Direction"
        self._attr_unique_id = f"{entry.entry_id}_last_direction"
        self._attr_icon = "mdi:swap-horizontal"

    @property
    def native_value(self) -> str | None:
        return self._hub.last_event.direction if self._hub.last_event else None


class CatFlapLastChipSensor(CatFlapBaseSensor):
    def __init__(self, entry: ConfigEntry, hub: CatFlapHub) -> None:
        super().__init__(entry, hub)
        self._attr_name = f"{entry.title} Last Chip"
        self._attr_unique_id = f"{entry.entry_id}_last_chip"
        self._attr_icon = "mdi:chip"

    @property
    def native_value(self) -> str | None:
        return self._hub.last_event.chip_id if self._hub.last_event else None


class CatFlapKnownCatSensor(CatFlapBaseSensor):
    def __init__(self, entry: ConfigEntry, hub: CatFlapHub) -> None:
        super().__init__(entry, hub)
        self._attr_name = f"{entry.title} Last Cat"
        self._attr_unique_id = f"{entry.entry_id}_last_cat"
        self._attr_icon = "mdi:cat"

    @property
    def native_value(self) -> str | None:
        if not self._hub.last_event or not self._hub.last_event.known_cat:
            return None
        return self._hub.last_event.cat_name


class CatFlapLastSeenSensor(CatFlapBaseSensor):
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, entry: ConfigEntry, hub: CatFlapHub) -> None:
        super().__init__(entry, hub)
        self._attr_name = f"{entry.title} Last Event"
        self._attr_unique_id = f"{entry.entry_id}_last_event"

    @property
    def native_value(self):
        if not self._hub.last_event:
            return None
        return dt_util.parse_datetime(self._hub.last_event.at)


class CatFlapCatCountSensor(CatFlapBaseSensor):
    def __init__(self, entry: ConfigEntry, hub: CatFlapHub) -> None:
        super().__init__(entry, hub)
        self._attr_name = f"{entry.title} Registered Cats"
        self._attr_unique_id = f"{entry.entry_id}_cat_count"
        self._attr_icon = "mdi:counter"

    @property
    def native_value(self) -> int:
        return len(self._hub.cats)


class CatOutsideTodaySensor(CatFlapBaseSensor):
    _attr_native_unit_of_measurement = "h"
    _attr_suggested_display_precision = 2
    _attr_icon = "mdi:timer-outline"

    def __init__(self, entry: ConfigEntry, hub: CatFlapHub, chip_id: str) -> None:
        super().__init__(entry, hub)
        self._chip_id = chip_id
        self._attr_unique_id = f"{entry.entry_id}_cat_outside_today_{chip_id}"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                self._async_handle_timer_tick,
                timedelta(minutes=1),
            )
        )

    @property
    def name(self) -> str:
        cat = self._hub.cats.get(self._chip_id)
        label = cat.name if cat else self._chip_id
        return f"{self._entry.title} {label} Outside Today"

    @property
    def native_value(self) -> float:
        return self._hub.get_outside_hours_today(self._chip_id)

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        cat = self._hub.cats.get(self._chip_id)
        return {
            "chip_id": self._chip_id,
            "cat_name": cat.name if cat else self._chip_id,
        }

    @callback
    def _async_handle_timer_tick(self, _now) -> None:
        self.async_write_ha_state()
