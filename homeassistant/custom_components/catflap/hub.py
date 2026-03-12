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
        self.outside_today_seconds: dict[str, float] = {}
        self.currently_outside_since: dict[str, str | None] = {}
        self.last_reset_date: str = dt_util.now().date().isoformat()
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
        self.outside_today_seconds = {
            chip_id: float(seconds)
            for chip_id, seconds in data.get("outside_today_seconds", {}).items()
        }
        self.currently_outside_since = {
            chip_id: (str(value) if value else None)
            for chip_id, value in data.get("currently_outside_since", {}).items()
        }
        self.last_reset_date = str(
            data.get("last_reset_date", dt_util.now().date().isoformat())
        )
        self._rollover_if_needed()
        self._ensure_cat_stats()

    async def async_save(self) -> None:
        self._rollover_if_needed()
        await self._store.async_save(
            {
                "cats": {
                    chip_id: profile.to_dict()
                    for chip_id, profile in self.cats.items()
                },
                "last_event": self.last_event.to_dict() if self.last_event else None,
                "outside_today_seconds": self.outside_today_seconds,
                "currently_outside_since": self.currently_outside_since,
                "last_reset_date": self.last_reset_date,
            }
        )

    async def async_register_cat(self, chip_id: str, name: str, inside: bool) -> None:
        self._rollover_if_needed()
        self.cats[chip_id] = CatProfile(chip_id=chip_id, name=name, inside=inside)
        self.outside_today_seconds.setdefault(chip_id, 0.0)
        if inside:
            self.currently_outside_since[chip_id] = None
        else:
            self.currently_outside_since[chip_id] = dt_util.now().isoformat()
        await self.async_save()
        self._async_publish()

    async def async_remove_cat(self, chip_id: str) -> bool:
        removed = self.cats.pop(chip_id, None)
        if removed is None:
            return False

        self.outside_today_seconds.pop(chip_id, None)
        self.currently_outside_since.pop(chip_id, None)
        await self.async_save()
        self._async_publish()
        return True

    async def async_set_presence(self, chip_id: str, inside: bool) -> bool:
        self._rollover_if_needed()
        cat = self.cats.get(chip_id)
        if cat is None:
            return False

        self._apply_presence_change(chip_id, inside)
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
        self._rollover_if_needed()
        cat = self.cats.get(chip_id)
        known_cat = cat is not None

        if known_cat and direction == DIRECTION_IN:
            self._apply_presence_change(chip_id, inside=True)
            cat.inside = True
        elif known_cat and direction == DIRECTION_OUT:
            self._apply_presence_change(chip_id, inside=False)
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

    def get_outside_hours_today(self, chip_id: str) -> float:
        self._rollover_if_needed()
        base_seconds = self.outside_today_seconds.get(chip_id, 0.0)
        since_raw = self.currently_outside_since.get(chip_id)
        if since_raw:
            since = dt_util.parse_datetime(since_raw)
            if since:
                base_seconds += max(0.0, (dt_util.now() - since).total_seconds())
        return round(base_seconds / 3600.0, 2)

    def _async_publish(self) -> None:
        async_dispatcher_send(self.hass, self.signal_state)

    def _ensure_cat_stats(self) -> None:
        now_iso = dt_util.now().isoformat()
        for chip_id, cat in self.cats.items():
            self.outside_today_seconds.setdefault(chip_id, 0.0)
            self.currently_outside_since.setdefault(
                chip_id, None if cat.inside else now_iso
            )

    def _apply_presence_change(self, chip_id: str, inside: bool) -> None:
        self._ensure_cat_stats()
        now = dt_util.now()
        now_iso = now.isoformat()
        since_raw = self.currently_outside_since.get(chip_id)

        if inside:
            if since_raw:
                since = dt_util.parse_datetime(since_raw)
                if since:
                    self.outside_today_seconds[chip_id] = (
                        self.outside_today_seconds.get(chip_id, 0.0)
                        + max(0.0, (now - since).total_seconds())
                    )
            self.currently_outside_since[chip_id] = None
            return

        if since_raw is None:
            self.currently_outside_since[chip_id] = now_iso

    def _rollover_if_needed(self) -> None:
        today = dt_util.now().date().isoformat()
        if self.last_reset_date == today:
            return

        today_start = dt_util.start_of_local_day()
        for chip_id in list(self.outside_today_seconds):
            self.outside_today_seconds[chip_id] = 0.0

        for chip_id, since_raw in list(self.currently_outside_since.items()):
            if since_raw is None:
                continue
            since_dt = dt_util.parse_datetime(since_raw)
            if since_dt is None or since_dt < today_start:
                self.currently_outside_since[chip_id] = today_start.isoformat()

        self.last_reset_date = today
