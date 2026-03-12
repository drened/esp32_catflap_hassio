# Changelog

## 0.1.7 - 2026-03-12

- Added options-flow actions to edit cats (rename and chip ID change).
- Added behavior settings in options flow:
  - duplicate event window
  - activity sensor window
- Added duplicate-event suppression in hub logic.
- Added diagnostic counters:
  - total events
  - dropped duplicates
  - unknown chip events
  - unknown direction events
- Added `catflap.update_cat` service.
- Improved entity presentation with more diagnostic categorization.
- Tightened ESPHome UART payload validation to reduce false reads.
- Added initial hub unit tests for dedupe and cat update behavior.
