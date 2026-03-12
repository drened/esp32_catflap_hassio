# ESP32 Cat Flap for Home Assistant

A DIY smart cat flap system built with an ESP32 that detects RFID pet microchips and integrates with Home Assistant via ESPHome.

The system identifies which cat enters or leaves through the flap and logs the direction (entry/exit). Each cat can be tracked individually inside Home Assistant.

## Features

- Home Assistant custom integration (`catflap`)
- Persistent cat registry (`chip_id`, `name`, `inside`)
- Event ingestion service for ESPHome/device events
- Inside/outside tracking per registered cat
- Event sensors (`last direction`, `last chip`, `last event time`, `last cat`)
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

1. Copy `homeassistant/custom_components/catflap` to your Home Assistant `custom_components` folder.
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

## ESPHome Test

`esphome/catflap.yaml` contains two template buttons:

- `Simulate Cat IN`
- `Simulate Cat OUT`

Before flashing:

1. Replace `catflap_entry_id` in `esphome/catflap.yaml` with your Home Assistant integration entry id.
2. Adjust `test_chip_id` to a real chip for end-to-end tests.

## Project Goals

- Open-source alternative to commercial smart cat flaps
- Fully local and privacy-friendly
- Reliable multi-cat detection
- Easy integration with Home Assistant

## Status

MVP integration available, hardware logic still in progress.
