# Phase 96.8K -- Worker Runtime + Adapter Registry v1

**Date:** 2026-05-07
**Status:** COMPLETE
**Gate:** CHROME_OPEN_VISIBLE_PROOF (achieved)
**Next Gate:** LOCAL_WORKER_RUNTIME_DAEMON_V1

---

## What Was Proven by CHROME_OPEN_VISIBLE_PROOF

The WSL client sent an open_application_url request through the
filesystem JSON relay. The native Windows PowerShell relay, running
in the logged-in desktop session, launched Chrome via direct
executable. The relay collected process/window metadata as evidence
and wrote a result with adapter_status=completed. The WSL client
read and parsed the result (BOM-tolerant). The main_window_title
field showed "Google Drive - Google Chrome".

This proves:
1. File-based relay between WSL and Windows desktop works end-to-end.
2. The Windows relay can launch GUI applications from the interactive session.
3. Process metadata is collected as evidence (not proof).
4. The WSL client correctly handles PS 5.1 encoding (UTF-8 BOM).
5. The full loop VPS -> WSL -> Windows -> Chrome -> result -> WSL -> VPS
   completes without any environment crossing its authority boundary.

---

## Why WSL Did Not Own GUI Authority

WSL runs Linux user-space processes. It does not have access to the
Windows desktop session. A Chrome process spawned from WSL may or may
not create a visible window on the Windows desktop. MainWindowHandle
from WSL-spawned processes is unreliable. Prior phases (96.8D-96.8G)
proved this empirically.

WSL owns: local shell, filesystem access, relay writes.
WSL does not own: GUI actuation, window management, desktop session.

---

## Why Windows Relay Is the Environment-Native Actuator

The PowerShell relay script runs in the logged-in Windows desktop
session (Session 1+, not Session 0). It has real desktop access
because it runs under the same user session that owns the display.
Start-Process from this session creates windows that appear on the
desktop. This is not a workaround -- it is the correct way to launch
GUI applications on Windows.

---

## Universal Harness != Universal Executor

The Universal Meta Harness does not execute everything itself. It
harnesses environment-native capabilities through typed adapters:

| Environment | What It Owns | What It Cannot Do |
|-------------|-------------|-------------------|
| VPS Claude tmux | Remote orchestration, scheduling, packet construction | Cannot own local GUI, local shell, or local filesystem |
| Local WSL tmux | Local shell, filesystem relay | Cannot own GUI, cannot launch visible Windows applications |
| Local Windows PS | GUI actuation, local shell, desktop session | Cannot be orchestrated remotely without relay |

The harness routes work to the correct environment. Each environment
does what it is natively capable of. No environment pretends to own
authority it does not have.

---

## Formal Concepts Introduced

### WorkerRuntime

A typed runtime instance that declares its environment, authority,
capabilities, and message bus. Each worker knows what it can and
cannot do.

### AdapterRegistry

Maps action types to adapters. When the worker receives a packet
requiring open_application_url, the registry resolves it to the
windows_interactive_desktop_relay adapter.

### CapabilityRegistry

Each adapter declares its capabilities with typed descriptors.
A capability declares whether it requires GUI, local shell, or
specific authority domains.

### EnvironmentAuthority

Typed descriptor for what an environment natively owns. Three
pre-built descriptors: VPS_AUTHORITY, WSL_AUTHORITY,
WINDOWS_DESKTOP_AUTHORITY.

### RuntimeProof

Immutable record that an action was attempted, what adapter handled
it, what the outcome was, and what evidence was collected. This is
the formal equivalent of the Phase 96.8J proof report.

### MessageBus

How workers and adapters communicate. v1 supports filesystem_json
(shared directory inbox/outbox). Future: ssh_tmux, direct_call.

---

## Environment Mapping

| Label | Environment | Worker ID | Authority |
|-------|-------------|-----------|-----------|
| A | VPS Claude tmux | (orchestrator, not a registered worker) | remote_orchestration |
| B | Local Windows PS | windows_interactive_desktop_relay | local_gui, local_shell |
| C | Local WSL tmux | local_wsl_worker | local_shell, filesystem_relay |

---

## Files Created

| File | Purpose |
|------|---------|
| core/runtime/worker_runtime_contracts.py | WorkerRuntimeDescriptor, EnvironmentAuthority, WorkerHeartbeat, RuntimeProofRecord |
| core/runtime/adapter_registry_contracts.py | AdapterDescriptor, CapabilityDescriptor, AdapterRegistry |
| data/registries/local_worker_adapter_registry_v1.json | Static registry fixture for local worker v1 |
| tests/test_worker_runtime_contracts.py | 15 contract tests |
| tests/test_adapter_registry_contracts.py | 14 registry tests |
| docs/system/phase968k_worker_runtime_adapter_registry_v1_report.md | This report |

---

## Tests Passed

| Test File | Tests | Status |
|-----------|-------|--------|
| test_worker_runtime_contracts.py | 15 | PASS |
| test_adapter_registry_contracts.py | 14 | PASS |
| **Total** | **29** | **ALL PASS** |

---

## What Was Not Executed

| Item | Status |
|------|--------|
| Chrome opened | NO (this phase) |
| Drive/Docs contents accessed | NO |
| Files ingested | NO |
| Gmail accessed | NO |
| Screenshots captured | NO |
| Tokens/cookies captured | NO |
| Memory promoted | NO |
| Discord daemon started | NO |

---

## Next Gate: LOCAL_WORKER_RUNTIME_DAEMON_V1

Build a small persistent local worker daemon that:
1. Registers its capabilities using WorkerRuntimeDescriptor.
2. Sends periodic heartbeats using WorkerHeartbeat.
3. Watches for incoming work packets.
4. Routes ping/open_application_url to the correct local adapter
   using the AdapterRegistry.
5. Returns RuntimeProofRecord for each completed action.

This daemon replaces the current ad-hoc relay client invocations
with a structured runtime that can be monitored, governed, and
extended.
