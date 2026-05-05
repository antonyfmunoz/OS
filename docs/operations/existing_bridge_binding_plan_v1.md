# Existing Bridge Binding Plan v1

**Date**: 2026-05-04
**Phase**: 93R.1 — Bind Existing Local Bridge to Work Order Contract v1
**Purpose**: Map the formal work-order contract onto the discovered VPS ↔ local bridge infrastructure.

---

## Confidence Legend

| Tag | Meaning |
|-----|---------|
| CONFIRMED | Code exists, tested or documented |
| LIKELY | Strong evidence from code, needs verification |
| UNKNOWN | Cannot determine from VPS-side |
| NEEDS_LOCAL_VERIFICATION | Must be confirmed on local machine |
| DO_NOT_TOUCH | Existing production system — do not modify |

---

## 1. Which Existing Files Are Used

### Primary transport: Local Bridge (System A)

| File | Role in work-order flow | Modification needed | Status |
|------|------------------------|---------------------|--------|
| `services/local_bridge_client.py` | VPS → local dispatch. Add `dispatch_work_order()` alongside existing `forward_to_local()`. | ADD function, do not modify existing | CONFIRMED |
| `services/local_bridge_server.py` | Local receiver. Add `/work-order` endpoint alongside existing `/message`. | ADD endpoint, do not modify existing | CONFIRMED |
| `services/cc_webhook_receiver.py` | VPS result receiver. Add `/work-order-result` endpoint alongside existing `/cc-reply`. | ADD endpoint, do not modify existing | CONFIRMED |
| `services/local_bridge_send_to_discord.sh` | Reply hook. No change needed — work order results use their own endpoint. | NONE | DO_NOT_TOUCH |
| `services/LOCAL_BRIDGE_SETUP.md` | Documentation. Append work-order setup section. | APPEND section | CONFIRMED |

### Secondary transport: Station Bus (System B)

| File | Role | Modification needed | Status |
|------|------|---------------------|--------|
| `eos_ai/substrate/station_bus.py` | File bus. Can carry work orders as a new message type alongside SafeAction. | NONE for now — use HTTP bridge first | DO_NOT_TOUCH |
| `eos_ai/substrate/station_daemon.py` | Daemon. Could gain a work-order handler. | NONE for now — work orders flow through bridge, not daemon | DO_NOT_TOUCH |
| `eos_ai/substrate/control_bridge.py` | Command queue. Work orders could be wrapped in ControlCommand. | NONE for now | DO_NOT_TOUCH |

### New additive files

| File | Role | Status |
|------|------|--------|
| `eos_ai/substrate/work_order_contracts.py` | Enums + dataclasses for WorkOrder, WorkOrderResult | NEW — additive |
| `eos_ai/substrate/work_order_factory.py` | Factory functions for creating typed work orders | NEW — additive |
| `tests/test_phase93r1_work_order_contracts.py` | Contract validation tests | NEW — additive |

---

## 2. Which Queue/Bus Mechanism Carries Work Orders

### Recommended: Local Bridge HTTP (Primary)

**Why HTTP over file bus:**
- Local bridge is already health-check-gated (graceful degradation)
- Bidirectional HTTP is simpler than file sync
- Work orders are JSON — same as existing `/message` payload
- No need to resolve the file bus VPS↔local sync question
- Result writeback via new `/work-order-result` endpoint closes the loop

**Transport flow:**

```
VPS: create_work_order()
  → work_order_contracts.WorkOrder.to_dict()
  → local_bridge_client.dispatch_work_order(wo_dict)
    → GET /health (2s timeout)
    → If healthy: POST /work-order with JSON payload
    → If unhealthy: queue locally, retry on next health check

LOCAL: /work-order endpoint receives JSON
  → Validates work order structure
  → Writes to ~/eos_work_orders/{work_order_id}.json
  → Returns 200 with {"claimed": True}
  → Local worker (human or AI session) reads from inbox

RESULT: Local worker completes
  → POST /work-order-result to VPS (100.77.233.50:8765)
  → VPS writes result to docs/operations/results/
  → VPS updates work order status to COMPLETE/PARTIAL/FAILED
```

### Fallback: Station Bus File Bus (if HTTP bridge unavailable)

Write work order to `eos_ai/.substrate_station/antony-workstation.outbox.json` with `"type": "work_order"`. Station daemon would need a new handler to process it. Deferred — use HTTP bridge first.

**Confidence**: CONFIRMED (HTTP path) / LIKELY (file bus fallback)

---

## 3. Where Work Orders Are Created on VPS

| Location | Purpose | Confidence |
|----------|---------|-----------|
| `docs/operations/` | Human-readable work order documents (like work_order_001.md) | CONFIRMED |
| `eos_ai/.substrate_station/work_orders/` | Machine-readable JSON work orders for dispatch | NEW — create directory |
| `eos_ai/substrate/work_order_factory.py` | Programmatic creation via factory functions | NEW — additive code |

### Work order lifecycle on VPS

1. **Author**: Write human-readable `.md` in `docs/operations/`
2. **Build**: Use `work_order_factory.py` to create machine-readable JSON
3. **Queue**: Write JSON to `eos_ai/.substrate_station/work_orders/{id}.json`
4. **Dispatch**: `local_bridge_client.dispatch_work_order()` sends to local
5. **Track**: Update status in the JSON file as transitions occur
6. **Result**: Store in `docs/operations/results/{id}_result.json`

---

## 4. Where Local Worker Claims/Reads Work Orders

| Location | Purpose | Confidence |
|----------|---------|-----------|
| `~/eos_work_orders/` | Local inbox directory for received work orders | NEEDS_LOCAL_VERIFICATION |
| HTTP `/work-order` endpoint | Receives and writes work orders to local inbox | NEEDS_LOCAL_VERIFICATION (endpoint not yet added) |

### Claim flow

1. Work order arrives via POST to local bridge
2. Local bridge server writes to `~/eos_work_orders/{work_order_id}.json`
3. Local bridge server returns `{"claimed": True, "work_order_id": "..."}`
4. VPS updates status to `CLAIMED_BY_LOCAL`
5. Founder or local AI session reads from `~/eos_work_orders/`
6. Execution begins (status → `IN_PROGRESS`)

**Confidence**: LIKELY — follows existing `~/eos_inbox/` pattern from `local_bridge_server.py`

---

## 5. Where Results Are Written Back

| Location | Purpose | Confidence |
|----------|---------|-----------|
| VPS: `docs/operations/results/{id}_result.json` | Structured result storage | NEW — create directory |
| VPS: `/work-order-result` endpoint | HTTP receiver for result POST | NEW — add to cc_webhook_receiver.py |
| Local: `~/eos_work_orders/{id}_result.json` | Local copy of result before sending | LIKELY |

### Writeback flow

1. Local worker writes result JSON to `~/eos_work_orders/{id}_result.json`
2. Local worker POSTs result to `http://100.77.233.50:8765/work-order-result`
3. VPS webhook receiver writes to `docs/operations/results/{id}_result.json`
4. VPS updates work order status to `COMPLETE` / `PARTIAL` / `FAILED`
5. VPS notifies founder via Discord (using existing channel routing)

**For binary evidence (screenshots, exports):**
- Use `tailscale file cp` to transfer files to VPS
- Or encode as base64 in result JSON (for small files <100KB)
- Deferred to Phase 94L — first work order will produce text-only results

---

## 6. How Approval Gates Are Represented

### Approval model

Work orders with `authority_mode: APPROVAL_REQUIRED` pause at actions that need founder sign-off. The existing `cc-prompt` mechanism handles this.

### Approval flow

```
Local worker encounters approval-required action
  → Sets work order status to WAITING_FOR_USER_APPROVAL
  → POSTs to VPS /cc-prompt: {
      session_name: "dex_local",
      text: "Work order {id} needs approval: [action description]",
      prompt_type: "permission"
    }
  → VPS sends to Discord with approval buttons
  → Founder clicks Approve/Deny
  → Response routes back to local tmux session via session_discord_bridge
  → Local worker reads approval/denial
  → Continues or blocks accordingly
```

**Confidence**: LIKELY — the `/cc-prompt` endpoint and Discord button mechanism exist. Wiring them to work order approval is straightforward but untested.

### Approval-required actions for Google Workspace ingestion

| Action | Why approval needed |
|--------|-------------------|
| Reading specific document content (not just metadata) | Privacy — founder should confirm each doc |
| Exporting/downloading documents | Data movement |
| Taking screenshots | Evidence capture |
| Accessing folders marked SENSITIVE | Sensitivity boundary |

---

## 7. How Audit Notes Are Preserved

### Per work order

Every status transition appends to `audit_notes` list:

```json
{
    "audit_notes": [
        "2026-05-04T10:00:00Z | CREATED by vps-orchestrator",
        "2026-05-04T10:00:05Z | QUEUED — health check pending",
        "2026-05-04T10:00:07Z | SENT_TO_LOCAL — bridge healthy",
        "2026-05-04T10:00:08Z | CLAIMED_BY_LOCAL",
        "2026-05-04T10:01:00Z | IN_PROGRESS — beginning Google Drive discovery",
        "2026-05-04T10:05:00Z | WAITING_FOR_USER_APPROVAL — read 'Coaching Frameworks' folder?",
        "2026-05-04T10:05:30Z | APPROVED by founder via Discord",
        "2026-05-04T10:10:00Z | COMPLETE — 24 docs discovered, 8 read, 16 metadata-only"
    ]
}
```

### Global audit log

All work order transitions are appended to `logs/work_orders.jsonl`:

```json
{"ts": "...", "work_order_id": "...", "status": "...", "detail": "..."}
```

**Confidence**: CONFIRMED — follows existing `logs/workstation.jsonl` pattern.

---

## 8. What Should Not Be Changed

| # | File/System | Why |
|---|------------|-----|
| 1 | `services/discord_bot.py` | Live production bot |
| 2 | `eos_ai/substrate/station_daemon.py` | Working daemon — don't add handlers yet |
| 3 | `eos_ai/substrate/station_bus.py` | Active bus files — don't change format |
| 4 | `eos_ai/substrate/station.py` | Contract layer — don't modify enums |
| 5 | `eos_ai/substrate/actions.py` | ActionKind enum — don't add kinds yet |
| 6 | `eos_ai/substrate/control_commands.py` | Command envelope — don't change schema |
| 7 | `.env` files | Bridge config already correct |
| 8 | Docker containers | Don't restart without explicit need |
| 9 | Cron entries | No work-order-related cron needed yet |
| 10 | `services/local_bridge_send_to_discord.sh` | Reply hook — separate from work orders |

---

## 9. What Remains Locally Unverified

| # | Item | Impact if wrong | How to verify |
|---|------|----------------|---------------|
| 1 | Tailscale connectivity | All communication fails | `tailscale ping 100.74.199.102` from VPS |
| 2 | Local bridge server running | Work order dispatch fails — queue locally | `curl http://100.74.199.102:8766/health` |
| 3 | Local tmux sessions exist | Message injection path broken | `tmux list-sessions` on local |
| 4 | `~/eos_work_orders/` can be created | Work order inbox fails | `mkdir -p ~/eos_work_orders && ls -la ~/eos_work_orders/` |
| 5 | Local machine has browser with Google login | Google Workspace work orders fail | Open browser, check Google logged in |
| 6 | Local aiohttp installed | Bridge server won't start | `pip show aiohttp` on local |
| 7 | `/work-order` endpoint added to local server | Work orders can't be dispatched via HTTP | Requires local server update in Phase 94L |
| 8 | VPS `/work-order-result` endpoint added | Results can't be posted back | Requires VPS update in Phase 94L |

**Phase 93R.1 defines the contract. Phase 94L implements the endpoints and executes the first work order.**
