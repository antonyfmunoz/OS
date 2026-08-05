# Mesh binary-frame heartbeat — correction ledger

**Date:** 2026-08-05
**Base SHA:** `8f4f42c58894c5e79da0872dc967433c533ad631`
**Risk class:** HIGH (core mesh transport infrastructure)
**Scope:** VPS mesh server binary-frame path + node registry heartbeat contract

---

## 1. The defect

A node that streams **only binary frames** (desktop/camera capture) sends no
JSON `node.heartbeat` message. The registry evicted it after
`heartbeat_timeout_s` (90 s in production) while its WebSocket remained
`ESTABLISHED`. Because the socket never dropped, the daemon never reconnected or
re-registered, so `mesh_dispatch` refused a demonstrably live node with
`node windows-desktop not connected`.

**The condition could not self-heal**: the frames the node was sending were
exactly the kind that did not re-register it, and the live socket suppressed the
reconnect path.

### Observed production timeline (`journalctl -u umh-mesh.service`)

```
Aug 05 00:37:34  node registered: windows-desktop (21 peripherals)
Aug 05 00:37:53  binary WS frame from windows-desktop ... (n=1)
Aug 05 00:41:30  node removed: windows-desktop          ← evicted ~4 min later
Aug 05 00:43:36  binary WS frame from windows-desktop ... (n=2000)  ← still streaming
```

Corroborating evidence at diagnosis time:

| Probe | Result |
|---|---|
| Tailscale peer `desktop-lvguiq9` | active, direct |
| ICMP | 0% loss, 83 ms |
| SSH :22 | open |
| Daemon PID 12024 (`launcher.py`) | running, **Session 1** |
| Socket → VPS:8094 | `ESTABLISHED` |
| Relay `/health` | `connected_nodes: 0` |
| `mesh_dispatch(...)` | `node windows-desktop not connected` |

The host was healthy; the failure was entirely a VPS-side registry state.

---

## 2. Before / after heartbeat flow

### Before

```
authenticated WS
  → binary frame arrives
    → _handle_binary_frame(node_id, raw)   [returns None]
    → continue                              ← registry NEVER touched
  → 90 s elapse with no JSON heartbeat
    → stale_nodes() reports the node
    → _unregister_node(node_id)
  → socket STILL ESTABLISHED → daemon never reconnects
  → dispatch refuses: "node not connected"   (unrecoverable)
```

Only `node.heartbeat` (JSON-RPC) reached `registry.update_heartbeat()`.

### After

```
authenticated WS  (node_id is None until node.hello binds it)
  → binary frame arrives
    → _handle_binary_frame(node_id, raw) -> bool
        malformed (meta_len > 65536, or 4+meta_len > len(raw)) -> False
        valid + routed                                          -> True
    → if True:  registry.update_heartbeat(node_id)
        └─ returns False for an unknown node → logged as a WARNING, never swallowed
  → node stays registered while it genuinely streams
  → node goes silent → normal eviction still fires
```

---

## 2b. CRITICAL found in review — the first fix was fail-OPEN

The initial implementation reused `_handle_binary_frame`'s return value as the
liveness signal. Independent adversarial review demonstrated, end-to-end over a
real WebSocket, that **seven bytes of zeros forged an indefinite heartbeat**:

```
b"\x00" * 7
  meta_len == 0        → 0 > 65536 is False, 4 > 7 is False  → both bounds pass
  json.loads(raw[4:4]) → raises → swallowed to meta = {}
  falls through        → return True                          → heartbeat refreshed
```

Reproduced independently before accepting the finding:

```
7 zero bytes     -> True
meta_len=0 +body -> True
```

**Why this was worse than the bug being fixed.** The original defect was
*fail-safe*: a live node was marked dead. This inversion was *fail-open*: a node
whose capture pipeline is dead but whose socket still emits padding would be
advertised as live indefinitely, and dispatch would route real work to a node
that cannot execute it.

**Root cause (author error).** Forwarding-tolerance and liveness-proof are
different predicates and must not share a return value. The relay is
*intentionally* permissive — it forwards a frame whose meta is unparseable as
`meta = {}`. Promoting that tolerance to proof of life is the defect.

**Resolution.** A separate, strict, unforgeable predicate
`_frame_proves_liveness()` was added; the caller now requires **both**
`proves_liveness and forwarded`. Forwarding behavior is unchanged (the relay
stays tolerant). Liveness requires a non-empty meta block that parses to a JSON
**object**, plus a non-empty payload after it.

Post-fix verification of every demonstrated vector:

| Frame | liveness |
|---|---|
| `b"\x00" * 7` | False |
| `meta_len=0` + body | False |
| non-JSON meta | False |
| JSON but not an object | False |
| valid meta, zero-length payload | False |
| real frame | **True** |

---

## 3. Files changed

| File | Change |
|---|---|
| `transports/node_mesh/server.py` | Added `_frame_proves_liveness()` — a strict, unforgeable liveness predicate. `_handle_binary_frame` returns `bool` for *forwarding* acceptance only. Caller refreshes the heartbeat only when **both** hold, only for this connection's bound `node_id`, and surfaces a registry refusal as a warning. |
| `transports/node_mesh/registry.py` | `_write_snapshot()` made atomic (temp file + `os.replace`); added `import os`. |
| `tests/test_mesh_binary_frame_heartbeat.py` | **New.** 29 tests: the forwarding/liveness split, the security boundary, eviction behavior, snapshot atomicity — including five live-WebSocket integration tests. |
| `data/audits/2026-08-05_mesh_binary_frame_heartbeat.md` | This ledger. |

`registry.update_heartbeat()` semantics were **not** changed — it already
returned `False` for an unknown node, which is the authoritative signal the fix
consumes. Only the snapshot write path was made atomic.

---

## 4. Security-boundary proof

Refresh is reachable **only** when every condition holds:

| # | Requirement | Enforced by |
|---|---|---|
| 1 | WS authentication completed | `_authenticate(token)` closes with 4001 before the frame loop is entered |
| 2 | Connection bound to one registered node | `node_id` stays `None` until `node.hello`; the caller guards on `if node_id` |
| 3 | Frame valid under the wire format | `_handle_binary_frame` returns `False` on the malformed early-return |
| 4 | Frame accepted by the normal handler | refresh is gated on that `True` |
| 5 | Update applies to that same node only | `update_heartbeat(node_id)` uses the connection-bound identity |

Refresh is therefore **unreachable** for: unauthenticated sockets, malformed
frames, rejected frames, unknown nodes, mismatched identities, replay on another
connection, arbitrary TCP traffic, failed authentication, and any exception
before frame acceptance.

Eviction was **not weakened**: `heartbeat_timeout_s` and `stale_nodes()` are
unchanged, and an idle node is still evicted (proved live, §5).

---

## 5. Validation results

### Targeted suite — `tests/test_mesh_binary_frame_heartbeat.py`: **15 passed**

Live-WebSocket integration (real `NodeMeshServer`, real client, real frames):

| Test | Proves |
|---|---|
| `test_live_node_streaming_binary_only_survives_three_windows` | binary-only node survives **3× the eviction window** (6 s @ 2 s timeout), then **is still evicted when idle**, and cleanup on close is intact |
| `test_live_malformed_frames_do_not_refresh_heartbeat` | malformed-only streaming still goes stale |
| `test_live_frame_from_one_node_cannot_refresh_another` | with two registered nodes, only the sender stays fresh; the silent node is still evicted |
| `test_unauthenticated_and_prehello_binary_never_registers` | failed auth and pre-`hello` binary never create or refresh a registration |

**Defect-detection check:** with the fix reverted, the live test fails
(`stale_after_streaming: True`); with the fix applied it passes. The test
observes the real defect, not a restatement of the patch.

### Differential regression proof (baseline vs candidate)

A raw pass/fail count from `pytest tests/` is not evidence on its own: the repo
carries substantial pre-existing failure debt (523 failed / 56 errors across all
17,693 tests, present before this change). So the candidate was compared against
its own base commit under an identical selector, in a separate worktree checked
out at `8f4f42c58`:

```
pytest tests/ -k "mesh or node or transport or dispatch or relay or
                  registry or workspace or fabric or grounding or continuity"
```

| SHA | failed | passed |
|---|---|---|
| baseline `8f4f42c58` | **51** | 1765 |
| candidate `e3e20f52b` | **51** | 1794 (**+29**) |

**Identical failure count; +29 passing, exactly the 29 tests added here.**

Counts alone could mask one regression plus one accidental fix, so the failing
**node-ID sets** were captured on both sides and diffed:

```
comm -13 BASE_ids NEW_ids   → (empty)   # regressions introduced: NONE
comm -23 BASE_ids NEW_ids   → (empty)   # failures fixed/moved: NONE
base=51  new=51
```

Both directions empty — the 51 failures are the **same** 51. No regression
introduced. The 51 failures are pre-existing (workspace panel nav,
continuity resume, voice turn assembly) and unrelated to mesh transport — none
of them touch `node_mesh`, `mesh_auth`, `mesh_dispatch`, or `binary_frame`.

### Regression — existing mesh suites: **68 passed**

`test_node_mesh.py`, `test_node_mesh_ws.py`, `test_mesh_auth_binding.py`,
`test_mesh_dispatch_contract.py`, `test_mesh_dispatch_governed.py` — shell,
filesystem, desktop, terminal, frame-relay, auth, and governed-dispatch behavior
unchanged.

### Mutation testing: **12/12 killed, 0 survivors**

| Mutant | Verdict |
|---|---|
| M1 omit the binary-frame refresh (original defect) | KILLED |
| M2 refresh **before** validation | KILLED |
| M3 refresh **every** connected node | KILLED |
| M4 malformed frame reports accepted | KILLED |
| M5 eviction disabled entirely | KILLED |
| M6 local timestamp only, authoritative registry not updated | KILLED |
| M7 swallow registry-update failure, report success | KILLED |
| M8 refresh the **wrong** node identity | KILLED |
| M9 allow `meta_len == 0` (zero-byte forgery) | KILLED |
| M10 liveness degrades on unparseable meta | KILLED |
| M11 liveness gate bypassed (forwarding alone refreshes) | KILLED |
| M12 non-object JSON accepted as liveness | KILLED |

Both mutated files restored **byte-identically** (sha256 verified in-sweep).

**M9 initially SURVIVED.** The parametrized cases all happened to be caught by
an *earlier* guard than the one M9 reverts, so the mutant was equivalent for
every input under test. The distinguishing input had to be derived explicitly: a
**valid JSON meta that exactly fills the frame, leaving zero payload bytes** —
`strict=False`, `M9=True`. That is the real attack the `>=` bound stops (a node
emitting well-formed headers with no captured image). Two such cases were added
and M9 died. A green sweep whose mutants are equivalent proves nothing; the
distinguishing input is the test.

**Honest note on the sweep:** M2 and M3 **survived the first run**. Both
original tests asserted against `NodeRegistry` directly while re-implementing
the caller's `if accepted:` guard inside the test — a test that mirrors the
server's logic cannot detect that logic being reordered or broadened. They were
replaced with live-WebSocket tests that drive the real server path, after which
both mutants died. The first sweep's survivors are recorded here rather than
quietly overwritten.

---

## 6. Performance impact (measured, not assumed)

`registry.update_heartbeat()` calls `_write_snapshot()` (JSON dump + file write).
Because binary frames now trigger it, the write rate rises from once per
heartbeat interval to once per accepted frame — so it was measured rather than
hand-waved.

**Production frame rate**, from `journalctl` (`n=500` at 00:39:22 → `n=1000` at
00:40:48): **≈5.8 frames/s** across the camera (2 fps, `client.py:101`) and
desktop streams.

**Measured cost** (600 refreshes, real `NodeRegistry`, temp snapshot path):

```
600 refreshes took 438.5 ms  → 0.731 ms each
at 5.8 frames/s → 0.42% of one core
```

0.42% of a single core, far inside the CPU Gate Law ceiling. The snapshot
content is byte-identical on a binary refresh (presence and `status` are already
`connected`), so the write is redundant but harmless.

**Deliberately NOT optimized.** Adding a "skip snapshot on liveness-only
refresh" branch would change `NodeRegistry` write semantics for every caller —
beyond the smallest correction authorized here. Snapshot consumers
(`compute_fabric_runtime._online_node_ids`, cockpit bootstrap/workspace routes)
read **presence/status only**, never `last_heartbeat` freshness, so neither the
current behavior nor a future optimization affects them. Recorded as a known,
quantified, non-blocking cost.

---

## 7. Identity rebinding (verified upstream guarantee)

Requirement 6 does not rest on this change alone. `_handle_hello`
(`server.py`) enforces token→node binding **fail-closed**: when
`node_tokens` are configured, a token not bound to the declared `node_id` is
rejected with close code 4003. A second `node.hello` on the same socket
therefore cannot rebind the connection to a different identity, so a
connection's `node_id` is fixed for its lifetime. The live cross-node test
confirms the resulting behavior empirically.

---

## 8. Scope discipline

- Mesh protocol **not** redesigned — no new message types, no wire-format change.
- **No** recovery subsystem added.
- Registry eviction **not** weakened.
- Arbitrary socket activity does **not** count as health — only an *accepted
  frame* does.
- Authentication and unrelated transports untouched.
- Pre-existing `ruff check` findings in `server.py` (5, import-organization)
  were present before this change and are left alone as out of scope.
