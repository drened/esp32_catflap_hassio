from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DIRECTION_IN, DIRECTION_OUT
from .models import CatProfile, FlapEvent

STORAGE_VERSION = 1


class CatFlapHub:
    """Runtime and persisted state for one cat flap config entry."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"catflap.{entry.entry_id}"
        )
        self.cats: dict[str, CatProfile] = {}
        self.last_event: FlapEvent | None = None
        self.signal_state = f"catflap_state_{entry.entry_id}"

    async def async_load(self) -> None:
        data = await self._store.async_load()
        if not data:
            return

        raw_cats = data.get("cats", {})
        self.cats = {
            chip_id: CatProfile.from_dict(item)
            for chip_id, item in raw_cats.items()
        }

        raw_event = data.get("last_event")
        self.last_event = FlapEvent.from_dict(raw_event) if raw_event else None

    async def async_save(self) -> None:
        await self._store.async_save(
            {
                "cats": {
                    chip_id: profile.to_dict()
                    for chip_id, profile in self.cats.items()
                },
                "last_event": self.last_event.to_dict() if self.last_event else None,
            }
        )

    async def async_register_cat(self, chip_id: str, name: str, inside: bool) -> None:
        self.cats[chip_id] = CatProfile(chip_id=chip_id, name=name, inside=inside)
        await self.async_save()
        self._async_publish()

    async def async_remove_cat(self, chip_id: str) -> bool:
        removed = self.cats.pop(chip_id, None)
        if removed is None:
            return False

        await self.async_save()
        self._async_publish()
        return True

    async def async_set_presence(self, chip_id: str, inside: bool) -> bool:
        cat = self.cats.get(chip_id)
        if cat is None:
            return False

        cat.inside = inside
        await self.async_save()
        self._async_publish()
        return True

    async def async_process_event(
        self,
        chip_id: str,
        direction: str,
        source: str | None = None,
    ) -> FlapEvent:
        cat = self.cats.get(chip_id)
        known_cat = cat is not None

        if known_cat and direction == DIRECTION_IN:
            cat.inside = True
        elif known_cat and direction == DIRECTION_OUT:
            cat.inside = False

        event = FlapEvent(
            chip_id=chip_id,
            direction=direction,
            at=dt_util.utcnow().isoformat(),
            source=source,
            cat_name=cat.name if cat else None,
            known_cat=known_cat,
        )
        self.last_event = event

        await self.async_save()
        self._async_publish()
        return event

    def _async_publish(self) -> None:
        async_dispatcher_send(self.hass, self.signal_state)
