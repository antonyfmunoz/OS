# C31 Phase 2C Report — Boundary Enforcement + Adapter Engine Wiring

**Date:** 2026-06-29
**Branch:** worktree-c31-phase2c
**Scope:** Close the substrate→adapters checker gap + connect the adapter engine to production.

---

## 1. Dependency Boundary Enforcement

### New Rule Added

`check_dependency_direction.py` now detects `substrate/ → adapters/` imports (both `from adapters` and `import adapters` patterns).

**Before:** Only substrate→transports and substrate→services enforced. 112 substrate→adapters violations completely invisible.

**After:** All three upward import directions enforced: substrate→transports, substrate→services, substrate→adapters.

### Legacy Allowlist

56 files with existing substrate→adapters imports grandfathered into `LEGACY_VIOLATIONS`. These are tech debt to be migrated via contracts/ports in future phases.

3 additional test files with substrate→transports imports also grandfathered (integration tests crossing boundaries by design).

**Full scan result:** `1270 files scanned — clean. Legacy violations grandfathered: 70 files (tech debt)`

Any NEW substrate→adapters import will now be blocked at commit time.

---

## 2. Adapter Engine Wiring

### `__init__.py` Populated

`adapters/adapter_engine/__init__.py` now exports all public types:
- `AdapterManifest`, `AdapterMaturityLevel`
- `MaturityEvidence`, `compute_adapter_maturity`
- `AdapterDescriptor`, `AdapterRegistry`, `CapabilityDescriptor`
- `ModalityType`, `ParticipantType`
- `ALL_PRODUCTION_MANIFESTS`, `populate_production_registry`

### Production Manifests Created

4 adapter manifests in `adapters/adapter_engine/production_manifests.py`:

| Adapter | Type | Maturity | Capabilities |
|---------|------|----------|-------------|
| `model_router` | ai_routing | L3_TESTED | ai_inference, ai_heavy_inference |
| `cc_sdk` | claude_code | L2_CAPABILITIES_KNOWN | claude_code_query |
| `google_workspace` | google_workspace | L2_CAPABILITIES_KNOWN | email_read, email_send, drive_scan |
| `calendar` | calendar | L2_CAPABILITIES_KNOWN | calendar_read, calendar_write |

### Status Endpoint

New route at `GET /api/umh/adapters/status` via `cockpit_adapter_status_routes.py`.

Returns:
```json
{
  "adapter_count": 4,
  "adapters": [
    {
      "adapter_id": "model_router",
      "adapter_type": "ai_routing",
      "capabilities": ["ai_inference", "ai_heavy_inference"],
      "modalities": ["api"],
      "participant_type": "external",
      "version": "v1"
    }
  ]
}
```

Registry populated lazily on first request via `populate_production_registry()`.

---

## 3. Verification

| Check | Result |
|-------|--------|
| `check_dependency_direction.py --all` | **1270 files clean** (70 legacy grandfathered) |
| `py_compile` (all 5 new/modified files) | **All pass** |
| `tests/substrate/` | **70/70 passed** |
| `tests/adapters/` | **50/50 passed** |
| Registry population test | **4 adapters, 8 capabilities registered** |

---

## 4. Files Changed

| File | Change |
|------|--------|
| `scripts/check_dependency_direction.py` | Add substrate→adapters rule + 59 legacy entries |
| `adapters/adapter_engine/__init__.py` | Populate with real exports |
| `adapters/adapter_engine/production_manifests.py` | **NEW** — 4 production manifests |
| `transports/api/cockpit_adapter_status_routes.py` | **NEW** — /api/umh/adapters/status |
| `transports/api/cockpit.py` | Mount adapter status router |

---

## 5. What This Does NOT Do

- Does not move the 56 legacy substrate→adapters imports — those are grandfathered for now
- Does not rewrite model routing or any adapter internals
- Does not add maturity evidence collection (execution tracking) — that's Phase 4
- Does not create manifests for unused adapters (ssh, tailscale, notion, scrapling)
- Adapter status is read-only observability — no control surface yet
