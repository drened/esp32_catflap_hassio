
# Architecture

## Components

1. ESP32 with ESPHome
2. Home Assistant custom integration (`custom_components/catflap`)

## Data Flow

1. ESP32 detects a cat chip and direction (`in`/`out`).
2. ESPHome calls Home Assistant service `catflap.process_event`.
3. Integration updates:
   - last flap event
   - per-cat inside/outside state (for known cats)
4. Entities update in Home Assistant via dispatcher signals.

## Persistence

- Runtime state is stored per config entry in Home Assistant storage.
- Persisted data:
  - known cats (`chip_id`, `name`, `inside`)
  - last event (`chip_id`, `direction`, `timestamp`, metadata)

## Entities

- Sensors:
  - last direction
  - last chip
  - last known cat
  - last event timestamp
  - registered cat count
- Binary sensors:
  - flap activity (recent event in last 30s)
  - dynamic `Inside` sensor for each registered cat
