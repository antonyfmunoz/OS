# Onboarding Topology Discovery v1

**Phase**: 94D.4 — Auto Worker Runtime + Topology Boundary
**Status**: ACTIVE
**Date**: 2026-05-04

---

## Purpose

When a new user begins using UMH, the system must discover their topology
before it can route work. This document defines what the discovery flow
must collect and how it maps to `TopologyProfile`.

## Discovery Steps

### Step 1 — Machine Inventory

Ask: "What machines will you use?"

For each machine, collect:
- **Type**: Cloud VPS, local workstation, phone, tablet, etc.
- **OS**: Linux, Windows, macOS, WSL, iOS, Android
- **Capabilities**: Can it run a browser? Does it have a GUI?
  Does it have a GPU? Can it run Docker?
- **Network**: IP or hostname (if on Tailscale/VPN)

Map each to a `NodeProfile`.

### Step 2 — Role Assignment

Based on capabilities, assign roles:
- Machine with orchestration + scheduling → `ORCHESTRATOR`
- Machine with GUI + screen control → `COMPUTER_USE_WORKER`
- Machine with file access → `LOCAL_FILE_NODE`
- Machine with LLM inference → `INFERENCE_NODE`

A single machine can hold multiple roles.

### Step 3 — Transport Discovery

For each pair of nodes that need to communicate:
- SSH available? Port, key auth?
- HTTP bridge running?
- Tailscale/VPN connected?
- Discord/Telegram available as relay?

Map each to a `TransportProfile`.

### Step 4 — Interface Discovery

What interfaces does the user have?
- Terminal on VPS → `CLI` with `PRIMARY_COMMAND`
- Discord server → `DISCORD` with `APPROVAL_CAPABLE`
- Phone app → `PUSH_NOTIFICATION` with `NOTIFICATION_ONLY`

Map each to an `InterfaceProfile`.

### Step 5 — Topology Assembly

Combine all profiles into a `TopologyProfile`. Store it.
This is the routing foundation for all work orders.

## Single-Machine Shortcut

If the user has only one machine, skip Steps 2-3.
Call `build_single_local_topology(owner_id)` and assign all roles
to that single node.

## File

`eos_ai/substrate/topology_contracts.py`
