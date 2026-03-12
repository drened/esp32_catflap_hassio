from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ACTIVITY_WINDOW_SECONDS,
    CONF_EVENT_DEDUPE_SECONDS,
    DEFAULT_ACTIVITY_WINDOW_SECONDS,
    DEFAULT_EVENT_DEDUPE_SECONDS,
    DIRECTION_IN,
    DIRECTION_OUT,
    DIRECTION_UNKNOWN,
)
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
        self.total_events: int = 0
        self.duplicate_events: int = 0
        self.unknown_chip_events: int = 0
        self.unknown_direction_events: int = 0
        self.last_duplicate_at: str | None = None
        self.last_duplicate_key: str | None = None
        self._last_processed_at_by_key: dict[str, str] = {}
        self.event_dedupe_seconds = 0
        self.activity_window_seconds = 0
        self.outside_today_seconds: dict[str, float] = {}
        self.currently_outside_since: dict[str, str | None] = {}
        self.last_reset_date: str = dt_util.now().date().isoformat()
        self.signal_state = f"catflap_state_{entry.entry_id}"
        self.refresh_options()

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
        self.total_events = int(data.get("total_events", 0))
        self.duplicate_events = int(data.get("duplicate_events", 0))
        self.unknown_chip_events = int(data.get("unknown_chip_events", 0))
        self.unknown_direction_events = int(data.get("unknown_direction_events", 0))
        self.last_duplicate_at = data.get("last_duplicate_at")
        self.last_duplicate_key = data.get("last_duplicate_key")
        self._last_processed_at_by_key = {
            key: str(value)
            for key, value in data.get("last_processed_at_by_key", {}).items()
        }
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
                "total_events": self.total_events,
                "duplicate_events": self.duplicate_events,
                "unknown_chip_events": self.unknown_chip_events,
                "unknown_direction_events": self.unknown_direction_events,
                "last_duplicate_at": self.last_duplicate_at,
                "last_duplicate_key": self.last_duplicate_key,
                "last_processed_at_by_key": self._last_processed_at_by_key,
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

    async def async_update_cat(
        self,
        old_chip_id: str,
        new_chip_id: str,
        name: str,
        inside: bool,
    ) -> bool:
        self._rollover_if_needed()
        current = self.cats.get(old_chip_id)
        if current is None:
            return False

        if new_chip_id != old_chip_id and new_chip_id in self.cats:
            return False

        outside_seconds = self.outside_today_seconds.pop(old_chip_id, 0.0)
        outside_since = self.currently_outside_since.pop(old_chip_id, None)
        self.cats.pop(old_chip_id)
        self.cats[new_chip_id] = CatProfile(
            chip_id=new_chip_id,
            name=name,
            inside=inside,
        )

        self.outside_today_seconds[new_chip_id] = outside_seconds
        if inside:
            self.currently_outside_since[new_chip_id] = None
        else:
            self.currently_outside_since[new_chip_id] = (
                outside_since or dt_util.now().isoformat()
            )

        await self.async_save()
        self._async_publish()
        return True

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
        dedupe_key = f"{chip_id}:{direction}"
        now = dt_util.utcnow()
        if self._is_duplicate_event(dedupe_key, now):
            self.duplicate_events += 1
            self.last_duplicate_key = dedupe_key
            self.last_duplicate_at = now.isoformat()
            await self.async_save()
            self._async_publish()
            return self.last_event or FlapEvent(
                chip_id=chip_id,
                direction=direction,
                at=now.isoformat(),
                source=source,
                cat_name=None,
                known_cat=False,
            )

        self._last_processed_at_by_key[dedupe_key] = now.isoformat()
        self.total_events += 1
        cat = self.cats.get(chip_id)
        known_cat = cat is not None
        if not known_cat:
            self.unknown_chip_events += 1
        if direction == DIRECTION_UNKNOWN:
            self.unknown_direction_events += 1

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

    def _is_duplicate_event(self, key: str, now) -> bool:
        if self.event_dedupe_seconds <= 0:
            return False

        prev_raw = self._last_processed_at_by_key.get(key)
        if not prev_raw:
            return False

        prev = dt_util.parse_datetime(prev_raw)
        if prev is None:
            return False

        return (now - prev).total_seconds() < self.event_dedupe_seconds

    def _int_option(self, key: str, default: int) -> int:
        raw = self.entry.options.get(key, default)
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return default
        return max(0, value)

    def refresh_options(self) -> None:
        self.event_dedupe_seconds = self._int_option(
            CONF_EVENT_DEDUPE_SECONDS, DEFAULT_EVENT_DEDUPE_SECONDS
        )
        self.activity_window_seconds = self._int_option(
            CONF_ACTIVITY_WINDOW_SECONDS, DEFAULT_ACTIVITY_WINDOW_SECONDS
        )
