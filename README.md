# ESP32 Cat Flap for Home Assistant

A DIY smart cat flap system built with an ESP32 that detects RFID pet microchips and integrates with Home Assistant via ESPHome.

The system identifies which cat enters or leaves through the flap and logs the direction (entry/exit). Each cat can be tracked individually inside Home Assistant.

## Features

- RFID pet microchip detection (ISO 11784/11785 – typical pet chips)
- Entry and exit direction detection using distance sensors
- Integration with Home Assistant via ESPHome
- Individual tracking for multiple cats
- Event logging for flap usage
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
- Sending events to Home Assistant

**Home Assistant Integration**  
Processes the events and manages:
- Cat profiles (name + chip ID)
- Cat presence status (inside / outside)
- History and automations

## Project Goals

- Open-source alternative to commercial smart cat flaps
- Fully local and privacy-friendly
- Reliable multi-cat detection
- Easy integration with Home Assistant

## Status

Work in progress.
