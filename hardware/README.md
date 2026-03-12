
# Hardware Overview

Current MVP hardware stack:

- ESP32 DevKit (ESP32-WROOM recommended)
- RFID reader with UART output (for pet chip IDs)
- 2x VL53L0X ToF sensors:
  - `front` sensor
  - `back` sensor
- Stable power supply (USB or 5V PSU with common ground)

The ESPHome config in this repo expects:

- I2C bus on `GPIO21` (SDA) and `GPIO22` (SCL)
- RFID UART on `GPIO16` (RX) and `GPIO17` (TX)
- Two VL53L0X addresses:
  - front: `0x29`
  - back: `0x30`

Important:

- Two VL53L0X modules cannot both stay on `0x29`.
- Set the second module to `0x30` via XSHUT boot/address routine, or use a dedicated I2C multiplexer.
- If your RFID reader outputs 5V UART, level-shift into ESP32 RX (3.3V logic safe).
