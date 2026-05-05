# Bridge Healthcheck — VPS Checklist v1

**Date**: 2026-05-04
**Phase**: 94R — Existing Local Bridge Healthcheck + Work Order Dispatch Readiness v1
**Purpose**: Verify all VPS-side prerequisites for dispatching Work Order 001 to the local PC worker.

---

## Instructions

Run each check from the VPS (`/opt/OS`). Mark PASS / FAIL / UNKNOWN / NEEDS_LOCAL_VERIFICATION.
All checks marked CRITICAL must PASS before any dispatch attempt.

---

## Check 1 — Bridge Client File Exists

| Field | Value |
|-------|-------|
| **Priority** | CRITICAL |
| **Command** | `ls -la /opt/OS/services/local_bridge_client.py` |
| **Expected** | File exists, 4119 bytes |
| **Result** | **PASS** — file exists (4119 bytes, dated 2026-04-27) |
| **Why** | VPS dispatches work orders through this client |

---

## Check 2 — Bridge Server File Exists (VPS copy)

| Field | Value |
|-------|-------|
| **Priority** | HIGH |
| **Command** | `ls -la /opt/OS/services/local_bridge_server.py` |
| **Expected** | File exists |
| **Result** | **PASS** — file exists (8024 bytes, dated 2026-04-27) |
| **Why** | Reference copy — local PC must have a matching version |

---

## Check 3 — Webhook Receiver File Exists

| Field | Value |
|-------|-------|
| **Priority** | CRITICAL |
| **Command** | `ls -la /opt/OS/services/cc_webhook_receiver.py` |
| **Expected** | File exists |
| **Result** | **PASS** — file exists (8410 bytes, dated 2026-04-27) |
| **Why** | Receives results from local worker via POST /cc-reply and /cc-prompt |

---

## Check 4 — Work Order Contract File Exists

| Field | Value |
|-------|-------|
| **Priority** | CRITICAL |
| **Command** | `ls -la /opt/OS/eos_ai/substrate/work_order_contracts.py` |
| **Expected** | File exists |
| **Result** | **PASS** — file exists (10788 bytes, dated 2026-05-04) |
| **Why** | Defines WorkOrder, WorkOrderResult, status enums, transition enforcement |

---

## Check 5 — Work Order Factory File Exists

| Field | Value |
|-------|-------|
| **Priority** | CRITICAL |
| **Command** | `ls -la /opt/OS/eos_ai/substrate/work_order_factory.py` |
| **Expected** | File exists |
| **Result** | **PASS** — file exists (6267 bytes, dated 2026-05-04) |
| **Why** | Factory builds pre-configured work orders with all blocked actions enforced |

---

## Check 6 — Work Order Contract Importable

| Field | Value |
|-------|-------|
| **Priority** | CRITICAL |
| **Command** | `python3 -c "import sys; sys.path.insert(0,'/opt/OS'); from eos_ai.substrate.work_order_contracts import WorkOrder, WorkOrderStatus; print('OK')"` |
| **Expected** | Prints `OK` |
| **Result** | **PASS** — imports clean, 16/16 tests passing |
| **Why** | Code contracts must be importable before any dispatch logic is built |

---

## Check 7 — Work Order Factory Builds GWS Discovery Order

| Field | Value |
|-------|-------|
| **Priority** | CRITICAL |
| **Command** | `python3 -c "import sys; sys.path.insert(0,'/opt/OS'); from eos_ai.substrate.work_order_factory import create_google_workspace_discovery_work_order, validate_work_order; wo = create_google_workspace_discovery_work_order(); print(validate_work_order(wo))"` |
| **Expected** | Prints `[]` (empty list = no validation errors) |
| **Result** | **PASS** — factory builds valid work order with 14 source targets, 16 blocked actions |
| **Why** | The dispatch package depends on a valid factory-built work order |

---

## Check 8 — Work Order 001 Document Exists

| Field | Value |
|-------|-------|
| **Priority** | CRITICAL |
| **Command** | `ls -la /opt/OS/docs/operations/local_google_workspace_ingestion_work_order_001.md` |
| **Expected** | File exists |
| **Result** | **PASS** — file exists (11212 bytes, dated 2026-05-04) |
| **Why** | Human-readable work order specification for founder review |

---

## Check 9 — Result Schema Exists

| Field | Value |
|-------|-------|
| **Priority** | CRITICAL |
| **Command** | `ls -la /opt/OS/docs/operations/local_google_workspace_ingestion_result_schema_v1.md` |
| **Expected** | File exists |
| **Result** | **PASS** — file exists (8986 bytes, dated 2026-05-04) |
| **Why** | Local worker must know the required result format |

---

## Check 10 — Bridge Env Vars Configured

| Field | Value |
|-------|-------|
| **Priority** | CRITICAL |
| **Command** | `grep LOCAL_BRIDGE /opt/OS/eos_ai/.env \| grep -c '='` |
| **Expected** | 3 (ENABLED, IP, PORT) |
| **Result** | **PASS** — `EOS_LOCAL_BRIDGE_ENABLED=1`, `EOS_LOCAL_BRIDGE_IP=100.74.199.102`, `EOS_LOCAL_BRIDGE_PORT=8766` in both `.env` files |
| **Why** | Bridge client reads these at import time |

---

## Check 11 — Binding Plan Exists

| Field | Value |
|-------|-------|
| **Priority** | HIGH |
| **Command** | `ls -la /opt/OS/docs/operations/existing_bridge_binding_plan_v1.md` |
| **Expected** | File exists |
| **Result** | **PASS** — file exists (11261 bytes, dated 2026-05-04) |
| **Why** | Documents how work orders flow through the bridge |

---

## Check 12 — Local Healthcheck Checklist Exists

| Field | Value |
|-------|-------|
| **Priority** | HIGH |
| **Command** | `ls -la /opt/OS/docs/operations/local_worker_healthcheck_checklist_v1.md` |
| **Expected** | File exists |
| **Result** | **PASS** — file exists (7590 bytes, dated 2026-05-04) |
| **Why** | Founder needs this checklist to verify local PC readiness |

---

## Check 13 — No Duplicate Bridge Being Created

| Field | Value |
|-------|-------|
| **Priority** | HIGH |
| **Command** | `grep -r "dispatch_work_order" /opt/OS/services/ 2>/dev/null \| wc -l` |
| **Expected** | 0 — no dispatch_work_order() exists yet in services/ |
| **Result** | **PASS** — function does not exist yet (Phase 94L will add it) |
| **Why** | Phase 94R prepares but does not modify bridge files |

---

## Check 14 — No Credentials Printed in Work Order

| Field | Value |
|-------|-------|
| **Priority** | HIGH |
| **Command** | `python3 -c "import sys,json; sys.path.insert(0,'/opt/OS'); from eos_ai.substrate.work_order_factory import create_google_workspace_discovery_work_order, work_order_to_bridge_payload; p=work_order_to_bridge_payload(create_google_workspace_discovery_work_order()); [print('FAIL: credential in payload') for k in ['password','token','secret','api_key','credential'] if k in json.dumps(p).lower()] or print('OK: no credentials')"` |
| **Expected** | `OK: no credentials` |
| **Result** | **PASS** — payload contains no credential strings |
| **Why** | Work order contract forbids credential capture |

---

## Check 15 — No External Account Access from VPS

| Field | Value |
|-------|-------|
| **Priority** | CRITICAL |
| **Command** | N/A — attestation check |
| **Expected** | This phase does not connect to Google, Instagram, or any external account |
| **Result** | **PASS** — Phase 94R is documentation + code preparation only |
| **Why** | External account access is scope of Phase 94L on the local machine |

---

## Check 16 — Tailscale Target IP Documented

| Field | Value |
|-------|-------|
| **Priority** | HIGH |
| **Command** | `grep '100.74.199.102' /opt/OS/services/LOCAL_BRIDGE_SETUP.md` |
| **Expected** | IP appears in documentation |
| **Result** | **PASS** — IP documented in LOCAL_BRIDGE_SETUP.md, env vars, and bridge_binding_plan |
| **Why** | Dispatch path requires known Tailscale IP |

---

## Check 17 — VPS Can Attempt Bridge Health Check

| Field | Value |
|-------|-------|
| **Priority** | HIGH |
| **Command** | `python3 -c "import sys; sys.path.insert(0,'/opt/OS'); from services.local_bridge_client import bridge_status; print(bridge_status())"` |
| **Expected** | Returns dict with `enabled: True`. `healthy` may be True or False depending on local PC state. |
| **Result** | **NEEDS_LOCAL_VERIFICATION** — bridge is enabled but local PC must be online and running bridge server |
| **Why** | Dispatch will fail gracefully if local is unhealthy — this is expected before local healthcheck |

---

## Summary Table

| # | Check | Priority | Status |
|---|-------|----------|--------|
| 1 | Bridge client file exists | CRITICAL | PASS |
| 2 | Bridge server file exists (VPS copy) | HIGH | PASS |
| 3 | Webhook receiver file exists | CRITICAL | PASS |
| 4 | Work order contract file exists | CRITICAL | PASS |
| 5 | Work order factory file exists | CRITICAL | PASS |
| 6 | Work order contract importable | CRITICAL | PASS |
| 7 | Factory builds valid GWS work order | CRITICAL | PASS |
| 8 | Work order 001 document exists | CRITICAL | PASS |
| 9 | Result schema exists | CRITICAL | PASS |
| 10 | Bridge env vars configured | CRITICAL | PASS |
| 11 | Binding plan exists | HIGH | PASS |
| 12 | Local healthcheck checklist exists | HIGH | PASS |
| 13 | No duplicate bridge being created | HIGH | PASS |
| 14 | No credentials in work order payload | HIGH | PASS |
| 15 | No external account access from VPS | CRITICAL | PASS |
| 16 | Tailscale target IP documented | HIGH | PASS |
| 17 | VPS can attempt bridge health check | HIGH | NEEDS_LOCAL_VERIFICATION |

**VPS readiness**: 16/17 PASS, 1/17 NEEDS_LOCAL_VERIFICATION
**Gate**: All CRITICAL checks PASS. Remaining check requires local PC to be online.
