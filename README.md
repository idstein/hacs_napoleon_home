# Napoleon Home — Home Assistant integration

Custom HACS integration for Napoleon Connected grills (Prestige 500 and other Ayla-based models).

> **Status:** design stage. See [`docs/plans/2026-04-20-napoleon-ha-integration-design.md`](docs/plans/2026-04-20-napoleon-ha-integration-design.md).

## What it does (v1)

- Subscribes to Napoleon Home cloud MQTT (Ayla EU / US regions) and exposes grill telemetry as Home Assistant sensors.
- Read-only in v1: probe temperatures, tank weight, firmware, connection state, alerts.
- Offline-aware: the grill is expected to be offline most of the time. Sensors go `unavailable` quietly, no errors.

## What it does not do (yet)

- No control (setting target temps, toggling lights/knobs) — planned for v2.
- No fully-offline operation — the current `thermometer-mqtt-eu` firmware class requires Ayla cloud reachability. LAN-only mode is a v3 stretch goal.
- No Prestige-Pro or MeatStick support yet — the property map is there, just empty.

## Install

HACS custom repository:

1. HACS → Integrations → ⋮ → *Custom repositories*
2. Repository: `https://github.com/idstein/hacs_napoleon_home` — Category: *Integration*
3. Install, restart Home Assistant, add the Napoleon integration from the UI.

## Region support

EU and US Napoleon Home accounts are separate Ayla tenants with different endpoints, app IDs, and property-name conventions. Pick your region at setup. Both are supported from v1, but only `thermometer-mqtt-eu` firmware is field-tested — US hardware (`pvx-field-us`) support ships with a scaffolded property map that will need a contributor with a US grill to complete.
