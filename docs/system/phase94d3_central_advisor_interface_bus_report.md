# Phase 94D.3 — Central Advisor Session + Interface-Agnostic Communication Bus Correction v1

**Date**: 2026-05-04
**Status**: COMPLETE
**Predecessor**: Phase 94D (Work Order 001 Dispatch — dispatch succeeded, local worker behavior incorrect)
**Source code modified**: NO existing files. 4 new additive contract modules + 1 test file.
**Tests**: 25/25 passing

---

## 1. Executive Summary

Phase 94D.3 defines the architectural correction needed after Phase 94D revealed two problems: (1) the local worker asked for approval only in the local terminal, and (2) it used Playwright/Chromium automation instead of visible GUI computer use. Both stem from the same root cause: the system was designed around a single CLI session rather than a centralized communication model.

This phase defines: a central advisor session as the founder-facing command/intelligence layer; an interface-agnostic message bus that normalizes all communication into a single envelope format regardless of interface; interface projections that declare the capabilities and limitations of each UI channel; 31 message types organized by origin (founder, advisor, node, system); a corrected local worker message loop that routes approvals through the bus instead of prompting locally; a GUI computer-use backend policy that disables Playwright by default; and a corrected WO-001 execution model that puts all of these together.

All contracts are code-complete with 25 tests validating serialization, routing, type categories, backend selection, and approval flow.

---

## 2. Why Approval Relay Alone Was Too Narrow

Phase 94D attempted to solve "how does the founder approve actions on the local PC from the VPS." The answer was going to be an approval relay — forward approval prompts from local to VPS, forward responses back.

The founder clarified that the problem is larger:
- The system should not be designed around one CLI session
- CLI is only one interface projection
- The founder communicates from VPS CLI, Discord, Telegram, phone, voice, workstation UI, browser overlay, web dashboard
- Approvals are one message type, not the entire architecture
- The real need is a centralized session that persists across interfaces

An approval relay would have solved one symptom while leaving the interface-locked architecture intact. This phase corrects the architecture.

---

## 3. Corrected Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CENTRAL ADVISOR SESSION                    │
│  (persistent, interface-agnostic, manages work + approvals)  │
└──────────┬──────────────┬──────────────┬────────────────────┘
           │              │              │
    ┌──────▼──────┐ ┌─────▼─────┐ ┌─────▼──────┐
    │ CLI (VPS)   │ │  Discord  │ │  Telegram  │  ... + mobile, voice,
    │ CLI (local) │ │  channel  │ │  chat      │      workstation, browser,
    │ Termius     │ │  buttons  │ │  keyboard  │      web dashboard
    └─────────────┘ └───────────┘ └────────────┘
         ▲                                    ▲
         │         MESSAGE BUS                │
         │    (envelope normalization,        │
         │     routing, audit)                │
         ▼                                    ▼
    ┌─────────────┐                    ┌─────────────┐
    │ VPS Node    │                    │ Local PC    │
    │ (agents,    │                    │ (GUI use,   │
    │  LLM, API)  │                    │  browser,   │
    └─────────────┘                    │  manual)    │
                                       └─────────────┘
```

Key change: **Interfaces are projections. The session is the center. Messages flow through one bus.**

---

## 4. Central Advisor Session Model

Defined in `docs/operations/central_advisor_session_model_v1.md`.

- 10 core responsibilities
- 4 message categories (founder, advisor, node, system)
- Session state: ACTIVE, IDLE, SLEEPING, PAUSED
- Persistence: Neon DB + in-memory checkpoint
- NOT an approval queue — approvals are one event type

---

## 5. Interface-Agnostic Message Bus

Defined in `docs/operations/interface_agnostic_message_bus_v1.md`.

- 20-field message envelope
- 9 declared interface types (CLI, Discord, Telegram, mobile, workstation, voice, browser overlay, web dashboard, plus node and system)
- Interface adapters normalize native input → envelope → native output
- Transport-agnostic: uses HTTP bridge, SSH, station bus, or in-process depending on route
- Continuity protocol: interface switch preserves session state, queued messages deliver on reconnect

---

## 6. Interface Projection Contract

Defined in `docs/operations/interface_projection_contract_v1.md`.

- 15-field projection declaration
- 8 interface types with full capability declarations
- 6 approval modes (text prompt, button, inline keyboard, modal, voice confirm, none)
- 22 capability types
- Fallback chain: degrade → re-route → queue → never drop

---

## 7. Local Worker Corrected Loop

Defined in `docs/operations/local_worker_message_loop_v1.md`.

Before: worker prompts locally, founder must be at local terminal.
After: worker sends APPROVAL_NEEDED to advisor via message bus, founder responds from any interface.

- 9-step execution loop
- State machine: IDLE → CLAIMING → EXECUTING → WAITING_FOR_APPROVAL → COMPLETING → DONE
- Manual local fallback only when bus is confirmed down AND founder explicitly selects it
- All local fallback actions tagged `audit_tags: ["manual_fallback"]`

---

## 8. GUI Computer-Use Backend Policy

Defined in `docs/operations/gui_computer_use_backend_policy_v1.md`.

4 backend classes:
1. **GUI_COMPUTER_USE** — visible screen, mouse/keyboard, founder watches (preferred)
2. **BROWSER_AUTOMATION** — Playwright/Selenium, invisible, disabled by default
3. **API_CONNECTOR** — official APIs, for bulk/programmatic access
4. **MANUAL_FALLBACK** — founder performs step manually

WO-001 policy: GUI_COMPUTER_USE required, Playwright disabled unless explicitly approved via MODIFY_CONSTRAINTS.

---

## 9. Corrected WO-001 Execution Model

Defined in `docs/operations/work_order_001_corrected_central_session_execution_model_v1.md`.

- Approvals route through message bus, not local terminal
- Founder responds from any interface (VPS CLI, Discord, phone, voice)
- Execution uses visible GUI computer use, not Playwright
- 8-step corrected flow with full message examples
- Existing work order instructions will be updated in Phase 94D.4

---

## 10. Code Contracts Created

| # | File | Contents | Tests |
|---|------|----------|-------|
| 1 | `eos_ai/substrate/message_bus_contracts.py` | MessageType (31), SourceInterface (10), MessagePriority, MessageStatus, MessageEnvelope with serialize/deserialize, category frozensets | 9 |
| 2 | `eos_ai/substrate/interface_projection_contracts.py` | InterfaceType (8), ApprovalMode (6), InterfaceCapability (22), InterfaceProjection dataclass, CLI/Discord/Workstation declarations | 4 |
| 3 | `eos_ai/substrate/advisor_session_contracts.py` | AdvisorSessionState (4), AdvisorEventKind (13), AdvisorSessionEvent, AdvisorSessionCommand, PendingApproval with resolve() | 5 |
| 4 | `eos_ai/substrate/computer_use_backend_contracts.py` | ComputerUseBackend (4), DEFAULT_BACKEND_BY_TASK_TYPE, BackendPolicy, select_backend(), requires_approval_for_browser_automation() | 7 |
| 5 | `tests/test_phase94d3_central_advisor_bus_contracts.py` | 25 tests across 4 test classes | — |

All 4 code modules are additive-only. No existing files modified.

---

## 11. Remaining Implementation Needed

| # | Component | Description | Phase |
|---|-----------|-------------|-------|
| 1 | Message bus router | Actual routing logic: receive envelope, resolve target, deliver via transport | 94D.4 |
| 2 | VPS `/message-bus` endpoint | HTTP endpoint on VPS to receive bus messages from nodes | 94D.4 |
| 3 | Local `/message-bus` endpoint | HTTP endpoint on local bridge to receive bus messages from advisor | 94D.4 |
| 4 | Interface adapters | CLI adapter, Discord adapter (normalize → envelope → render) | 94D.4+ |
| 5 | Advisor session runtime | State machine, pending approval tracking, work order tracking | 94D.5 |
| 6 | GUI computer-use backend check | `check_gui_computer_use_available()` on local PC | 94D.4 |
| 7 | Updated WO-001 instructions | Rewrite execution instructions to use bus instead of local prompts | 94D.4 |
| 8 | Session persistence | Neon DB tables for message history, session state | 94D.5 |
| 9 | Approval relay via Discord | Wire APPROVAL_NEEDED → Discord embed with buttons → APPROVAL_RESPONSE | 94D.5 |

---

## 12. Recommended Next Phase

### Phase 94D.4 — Implement Central Message Relay + GUI Computer-Use Backend Healthcheck

**Scope:**
1. Add `/message-bus` endpoint to `cc_webhook_receiver.py` on VPS
2. Add `/message-bus` endpoint to `local_bridge_server.py` on local
3. Implement minimal message bus router (receive, validate, route to target)
4. Implement CLI adapter (normalize text → envelope, envelope → text)
5. Implement GUI computer-use backend availability check on local
6. Update WO-001 execution instructions to use bus
7. Test end-to-end: local worker sends APPROVAL_NEEDED → VPS CLI receives → founder types APPROVE → routes back to local

**Entry conditions:**
- Phase 94D.3 contracts complete (this phase)
- 25/25 tests passing
- Bridge is healthy (established in Phase 94D.1)
- SSH key auth working (established in Phase 94D.1)

---

## 13. What Was Produced

### Documentation (8 files)

| # | File | Purpose |
|---|------|---------|
| 1 | `docs/operations/central_advisor_session_model_v1.md` | Central advisor session definition |
| 2 | `docs/operations/interface_agnostic_message_bus_v1.md` | Message bus architecture |
| 3 | `docs/operations/interface_projection_contract_v1.md` | Interface projection declarations |
| 4 | `docs/operations/central_command_message_types_v1.md` | 31 message type definitions |
| 5 | `docs/operations/local_worker_message_loop_v1.md` | Corrected local worker behavior |
| 6 | `docs/operations/gui_computer_use_backend_policy_v1.md` | Backend policy + Playwright disabled |
| 7 | `docs/operations/work_order_001_corrected_central_session_execution_model_v1.md` | Corrected WO-001 flow |
| 8 | `docs/system/phase94d3_central_advisor_interface_bus_report.md` | This phase report |

### Code (5 additive files)

| # | File | Tests |
|---|------|-------|
| 1 | `eos_ai/substrate/message_bus_contracts.py` | 9 |
| 2 | `eos_ai/substrate/interface_projection_contracts.py` | 4 |
| 3 | `eos_ai/substrate/advisor_session_contracts.py` | 5 |
| 4 | `eos_ai/substrate/computer_use_backend_contracts.py` | 7 |
| 5 | `tests/test_phase94d3_central_advisor_bus_contracts.py` | 25 total |

---

## 14. What Was NOT Changed

| # | File/System | Why |
|---|------------|-----|
| 1 | `services/local_bridge_client.py` | Transport layer — used as-is |
| 2 | `services/local_bridge_server.py` | Phase 94D.4 adds /message-bus endpoint |
| 3 | `services/cc_webhook_receiver.py` | Phase 94D.4 adds /message-bus endpoint |
| 4 | `services/discord_bot.py` | Phase 94D.5 adds adapter |
| 5 | `eos_ai/substrate/work_order_contracts.py` | Not modified — contracts compatible |
| 6 | `eos_ai/substrate/station_bus.py` | Not modified |
| 7 | `eos_ai/substrate/station_daemon.py` | Not modified |
| 8 | `eos_ai/substrate/__init__.py` | New modules not added to surface |
| 9 | `.env` files | Not modified |
| 10 | Docker containers | Not restarted |

---

## 15. Safety Attestation

| Question | Answer |
|----------|--------|
| Did this phase perform computer use? | NO |
| Did this phase open Google Drive? | NO |
| Did this phase use Playwright? | NO |
| Did this phase send/post/edit/delete/move files? | NO |
| Did this phase capture credentials? | NO |
| Did this phase promote memory? | NO |
| Was governance bypassed? | NO |
| Did this phase modify existing production code? | NO — all additive |
| Did any test call network? | NO — all in-memory |
| Did any test modify external state? | NO |
