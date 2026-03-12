# ESP32 Cat Flap Addon for Home Assistant

A DIY addon for cat flap systems built with an ESP32 that detects RFID pet microchips and integrates with Home Assistant via ESPHome.

The system identifies which cat enters or leaves through the flap and logs the direction (entry/exit). Each cat can be tracked individually inside Home Assistant.

## Features

- Home Assistant custom integration (`catflap`)
- Persistent cat registry (`chip_id`, `name`, `inside`)
- Event ingestion service for ESPHome/device events
- Duplicate event suppression (configurable)
- Inside/outside tracking per registered cat
- Per-cat sensor: `Outside Today` (hours)
- Event sensors (`last direction`, `last chip`, `last event time`, `last cat`)
- Diagnostic sensors (`total events`, `duplicates`, `unknown chip/direction`)
- Fully local operation (no cloud required)

## Hardware

Planned hardware components:

- ESP32
- RFID reader for 134.2 kHz pet microchips
- 2x VL53L0X time-of-flight distance sensors
- Cat flap tunnel housing

## Software Architecture

The system consists of two main parts:

**ESP32 (ESPHome)**  
Handles sensor reading and detection logic:
- RFID chip reading
- Direction detection (entry / exit)
- Sending events to Home Assistant service `catflap.process_event`

**Home Assistant Integration**  
Processes the events and manages:
- Cat profiles (name + chip ID)
- Cat presence status (inside / outside)
- History and automations

## Setup

1. Copy `custom_components/catflap` to your Home Assistant `custom_components` folder.
2. Restart Home Assistant.
3. Add integration: `Settings -> Devices & Services -> Add Integration -> ESP32 Cat Flap`.
4. Set a flap name.

## Services

- `catflap.register_cat`
  - `chip_id` (required)
  - `name` (required)
  - `inside` (optional, default: `false`)
  - `entry_id` (optional if only one cat flap integration exists)
- `catflap.remove_cat`
  - `chip_id` (required)
  - `entry_id` (optional if only one integration exists)
- `catflap.set_presence`
  - `chip_id` (required)
  - `inside` (required)
  - `entry_id` (optional if only one integration exists)
- `catflap.process_event`
  - `chip_id` (required)
  - `direction` (required: `in`, `out`, `unknown`)
  - `source` (optional)
  - `entry_id` (optional if only one integration exists)

You can also manage cats from the integration UI:

1. Open `Settings -> Devices & Services`.
2. Open `ESP32 Cat Flap`.
3. Click `Configure`.
4. Use `Add cat`, `Remove cat`, or `Set presence`.
5. Use `Edit cat` to rename/change chip ID.
6. Use `Settings` to tune duplicate-filter and activity windows.

## ESPHome Test

`esphome/catflap.yaml` contains two template buttons:

- `Simulate RFID Read`
- `Simulate Cat IN`
- `Simulate Cat OUT`

Before flashing:

1. Replace `catflap_entry_id` in `esphome/catflap.yaml` with your Home Assistant integration entry id.
2. Adjust `test_chip_id` to a real chip for end-to-end tests.

For real RFID wiring, set the chip id in ESPHome when a reader event arrives:

- Call ESPHome service `esphome.catflap_set_chip_id` with `chip_id`.
- Direction is derived from ToF sequence (`front -> back` = `in`, `back -> front` = `out`).

## Outside Duration Per Day

The integration provides this directly:

- Dynamic sensor per cat: `<Flap Name> <Cat Name> Outside Today`
- Unit: hours (`h`)
- Auto reset at local midnight

## Project Goals

- Open-source alternative to commercial smart cat flaps
- Fully local and privacy-friendly
- Reliable multi-cat detection
- Easy integration with Home Assistant

## Status

MVP integration available, hardware logic still in progress.

## Tests

Run hub logic tests locally:

```powershell
python -m unittest -v tests/test_hub.py
```

## Releases

- Version history: `CHANGELOG.md`
