# Wiring

## ESP32 Pins Used

- `GPIO21` -> I2C SDA (VL53L0X front + back SDA)
- `GPIO22` -> I2C SCL (VL53L0X front + back SCL)
- `GPIO16` -> UART RX (connect RFID module TX here)
- `GPIO17` -> UART TX (optional, connect to RFID RX if needed)
- `3V3` -> VL53L0X VCC
- `GND` -> common ground for ESP32 + RFID + both ToF sensors

## VL53L0X

- Front sensor:
  - SDA -> GPIO21
  - SCL -> GPIO22
  - Address expected by config: `0x29`
- Back sensor:
  - SDA -> GPIO21
  - SCL -> GPIO22
  - Address expected by config: `0x30`

Address note:

- Default VL53L0X address is `0x29` for both.
- You must set one sensor to `0x30` (typically via XSHUT sequencing) or use an I2C multiplexer.

## RFID UART

- RFID `TX` -> ESP32 `GPIO16` (RX)
- RFID `RX` -> ESP32 `GPIO17` (TX) (optional, depends on module)
- RFID `GND` -> ESP32 `GND`
- RFID `VCC` -> module-specific supply (often `5V`)

Voltage safety:

- ESP32 GPIO is 3.3V logic.
- If RFID TX is 5V TTL, use a level shifter/divider into GPIO16.

## Practical Checks Before Flashing

1. Confirm both VL53L0X sensors are discoverable on I2C and not colliding.
2. Confirm RFID serial settings match ESPHome (`9600 8N1` by default in this repo).
3. Keep all grounds tied together.
