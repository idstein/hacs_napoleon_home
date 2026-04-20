# Napoleon Home — HA integration design

**Date:** 2026-04-20
**Status:** approved, ready to plan implementation
**Owner:** @idstein

## Goals

- Expose a Napoleon Connected grill (starting with a Prestige 500, `oem_model = thermometer-mqtt-eu`) as a device in Home Assistant, with read-only sensors fed by push updates.
- Work for both EU and US Napoleon Home accounts out of the box, with clean internal separation between regions (different Ayla tenants, endpoints, app credentials, property-name conventions).
- Treat "grill offline" as a healthy state — the grill is off 95 %+ of the time and only cooks for 1–2 h at a stretch. Integration must not raise errors, unload entries, or notify when the grill is off.

## Non-goals (v1)

- No control (temperature setpoints, light/knob toggles). Planned for v2.
- No fully-offline operation. MQTT-class Ayla devices don't expose the classic LAN HTTP server reliably, so v1 is cloud-dependent. LAN proxy mode is a v3 stretch.
- No Prestige-Pro / MeatStick / Woodstove / thermostat support. Property maps are stubbed so those are additive work.
- No discovery (zeroconf/DHCP). The device is offline too often for discovery to be reliable.
- No YAML config import. UI-only.

## Answered question: can it run fully offline?

No, not with this device class. `thermometer-mqtt-eu` firmware talks TLS-MQTT to `mqtt-field-eu.aylanetworks.com:8883`. The LAN HTTP protocol used by older Ayla devices (`napoleon_lan_server.py` in `skm-hikvision/`) does not work for MQTT-class devices — the device's port 80 is closed when idle and the registration endpoint times out even when it's up. The `lanip_key` fetched from the cloud is vestigial for this model.

For a truly local integration in a future version we would need to DNS-redirect the device to a HA-side MQTT broker and inject a matching TLS cert. That's invasive (Pi-hole-style DNS override + custom CA pushed to the grill during provisioning) and is explicitly out of scope for v1.

---

## §1 — Architecture

```
┌────────────────────── Home Assistant ───────────────────────────┐
│  Config entry                                                   │
│   ├─ region: "EU" | "US"                                        │
│   ├─ email, refresh_token                                       │
│   └─ devices: [{dsn, key, lanip_key, oem_model, naming}]        │
│                   │                                              │
│                   ▼                                              │
│        RegionProfile ──► picks endpoints + app_id/secret         │
│        ├─ EU:  user-field-eu, ads-eu, mqtt-field-eu             │
│        │       app_id=smarthome_eu-rA-hQ-id-5Q-id               │
│        └─ US:  user-field,    ads-field, mqtt-usfield           │
│                app_id=smarthome_dev-rA-hQ-id                    │
│                                                                 │
│        AylaAuth  ──►  AylaMqttClient  ──►  DataUpdateCoordinator│
│                           │                                      │
│                           └─ PropertyMap per oem_model           │
│                              (thermometer-mqtt-eu / pvx-* / …)  │
└─────────────────────────────────────────────────────────────────┘
```

- **Repo:** `github.com/idstein/hacs_napoleon_home`, HACS integration category, layout modeled on `idstein/hacs_esphome_dashboard`.
- **Python package:** `custom_components/napoleon/` — integration domain `napoleon`.
- **Transport:** MQTT-first (push). REST used at startup to hydrate and every 5 min as a slow safety-net for MQTT gaps.
- **IoT class:** `cloud_push`.
- **LAN:** `lanip_key` is fetched and stored but unused in v1 (v3 stretch goal).
- **Multi-device:** supports multiple devices per account, deferred model coverage per `oem_model`.
- **Minimum HA:** 2025.1. Python: 3.12+.

## §2 — Components

```
custom_components/napoleon/
├── __init__.py            # async_setup_entry / async_unload_entry
├── manifest.json          # domain=napoleon, iot_class=cloud_push,
│                          #   requirements: aiohttp, aiomqtt>=2.0
├── const.py               # DOMAIN, CONF_REGION, CONF_EMAIL,
│                          #   CONF_REFRESH_TOKEN, DEFAULT_HEARTBEAT=300
├── regions.py             # REGION_PROFILES = {"EU": {...}, "US": {...}}
├── config_flow.py         # user, reauth, options steps
├── coordinator.py         # NapoleonCoordinator (one per config entry)
├── api/
│   ├── auth.py            # AylaAuth: sign_in, refresh
│   ├── rest.py            # AylaRest: devices/properties/lan/status
│   └── mqtt.py            # AylaMqttClient: aiomqtt wrapper + reconnect
├── property_maps/
│   ├── base.py            # PropertyMap, EntityDef
│   ├── thermometer_mqtt_eu.py
│   └── unknown.py         # fallback for unknown oem_models
├── entity.py              # NapoleonEntity base class
├── sensor.py
├── binary_sensor.py
├── diagnostics.py
├── strings.json / translations/en.json
└── tests/
    ├── conftest.py
    ├── test_config_flow.py
    ├── test_coordinator.py
    └── test_sensor.py

.github/workflows/{validate,lint,test,release}.yml
hacs.json
info.md
README.md
```

**Runtime data flow:**

1. `async_setup_entry` builds `AylaAuth` → `AylaRest.devices()` → `AylaRest.properties(dsn)` → coordinator hydrated → `AylaMqttClient.connect()` + subscribe.
2. MQTT message → parse → `coordinator.ingest(dsn, partial_props)` → `async_set_updated_data()`.
3. REST heartbeat every 5 min refreshes `connection_status` per device.
4. Access-token refresh fires at `exp - 300s` and rotates the MQTT credential.
5. Refresh-token 401 → `ConfigEntryAuthFailed` → HA reauth flow.

**Entity catalog for `thermometer-mqtt-eu` (the 59 properties we already captured):**

- Temperature sensors: `PRB_TMP_ONE..FOUR` (unit from `TUNIT`).
- Target-temp sensors: parsed from `TRGT_TMP_*` JSON shape, with `{"ptr":[4095]}` → `None`.
- Tank: `TNK_WT` + derived `tank_pct` from `EMTY_TNK_W` / `F_TNKWT`; the three raw values as diagnostics.
- Signal: `RSSI` (diagnostic).
- Binary sensors: `BSMODE`, `LCD_OFF`, `TOFF`, `online` (derived from connectivity rule).
- Diagnostics: `version`, `REGN`, `CNTRY`, `GS_TNK_NAME`, `RST_CNT`, `DTYPE`, `BRT_LVL`, `BT_LVL`, `DTSPLY`.
- Alerts (non-empty = tripped): `TMP_ALRT_PRB_*`, `TMR_ALRT_PRB_*`.
- Info strings: `DEVC_NME`, `PRB_*_NME`, `CKNME_PRB_*`, `CKTIME`.

## §3 — Config flow UX

**3a. Initial setup.** Two-step: (1) region + email + password, (2) discovered-devices summary. On step 1 submit we `sign_in`, on step 2 submit we store `refresh_token` (never the password) and call `/devices.json`. If zero devices we still create the entry and raise a repair issue, rather than aborting.

Entry `unique_id = "<region>:<ayla_user_uuid>"` to block duplicates.

**3b. Reauth.** Triggered by `ConfigEntryAuthFailed`. Region and email shown read-only; only asks for the new password. Different email → `reauth_email_mismatch` error (account changes require delete-and-re-add).

**3c. Options.** Just two knobs: heartbeat interval (default 300 s, clamp 60–3600) and diagnostic logging toggle.

**3d. Error strings:** `invalid_auth`, `cannot_connect`, `unknown_region`, `reauth_email_mismatch`, `no_devices` (repair issue, not blocking).

## §4 — Data flow & edge cases

**4a. Startup.** Under ~1 s to first render: auth → REST hydrate → coordinator publish → MQTT connect → background heartbeat scheduling.

**4b. MQTT topics.** Exact topic strings confirmed during implementation by a one-session capture. Logical shape:

- `ayla/{dsn}/property/update` — single datapoint.
- `ayla/{dsn}/property/batch` — bulk update at grill wake.
- `ayla/{dsn}/connectivity` — `{"state":"online"|"offline"}`.

Handler is a pure merge; bad payloads log once at warning and are dropped.

**4c. Token refresh.** Scheduled at `exp − 300 s`. On 401 during REST, one retry after refresh, then escalate to `ConfigEntryAuthFailed`. Never refresh synchronously inside a REST call.

**4d. MQTT reconnect.** Exponential 1/2/5/15/60 s backoff, capped. Deterministic `clientid = ha-napoleon-{entry_id}`. Logs first attempt at INFO, rest at DEBUG. `mqtt_connected` binary sensor exposes the state for user-level notifications.

**4e. Grill-offline semantics.** `connectivity[dsn] = online` iff any of:

- latest MQTT connectivity = online, OR
- any property update within last 90 s, OR
- last REST `connection_status` = Online.

When offline: grill-state entities go `UNAVAILABLE`, diagnostic entities stay available with last known values, `online` binary sensor = off, no log, no notification. Coordinator never raises `UpdateFailed` for offline.

**4f. Notable edges.**

| Situation | Behavior |
| --- | --- |
| No device on account yet | Setup succeeds, repair issue; reloadable |
| Two grills on one account | Both appear, separate device_registry entries |
| EU + US accounts | Two independent config entries |
| Unknown `oem_model` | `unknown.py` exposes all props as raw diagnostics + single warning |
| Stale hydrate when grill off for weeks | Connectivity rule immediately marks UNAVAILABLE |
| Value type mismatch | `value_fn` coerces; exception → `None` + one warn per entity |
| Clock skew on `updated_at` | Ignored; arrival time used |
| User changes Ayla password | Refresh → 401 → reauth |
| HA restart | `refresh_token` drives silent resume |
| Device factory reset | `lan_config` fetch 404s once; no functional impact v1 |
| `TRGT_TMP_FOUR = {"ptr":[4095]}` | Parsed as "no target set" → `None` |

## §5 — Testing & CI

**5a. Tests (pytest-homeassistant-custom-component).**

- Pure logic: `test_property_maps`, `test_auth`, `test_regions`, `test_coordinator_availability` (table-driven against the connectivity rule).
- I/O mocks: `test_rest` (aiohttp_client_mock: 200/401/404/500/timeout), `test_mqtt` (fake broker: subscribe list, handler dispatch, reconnect backoff, token rotation).
- Full HA fixture: `test_config_flow` (all 5 error codes + dup rejection), `test_setup_entry` (setup/unload/reload), `test_grill_offline` (the key smoke test: offline → UNAVAILABLE → online → repopulate, asserts `UpdateFailed` never raised).

Target: ≥90 % line coverage on `api/` + `coordinator.py`, ≥80 % overall, CI-enforced.

Fixtures: `mock_ayla_rest` (FakeRest preloaded with the real 59-property dump, scrubbed), `mock_mqtt` (`MockMqtt.publish_device_message(dsn, prop, value)`), `real_property_fixture.json` (anonymized real capture).

**5b. CI (`.github/workflows/`).**

- `validate.yml` — `hacs/action@main` (category: integration) + `home-assistant/actions/hassfest@master`.
- `lint.yml` — `ruff check .`, `ruff format --check .`, `mypy --strict custom_components/napoleon`.
- `test.yml` — matrix `python-version: [3.12, 3.13]`, `pytest --cov --cov-fail-under=90`.
- `release.yml` — on tag `v*`, zip `custom_components/napoleon/` and attach to GH release.

**5c. Post-install smoke test** (manual, one run after first release): install via HACS custom repo, run through config flow, power grill on & probe 4, verify sensor updates <2 s after MQTT message, power off & verify UNAVAILABLE within 2 min with no errors, HA restart to confirm silent resume. Checklist goes into README "Is it working?" section.

## Open questions / followups

- Confirm exact MQTT topic strings by sniffing one session during implementation; the design is indifferent to the exact strings but the test fixtures need to match.
- If Ayla EU's MQTT broker requires a non-token password (e.g. HMAC-signed credential derived from app_id/app_secret and token), auth.py will need an extra step. Will verify empirically first — but based on the Ayla SDK pattern it's expected to be just the access_token as password.
- Rotate the Ayla account password before publishing any commit that mentions it; the repo will never contain the real password, only a placeholder in docs.
