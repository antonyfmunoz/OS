# os-operator Sustained-Load Starvation Diagnosis

**Packet:** WP-P4-OS-OPERATOR-SUSTAINED-LOAD-001 (lane E, `data/umh/roadmap/p4_sync_workgraph.json`)
**Date:** 2026-07-06
**Author:** Lane-C executor (Developer Agent)
**Status:** Diagnosis complete. Fixes PROPOSED (not applied) — see §7.
**Container at report time:** restored to `healthy` after diagnosis-time restart (see §6).

---

## 1. Summary

os-operator went `unhealthy` 3-for-3 under sustained wave load on 2026-07-06;
`docker restart os-operator` cleared it each time. This diagnosis reproduced the
**exact wedged state passively** (no load generation required — the container had
already degraded again by the time analysis began) and isolated the mechanism to
**two independent, compounding faults**, both confirmed with live kernel-cgroup
evidence:

1. **Resource starvation over uptime** (the healthcheck-failure axis): the
   container is CPU-throttled on **99.7% of scheduling periods** (`nr_throttled
   13999 / nr_periods 14036`) against its `cpus: "0.50"` cap, AND pinned against
   its `memory: 1G` hard limit (**`memory.events: max 517`** — the memory
   high-water reclaim was triggered 517 times; RES sat at 983 MiB / 1024 MiB =
   96%). The combination starves the uvicorn event loop of scheduling time, so
   even the trivial `/health` probe (a pure `async def` scheduling
   `asyncio.sleep(0)`, touching neither threadpool nor DB) times out → Docker
   marks the container unhealthy.

2. **A single intrinsically-slow blocking endpoint** (the trigger under load):
   `GET /api/umh/unified-workstation/snapshot` blocks for **>55 s on a
   fresh process with no memory pressure** (measured 55.2 s → 504). It is a
   synchronous `def` handler, so it holds an **AnyIO threadpool token for its
   entire duration**. The cockpit polls it on a loop; copies pile up; the
   40-token AnyIO pool exhausts; the 55 s server-side timeout middleware fires
   → the observed `504 Gateway Timeout` flood.

`docker restart` fixes it because a fresh process drops RES from 983 MiB → 244 MiB
(96% → 24%), relieving axis (1) and clearing the queued backlog of blocked
threads — until uptime + polling re-accumulate the pressure.

**Root cause is inside os-operator.** No governed-mutation path is implicated. No
feature-behavior change is proposed as an applied fix (both real fixes are
behavior-adjacent and are escalated as proposals).

---

## 2. Environment / configuration (read-only facts)

Host: 4 cores (`nproc` = 4). Hostinger VPS — CPU-throttle-sensitive.

`docker-compose.yml` → `os-operator`:

- `command: python3 -m uvicorn services.operator_api:app --host 0.0.0.0 --port 8091`
- `deploy.resources.limits`: **`cpus: "0.50"`**, **`memory: 1G`**
  (`NanoCpus=500000000`, `Memory=1073741824`, `MemorySwap=2147483648`).
- Healthcheck: `python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8091/health', timeout=5)"`,
  `interval: 30s`, `timeout: 10s`, `retries: 3`, `start_period: 30s`.
- Port: `127.0.0.1:8091:8091` (loopback only; fronted by nginx/cockpit, which is
  where the client-visible `504` originates when the middleware returns it).

---

## 3. Evidence chain

### 3.1 Container was already wedged (passive reproduction)

`docker inspect os-operator --format '{{json .State.Health}}'` at analysis start:

```
Status: unhealthy, FailingStreak: 9
Every failing probe: TimeoutError: timed out   (urllib readinto → socket recv)
```

`docker stats os-operator --no-stream` at analysis start:

```
CPU 52.36%   MEM 958.6MiB / 1GiB (93.61%)   PIDS 42
```

(52% CPU against a 0.50 cap = the cap is fully saturated — 0.50 cores ≈ 50% of
one host core reported as ~52% container-relative.)

Three **single, trivial** `curl` probes to `/health` (no load run) each hung the
full 12 s client timeout:

```
health: http=000 total=12.006712s   (x3, all connection-never-completes)
```

A single `curl` to `/snapshot` hung the full 58 s: `http=000 total=58.005426s`.
loadavg before/during these single probes: 3.69 → 2.70 (well under the 8.0
abort ceiling; no load generated).

### 3.2 Kernel cgroup counters — the smoking gun

`/sys/fs/cgroup/cpu.stat` (inside container):

```
nr_periods    14036
nr_throttled  13999        ← 99.7% of scheduling periods throttled
throttled_usec 1887560670  ← ~1888 s of wall-time spent CPU-throttled
```

`/sys/fs/cgroup/memory.events` (inside container):

```
max 517        ← memory high-water reclaim triggered 517 times
oom_kill 0     ← never OOM-killed (State.OOMKilled=false confirms)
```

`memory.current 1003220992 / memory.max 1073741824` = **93.4%** at report time.

**Interpretation:** the process is throttled essentially every CPU period AND
living against the memory ceiling. The GIL-bound event loop cannot get scheduled
often enough to service even a zero-work coroutine within Docker's 10 s probe
timeout.

### 3.3 The healthcheck is already correctly isolated

`services/operator_api.py:275` `/health` is a pure `async def` that does
`await asyncio.wait_for(asyncio.sleep(0), timeout=3.0)` and returns. It touches
**neither** the AnyIO threadpool **nor** the DB. Probe isolation is therefore
**not** the fix — the loop starves regardless of what the probe does. This rules
out "healthcheck hits the starved pool" as the cause.

### 3.4 The threadpool topology

- `services/operator_api.py` lifespan sets a **16-worker** default executor via
  `loop.set_default_executor(_api_executor)` — but this ONLY governs
  `loop.run_in_executor()` / `asyncio.to_thread()` calls.
- Starlette runs **synchronous `def` route handlers** in **AnyIO's own
  `CapacityLimiter`**, default **40 tokens**, which is **never tuned** in this
  codebase (grep for `set_total_tokens` / `CapacityLimiter` returns only
  unrelated `total_tokens` matches). So there are effectively two pools.
- Route-handler census across `transports/api/cockpit_*routes.py`:
  **771 synchronous `def` routes vs 69 `async def`.** The cockpit dashboard polls
  ~30 of these per refresh cycle (visible in logs as a repeating burst of
  `GET /api/umh/organism/*`, `.../workspace/*`, `.../unified-approval/*`, …).
  Every one of those consumes an AnyIO token for its duration.

### 3.5 The slow endpoint is intrinsic, not just a victim

After restart, on a **fresh 244 MiB process with zero memory pressure**:

```
GET /api/umh/unified-workstation/snapshot   → 504  total=55.23s
```

So `/snapshot` blocks >55 s **on its own**, independent of the resource axis.
`/snapshot` (`transports/api/cockpit_unified_workstation_routes.py:131`,
`def get_snapshot`) composes six sub-reads:

```
rt.snapshot().to_dict()   (UnifiedWorkstationRuntime construction + snapshot)
_read_continuity()  _read_mode_composite()  _read_overnight()
_read_nodes()  _read_presence_capabilities()
```

The trivial ones were ruled out by inspection: `_read_nodes()` →
`_read_mesh_snapshot()` / `_read_vps_node()` are a single small file read plus
`platform.*` calls (`cockpit_workstation_control_routes.py:568-604`). The >55 s
block is therefore inside `UnifiedWorkstationRuntime().snapshot()` or one of
`_read_overnight()` / `_read_mode_composite()`. Tracing and fixing that changes
endpoint behavior and is **out of scope for this packet** (feature-behavior stop
condition) — it is filed as proposed follow-up P1 in §7.

### 3.6 Log signature corroboration

`docker logs os-operator` around the unhealthy window shows:

- Repeating `504 Gateway Timeout` on exactly two paths:
  `/api/umh/unified-workstation/snapshot` and
  `/api/umh/command-center-mvp/execution-summary`.
- A ~30-endpoint polling flood from the single cockpit client (172.18.0.1).
- `environment_reconciler: reconciliation … (8594.0ms)` — an 8.6 s
  loop-occupying reconcile, consistent with threadpool/loop contention.
- `runtime_supervisor: runtime {codex,hermes,opencode,ollama,beast_gpu}
  recovery failed … still unavailable` — unrelated background runtime-availability
  churn (not a fault of this packet, noted for completeness).

---

## 4. Root-cause statement

Under sustained cockpit polling load, os-operator wedges because:

> `/snapshot` (a synchronous, intrinsically >55 s handler) holds AnyIO threadpool
> tokens for its full duration; repeated polling piles copies up and drains the
> 40-token pool. Concurrently, memory climbs to the 1 GiB hard limit (517 reclaim
> events) and CPU is throttled on 99.7% of periods against the 0.50-core cap.
> The starved, GIL-bound event loop cannot service even the zero-work `/health`
> coroutine within Docker's 10 s probe timeout → `unhealthy` (3 retries × 30 s
> interval = the observed 3-for-3). `docker restart` resets accumulated RES
> (983 MiB → 244 MiB) and clears the blocked-thread backlog, restoring health
> until the cycle repeats.

Both axes are **inside os-operator**. Neither involves a governed-mutation path.

---

## 5. Secondary anomaly investigated (:8095 dispatch 401 poller)

Task-flagged: an unidentified localhost process POSTs to `:8095/dispatch` every
~5 s getting 401s. **Identified, read-only, not a rogue process:**

- `:8095` LISTEN: host PID **906512** = `/usr/bin/python3 /opt/OS/transports/node_mesh/run.py`
  (the node-mesh relay, `ppid 906452`, ~4 h uptime).
- The connecting peer is **os-operator itself** (container IP `172.18.0.3` →
  `docker inspect` maps `172.18.0.3 = os-operator`).

So os-operator's own mesh-dispatch relay path polls the host mesh relay. The 401s
are **expected fail-closed behavior**: `UMH_MESH_RELAY_SECRET` is empty when not
1Password-injected (documented in the compose comment: *"empty when not injected
keeps the dispatch path fail-closed (relay refuses…)"*), so the relay correctly
rejects with 401. This is a **minor** contributor only — it wakes a thread every
~5 s. **No action taken** (report-only per packet; killing nothing). If the noise
is undesirable, the correct fix is to inject `UMH_MESH_RELAY_SECRET` at compose
time or gate the poll when the secret is absent — filed as proposed follow-up P3.

---

## 6. Container restoration (constraint compliance)

The container was already `unhealthy`/wedged at analysis start and single trivial
probes confirmed it could not serve `/health`. Per packet constraints (restore if
a run leaves it unhealthy), it was restarted:

```
nice -n 15 docker restart os-operator
```

Post-restart verification:

```
/health            → http=200 (~9 s after restart)
docker health      → healthy, FailingStreak=0
docker stats       → MEM 244MiB / 1GiB (24%)   (was 983MiB / 96%)
```

Container is **healthy** as of report time. No prod DB writes, no secret material
touched, no other containers restarted.

---

## 7. Fixes: PROPOSED (not applied)

No fix is applied. Every genuinely effective fix is either a feature-behavior
change or a resource change that could mask the leak — both excluded by packet
stop conditions. They are proposed here for a follow-on packet.

**P1 — Fix the `/snapshot` >55 s block (PRIMARY; behavior-adjacent → escalate).**
Trace which of `UnifiedWorkstationRuntime().snapshot()` / `_read_overnight()` /
`_read_mode_composite()` blocks >55 s and make it bounded (timeout + cached
fallback), OR make `get_snapshot` `async def` and push the composition through
`asyncio.to_thread` with a per-sub-read timeout. This is the actual trigger and
removes the token-pile-up. **Changes endpoint latency/shape → requires its own
packet + regression qualification.**

**P2 — Bound AnyIO threadpool pressure WITHOUT raising thread count.** Do NOT
raise the AnyIO limiter above 40 — more threads under a 0.50-core cap increases
CPU contention and would worsen the loop starvation. Instead: (a) convert the
handful of hot-polled read routes that do only file reads to `async def` with
`asyncio.to_thread` + short timeouts so a slow one cannot hold a limiter token
indefinitely; (b) consider a dedicated small limiter for the known-slow routes.
Behavior-adjacent → own packet.

**P3 — Memory headroom / recycle (infra, behavior-preserving but masks leak).**
Options, in preference order: (i) find and fix the RES growth from 244 MiB →
983 MiB over ~7 h uptime (a real leak or unbounded cache — proper fix); (ii) as a
stopgap only, raise `memory: 1G → 1.5G` to lengthen the interval between wedges
(masks, does not fix); (iii) add an external `autoheal`-style watcher to
`docker restart` on `unhealthy` (Docker does not auto-restart on unhealthy, only
on exit). (i) is the correct fix and needs profiling in its own packet.

**P3-adjacent — silence the :8095 401 poll** by injecting
`UMH_MESH_RELAY_SECRET` or gating the poll when the secret is absent (§5).

### Why NO compose/code patch ships with this diagnosis

The one change that would be *purely* behavior-preserving — raising the
healthcheck `timeout`/`retries` so a transient starve doesn't flip the container
unhealthy — would **mask** the real fault (the loop genuinely cannot serve
requests during the wedge; a longer probe timeout just hides a real outage from
Docker while the cockpit still gets 504s). That is worse than no change. Every
effective fix is behavior-adjacent. Per the packet's own rule ("If the right fix
is ambiguous or behavior-adjacent: ship the diagnosis doc alone with the fix
PROPOSED, not applied"), this diagnosis ships alone.

---

## 8. Reproduction safety record

- No load generator was run. The wedged state was already present and confirmed
  with **single** trivial `curl` probes (1 request each).
- `nproc` = 4; abort ceiling would be loadavg > 8.0. Observed loadavg during all
  probing stayed in the 1.6–3.7 range. No abort condition reached.
- All docker/curl introspection commands run `nice -n 15` where they could spin.
- One `docker restart` (required restoration), `nice -n 15`.
