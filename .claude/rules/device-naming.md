# Device Naming Protocol

NEVER hardcode device display names as raw strings in any file.
Not "VPS", not "Beast", not "Beast PC", not "Windows", not "Server".

Format: `tailscale-hostname (device-type)` — e.g. `srv1500858 (VPS)`

Single source of truth: `infra/device_registry.json`

- **Frontend**: import from `cockpit/src/renderer/constants/devices.ts`
  — use `VPS.displayName`, `BEAST.displayName`, `getDeviceDisplayName(id)`
- **Backend**: read from `infra/device_registry.json`
- **API**: `/workspace/mesh-nodes` returns canonical names

Adding a new device:
1. Add entry to `infra/device_registry.json`
2. Add constant to `cockpit/src/renderer/constants/devices.ts`
3. All UI surfaces pick it up automatically
