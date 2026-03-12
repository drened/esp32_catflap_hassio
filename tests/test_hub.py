from __future__ import annotations

import copy
import importlib
import importlib.util
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace


def _install_fake_homeassistant(now_ref: dict[str, datetime]) -> None:
    homeassistant = types.ModuleType("homeassistant")
    config_entries = types.ModuleType("homeassistant.config_entries")
    core = types.ModuleType("homeassistant.core")
    helpers = types.ModuleType("homeassistant.helpers")
    dispatcher = types.ModuleType("homeassistant.helpers.dispatcher")
    storage = types.ModuleType("homeassistant.helpers.storage")
    util = types.ModuleType("homeassistant.util")
    dt = types.ModuleType("homeassistant.util.dt")

    class ConfigEntry:
        def __init__(self, entry_id: str) -> None:
            self.entry_id = entry_id

    class HomeAssistant:
        def __init__(self) -> None:
            self.data = {}
            self._signals: list[str] = []

    class Store:
        _db: dict[str, dict] = {}

        def __init__(self, _hass, _version, key) -> None:
            self.key = key

        async def async_load(self):
            data = Store._db.get(self.key)
            return copy.deepcopy(data) if data else None

        async def async_save(self, data):
            Store._db[self.key] = copy.deepcopy(data)

    def async_dispatcher_send(hass: HomeAssistant, signal: str) -> None:
        hass._signals.append(signal)

    def now() -> datetime:
        return now_ref["now"]

    def utcnow() -> datetime:
        return now_ref["now"]

    def parse_datetime(value: str):
        return datetime.fromisoformat(value)

    def start_of_local_day():
        current = now_ref["now"]
        return current.replace(hour=0, minute=0, second=0, microsecond=0)

    config_entries.ConfigEntry = ConfigEntry
    core.HomeAssistant = HomeAssistant
    dispatcher.async_dispatcher_send = async_dispatcher_send
    storage.Store = Store
    dt.now = now
    dt.utcnow = utcnow
    dt.parse_datetime = parse_datetime
    dt.start_of_local_day = start_of_local_day

    homeassistant.config_entries = config_entries
    homeassistant.core = core
    homeassistant.helpers = helpers
    homeassistant.util = util
    helpers.dispatcher = dispatcher
    helpers.storage = storage
    util.dt = dt

    sys.modules["homeassistant"] = homeassistant
    sys.modules["homeassistant.config_entries"] = config_entries
    sys.modules["homeassistant.core"] = core
    sys.modules["homeassistant.helpers"] = helpers
    sys.modules["homeassistant.helpers.dispatcher"] = dispatcher
    sys.modules["homeassistant.helpers.storage"] = storage
    sys.modules["homeassistant.util"] = util
    sys.modules["homeassistant.util.dt"] = dt


class CatFlapHubTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.now_ref = {"now": datetime(2026, 3, 12, 10, 0, tzinfo=timezone.utc)}
        _install_fake_homeassistant(self.now_ref)

        root = Path(__file__).resolve().parents[1]
        catflap_dir = root / "custom_components" / "catflap"

        custom_components_pkg = types.ModuleType("custom_components")
        custom_components_pkg.__path__ = [str(root / "custom_components")]
        catflap_pkg = types.ModuleType("custom_components.catflap")
        catflap_pkg.__path__ = [str(catflap_dir)]
        sys.modules["custom_components"] = custom_components_pkg
        sys.modules["custom_components.catflap"] = catflap_pkg

        self._load_module(
            "custom_components.catflap.const", catflap_dir / "const.py"
        )
        self._load_module(
            "custom_components.catflap.models", catflap_dir / "models.py"
        )
        self.hub_module = self._load_module(
            "custom_components.catflap.hub", catflap_dir / "hub.py"
        )
        storage_module = importlib.import_module("homeassistant.helpers.storage")
        storage_module.Store._db.clear()

        self.hass = SimpleNamespace(data={}, _signals=[])
        self.entry = SimpleNamespace(entry_id="entry-1", options={})
        self.hub = self.hub_module.CatFlapHub(self.hass, self.entry)
        await self.hub.async_load()

    @staticmethod
    def _load_module(module_name: str, path: Path):
        spec = importlib.util.spec_from_file_location(module_name, path)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    def _advance(self, **kwargs) -> None:
        self.now_ref["now"] = self.now_ref["now"] + timedelta(**kwargs)

    async def test_known_cat_presence_changes_from_events(self) -> None:
        await self.hub.async_register_cat("9001", "Minka", inside=True)
        await self.hub.async_process_event("9001", "out", source="test")
        self.assertFalse(self.hub.cats["9001"].inside)

        await self.hub.async_process_event("9001", "in", source="test")
        self.assertTrue(self.hub.cats["9001"].inside)
        self.assertEqual(self.hub.last_event.direction, "in")
        self.assertTrue(self.hub.last_event.known_cat)

    async def test_unknown_chip_event_keeps_unknown_flag(self) -> None:
        event = await self.hub.async_process_event("9999", "in", source="test")
        self.assertFalse(event.known_cat)
        self.assertIsNone(event.cat_name)
        self.assertEqual(event.chip_id, "9999")
        self.assertEqual(self.hub.unknown_chip_events, 1)

    async def test_outside_today_accumulates_for_current_day(self) -> None:
        await self.hub.async_register_cat("9001", "Minka", inside=True)
        await self.hub.async_set_presence("9001", inside=False)
        self._advance(hours=1, minutes=30)

        hours_outside = self.hub.get_outside_hours_today("9001")
        self.assertAlmostEqual(hours_outside, 1.5, places=2)

        await self.hub.async_set_presence("9001", inside=True)
        self.assertAlmostEqual(self.hub.get_outside_hours_today("9001"), 1.5, places=2)

    async def test_outside_today_resets_at_midnight(self) -> None:
        await self.hub.async_register_cat("9001", "Minka", inside=False)
        self._advance(hours=1)
        self.assertAlmostEqual(self.hub.get_outside_hours_today("9001"), 1.0, places=2)

        self.now_ref["now"] = datetime(2026, 3, 13, 1, 0, tzinfo=timezone.utc)
        self.assertAlmostEqual(self.hub.get_outside_hours_today("9001"), 1.0, places=2)

    async def test_duplicate_event_is_counted_and_ignored(self) -> None:
        await self.hub.async_register_cat("9001", "Minka", inside=True)
        await self.hub.async_process_event("9001", "out", source="test")
        first_event_at = self.hub.last_event.at
        await self.hub.async_process_event("9001", "out", source="test")

        self.assertEqual(self.hub.duplicate_events, 1)
        self.assertEqual(self.hub.total_events, 1)
        self.assertEqual(self.hub.last_event.at, first_event_at)

    async def test_update_cat_changes_chip_and_name(self) -> None:
        await self.hub.async_register_cat("9001", "Minka", inside=True)
        updated = await self.hub.async_update_cat(
            old_chip_id="9001",
            new_chip_id="9002",
            name="Minka Prime",
            inside=False,
        )
        self.assertTrue(updated)
        self.assertIn("9002", self.hub.cats)
        self.assertNotIn("9001", self.hub.cats)
        self.assertEqual(self.hub.cats["9002"].name, "Minka Prime")
        self.assertFalse(self.hub.cats["9002"].inside)


if __name__ == "__main__":
    unittest.main()
