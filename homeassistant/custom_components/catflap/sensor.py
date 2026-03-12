from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DATA_HUB, DOMAIN
from .hub import CatFlapHub


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    hub: CatFlapHub = hass.data[DOMAIN][entry.entry_id][DATA_HUB]
    async_add_entities(
        [
            CatFlapDirectionSensor(entry, hub),
            CatFlapLastChipSensor(entry, hub),
            CatFlapKnownCatSensor(entry, hub),
            CatFlapLastSeenSensor(entry, hub),
            CatFlapCatCountSensor(entry, hub),
        ]
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
