<style>
:root {
  --bg: #f6f6f4;
  --surface: #ffffff;
  --surface-2: #efeeeb;
  --ink: #1a1c1e;
  --ink-2: #4b4f54;
  --ink-3: #767b82;
  --rule: #d9d7d1;
  --rule-2: #e7e5e0;
  --accent: #2f5fd0;          /* control-plane blue, used sparingly */
  --accent-soft: #e5ebfa;
  --mono-bg: #ececE8;

  /* severity — separate from accent, encodes state only */
  --crit: #b3261e;
  --crit-bg: #f9e3e1;
  --high: #b9591a;
  --high-bg: #f7e7da;
  --med: #8a6d1e;
  --med-bg: #f3ecd6;
  --low: #4b6b56;
  --low-bg: #e6eee9;

  /* classification chips */
  --cg: #2c6a4a;   --cg-bg: #e2efe8;
  --gf: #8a6d1e;   --gf-bg: #f3ecd6;
  --sd: #b3261e;   --sd-bg: #f9e3e1;
  --ro: #5a6068;   --ro-bg: #ececeb;
  --unc: #6b4fa0;  --unc-bg: #ece6f6;
  --dep: #7a6a5c;  --dep-bg: #efe9e2;
  --dm: #5a6068;   --dm-bg: #e8e8e6;

  --font-sans: "Söhne", "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  --font-mono: "Berkeley Mono", "SF Mono", "JetBrains Mono", ui-monospace, "Menlo", monospace;
  --maxw: 1120px;
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg: #16181b;
    --surface: #1d2024;
    --surface-2: #23272c;
    --ink: #e9eaec;
    --ink-2: #b3b8bf;
    --ink-3: #868c94;
    --rule: #33383e;
    --rule-2: #2a2e33;
    --accent: #7ea2f0;
    --accent-soft: #23304f;
    --mono-bg: #24282d;

    --crit: #f0938c; --crit-bg: #3a211f;
    --high: #e8ac7f; --high-bg: #372620;
    --med: #ddc274;  --med-bg: #332e1d;
    --low: #a3c9b2;  --low-bg: #1f2a23;

    --cg: #8fd3ac; --cg-bg: #1c2b23;
    --gf: #ddc274; --gf-bg: #332e1d;
    --sd: #f0938c; --sd-bg: #3a211f;
    --ro: #a2a8b0; --ro-bg: #262a2f;
    --unc: #bda9e8; --unc-bg: #292139;
    --dep: #c9b6a3; --dep-bg: #2f2820;
    --dm: #9aa0a8; --dm-bg: #24282d;
  }
}
:root[data-theme="light"] {
  --bg: #f6f6f4; --surface: #ffffff; --surface-2: #efeeeb; --ink: #1a1c1e;
  --ink-2: #4b4f54; --ink-3: #767b82; --rule: #d9d7d1; --rule-2: #e7e5e0;
  --accent: #2f5fd0; --accent-soft: #e5ebfa; --mono-bg: #ececE8;
  --crit: #b3261e; --crit-bg: #f9e3e1; --high: #b9591a; --high-bg: #f7e7da;
  --med: #8a6d1e; --med-bg: #f3ecd6; --low: #4b6b56; --low-bg: #e6eee9;
  --cg: #2c6a4a; --cg-bg: #e2efe8; --gf: #8a6d1e; --gf-bg: #f3ecd6;
  --sd: #b3261e; --sd-bg: #f9e3e1; --ro: #5a6068; --ro-bg: #ececeb;
  --unc: #6b4fa0; --unc-bg: #ece6f6; --dep: #7a6a5c; --dep-bg: #efe9e2;
  --dm: #5a6068; --dm-bg: #e8e8e6;
}
:root[data-theme="dark"] {
  --bg: #16181b; --surface: #1d2024; --surface-2: #23272c; --ink: #e9eaec;
  --ink-2: #b3b8bf; --ink-3: #868c94; --rule: #33383e; --rule-2: #2a2e33;
  --accent: #7ea2f0; --accent-soft: #23304f; --mono-bg: #24282d;
  --crit: #f0938c; --crit-bg: #3a211f; --high: #e8ac7f; --high-bg: #372620;
  --med: #ddc274; --med-bg: #332e1d; --low: #a3c9b2; --low-bg: #1f2a23;
  --cg: #8fd3ac; --cg-bg: #1c2b23; --gf: #ddc274; --gf-bg: #332e1d;
  --sd: #f0938c; --sd-bg: #3a211f; --ro: #a2a8b0; --ro-bg: #262a2f;
  --unc: #bda9e8; --unc-bg: #292139; --dep: #c9b6a3; --dep-bg: #2f2820;
  --dm: #9aa0a8; --dm-bg: #24282d;
}

* { box-sizing: border-box; }
body {
  background: var(--bg);
  color: var(--ink);
  font-family: var(--font-sans);
  font-size: 15.5px;
  line-height: 1.62;
  margin: 0;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}
.wrap { max-width: var(--maxw); margin: 0 auto; padding: 0 28px 120px; }

/* ---- masthead ---- */
.masthead {
  border-bottom: 2px solid var(--ink);
  padding: 52px 0 26px;
  margin-bottom: 12px;
}
.eyebrow {
  font-family: var(--font-mono);
  font-size: 11.5px;
  letter-spacing: 0.13em;
  text-transform: uppercase;
  color: var(--accent);
  margin: 0 0 18px;
  font-weight: 600;
}
h1 {
  font-size: clamp(28px, 4.2vw, 44px);
  line-height: 1.06;
  letter-spacing: -0.02em;
  font-weight: 680;
  margin: 0 0 18px;
  text-wrap: balance;
  max-width: 20ch;
}
.dek {
  font-size: 17px;
  color: var(--ink-2);
  max-width: 62ch;
  margin: 0 0 26px;
}
.meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 28px;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--ink-3);
}
.meta-row b { color: var(--ink-2); font-weight: 600; }

/* ---- verdict banner ---- */
.verdict {
  margin: 30px 0 8px;
  border: 1px solid var(--rule);
  border-left: 4px solid var(--crit);
  background: var(--surface);
  border-radius: 3px;
  padding: 20px 24px;
}
.verdict h2 { margin: 0 0 8px; border: 0; padding: 0; font-size: 15px; }
.verdict p { margin: 0; color: var(--ink-2); max-width: 84ch; }

/* ---- section headers ---- */
h2 {
  font-size: 13px;
  font-family: var(--font-mono);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink);
  font-weight: 700;
  margin: 62px 0 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--rule);
  display: flex;
  align-items: baseline;
  gap: 12px;
}
h2 .num {
  color: var(--accent);
  font-size: 12px;
}
h3 {
  font-size: 17px;
  letter-spacing: -0.01em;
  font-weight: 640;
  margin: 34px 0 12px;
}
h4 {
  font-size: 13px;
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--ink-2);
  margin: 26px 0 10px;
}
p { max-width: 82ch; }
a { color: var(--accent); text-decoration-thickness: 1px; text-underline-offset: 2px; }

code, .mono {
  font-family: var(--font-mono);
  font-size: 0.86em;
}
p code, li code, td code {
  background: var(--mono-bg);
  padding: 1px 5px;
  border-radius: 3px;
  color: var(--ink);
  white-space: nowrap;
}
.path { font-family: var(--font-mono); font-size: 0.84em; color: var(--ink-2); white-space: nowrap; }

/* ---- stat strip ---- */
.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1px;
  background: var(--rule);
  border: 1px solid var(--rule);
  border-radius: 4px;
  overflow: hidden;
  margin: 8px 0 4px;
}
.stat {
  background: var(--surface);
  padding: 16px 18px;
}
.stat .k {
  font-family: var(--font-mono);
  font-size: 10.5px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--ink-3);
  margin-bottom: 7px;
}
.stat .v {
  font-size: 27px;
  font-weight: 660;
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
  line-height: 1;
}
.stat .v small { font-size: 14px; color: var(--ink-3); font-weight: 500; }
.stat.crit .v { color: var(--crit); }
.stat.high .v { color: var(--high); }
.stat.good .v { color: var(--cg); }

/* ---- tables ---- */
.tablewrap {
  overflow-x: auto;
  border: 1px solid var(--rule);
  border-radius: 5px;
  margin: 18px 0 8px;
  background: var(--surface);
}
table {
  border-collapse: collapse;
  width: 100%;
  font-size: 13px;
  min-width: 720px;
}
thead th {
  position: sticky; top: 0;
  background: var(--surface-2);
  text-align: left;
  font-family: var(--font-mono);
  font-size: 10.5px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--ink-2);
  font-weight: 600;
  padding: 11px 14px;
  border-bottom: 1.5px solid var(--rule);
  white-space: nowrap;
  z-index: 2;
}
tbody td {
  padding: 10px 14px;
  border-bottom: 1px solid var(--rule-2);
  vertical-align: top;
  color: var(--ink-2);
}
tbody tr:last-child td { border-bottom: 0; }
tbody tr:hover td { background: var(--surface-2); }
td b, td strong { color: var(--ink); font-weight: 620; }
.num-col { font-variant-numeric: tabular-nums; text-align: right; white-space: nowrap; }
table.compact { font-size: 12.5px; }
table.compact td, table.compact th { padding: 8px 12px; }

/* ---- chips ---- */
.chip {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.03em;
  font-weight: 600;
  text-transform: uppercase;
  padding: 2px 7px;
  border-radius: 3px;
  white-space: nowrap;
  line-height: 1.5;
}
.c-cg  { color: var(--cg);  background: var(--cg-bg); }
.c-gf  { color: var(--gf);  background: var(--gf-bg); }
.c-sd  { color: var(--sd);  background: var(--sd-bg); }
.c-ro  { color: var(--ro);  background: var(--ro-bg); }
.c-unc { color: var(--unc); background: var(--unc-bg); }
.c-dep { color: var(--dep); background: var(--dep-bg); }
.c-dm  { color: var(--dm);  background: var(--dm-bg); }

.sev {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  padding: 2px 8px;
  border-radius: 3px;
  white-space: nowrap;
}
.s-crit { color: #fff; background: var(--crit); }
.s-high { color: #fff; background: var(--high); }
.s-med  { color: var(--med); background: var(--med-bg); border: 1px solid var(--med); }
.s-low  { color: var(--low); background: var(--low-bg); border: 1px solid var(--low); }
@media (prefers-color-scheme: dark) {
  .s-crit, .s-high { color: #16181b; }
}
:root[data-theme="dark"] .s-crit, :root[data-theme="dark"] .s-high { color: #16181b; }
:root[data-theme="light"] .s-crit, :root[data-theme="light"] .s-high { color: #fff; }

/* ---- side-door cards ---- */
.door {
  border: 1px solid var(--rule);
  border-left: 4px solid var(--sd);
  border-radius: 4px;
  background: var(--surface);
  padding: 18px 20px;
  margin: 14px 0;
}
.door.high { border-left-color: var(--high); }
.door.med  { border-left-color: var(--med); }
.door-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.door-head .rank {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--ink-3);
  font-weight: 600;
}
.door-head .title { font-size: 15.5px; font-weight: 640; color: var(--ink); }
.door p { margin: 6px 0; font-size: 13.5px; }
.door .ev {
  font-family: var(--font-mono);
  font-size: 11.5px;
  color: var(--ink-3);
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed var(--rule);
  word-break: break-word;
}
.door .ev b { color: var(--ink-2); }

/* ---- legend ---- */
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 18px;
  padding: 14px 16px;
  background: var(--surface);
  border: 1px solid var(--rule);
  border-radius: 4px;
  margin: 8px 0 18px;
  font-size: 12px;
  color: var(--ink-2);
}
.legend .item { display: flex; align-items: center; gap: 7px; }

ul.tight { margin: 8px 0; padding-left: 22px; }
ul.tight li { margin: 5px 0; max-width: 82ch; }
.note {
  font-size: 13px;
  color: var(--ink-3);
  border-left: 2px solid var(--rule);
  padding-left: 14px;
  margin: 14px 0;
  max-width: 80ch;
}
.callout {
  background: var(--accent-soft);
  border: 1px solid var(--rule);
  border-radius: 4px;
  padding: 14px 18px;
  margin: 16px 0;
  font-size: 13.5px;
  color: var(--ink-2);
}
.callout b { color: var(--ink); }
hr.soft { border: 0; border-top: 1px solid var(--rule-2); margin: 40px 0; }
</style>

<div class="wrap">

<header class="masthead">
  <p class="eyebrow">UMH Convergence Audit · Workstream C (C1–C3) + A · Execution-Spine Compliance</p>
  <h1>Governed-Mutation Spine Compliance Report</h1>
  <p class="dek">A path-by-path audit of every state-changing surface in UMH against the canonical governed-mutation contract. Covers the Python mutation core, ~140 FastAPI cockpit route modules, the 8 Hono TS routes, services, cron, node mesh, Windows runtime nodes, write-capable adapters, the Discord approval channel, projection writebacks, and memory/reality writes.</p>
  <div class="meta-row">
    <span><b>Audit date</b> 2026-07-03</span>
    <span><b>Repo</b> /opt/OS/.claude/worktrees/umh-convergence-audit</span>
    <span><b>Sources</b> C1 · C2 · C3 · A ledgers</span>
    <span><b>Access</b> read-only</span>
  </div>
</header>

<div class="verdict">
  <h2>Verdict</h2>
  <p>The canonical spine exists, is well-built, and is <b>densely adopted on the deployed HTTP surface</b> — 360 <code>governed_mutation()</code> call sites, and the pre-commit gate reports the route/service layer clean. But the contract "every state change routes through governed mutation, no exceptions" (PLATFORM_SPEC §1) is <b>not upheld below the transport layer</b>. The single wrapper that fronts every governed route <b>fails open</b> to direct ungoverned execution when the control-plane daemon is down; the parallel Hono write surface records governed proof artifacts for <b>mutations it never executes</b>; and an <b>unauthenticated node-mesh relay</b> can dispatch arbitrary remote actuation with no verdict when a single env var is unset. Beneath these sit four rival execution spines, four parallel approval state machines, a whole cron plane that mutates Neon/Notion/calendar directly every 5–15 minutes, and two governed code paths that are <b>silently broken by AttributeError</b>. The transport layer is the strongest-converged surface; the bypasses live below it, beside it, and inside the wrapper itself.</p>
</div>

<div class="stats">
  <div class="stat"><div class="k">Python API files</div><div class="v">143</div></div>
  <div class="stat"><div class="k">HTTP handlers</div><div class="v">1,306</div></div>
  <div class="stat"><div class="k">Mutation handlers</div><div class="v">320</div></div>
  <div class="stat good"><div class="k">governed_mutation sites</div><div class="v">360</div></div>
  <div class="stat crit"><div class="k">Critical spine gaps</div><div class="v">6</div></div>
  <div class="stat high"><div class="k">High spine gaps</div><div class="v">14</div></div>
</div>

<h2><span class="num">01</span> Canonical spine &amp; rival-spine inventory</h2>

<h3>The canonical governed-mutation path (as wired)</h3>
<p>The governed spine is real and its transport-layer adoption is genuine — traced positive controls confirm Python call sites pass closures that perform the actual write, not no-ops (C2 F11).</p>

<div class="tablewrap">
<table class="compact">
<thead><tr><th>Stage</th><th>Location</th><th>Responsibility</th></tr></thead>
<tbody>
<tr><td>HTTP route handler</td><td class="path">transports/api/cockpit_*_routes.py (~90 files)</td><td>Builds <code>execute_fn</code> closure, declares <code>mutation_name</code></td></tr>
<tr><td><b>governed_mutation()</b></td><td class="path">transports/api/governed.py:65</td><td>Canonical HTTP wrapper → <code>MutationRequest</code></td></tr>
<tr><td>MutationRouter.execute()</td><td class="path">substrate/organism/mutation_router.py:93</td><td>Registry lookup, rejects unregistered names, builds <code>ActionEnvelope</code></td></tr>
<tr><td>GovernedExecutionSpine.submit()</td><td class="path">substrate/organism/governed_spine.py:197</td><td>Governance check, approval gate, retry, proof, verify, rollback, journal, EventSpine, learning</td></tr>
<tr><td>Spine + registry ownership</td><td class="path">substrate/organism/daemon.py:302,273</td><td>Owned by the organism daemon singleton</td></tr>
<tr><td>Autonomous policy wrapper</td><td class="path">substrate/organism/autonomous_action_gateway.py:128,174</td><td>Wraps <code>spine.submit</code> for autonomous lane</td></tr>
</tbody>
</table>
</div>

<div class="note"><b>Ground-truth correction (C1).</b> <code>governed_mutation()</code> is defined <b>only</b> at <span class="path">transports/api/governed.py:65</span> — not in <code>governed_spine.py</code> as prior docs state. <code>governed_spine.py</code> contains the <code>GovernedExecutionSpine</code> class only. Verified: <code>grep -rn "def governed_mutation"</code> → single hit. (GAP-C1-013)</p></div>

<h3>Four rival spines — who calls each</h3>
<p>Four distinct classes named or acting as an "execution spine" coexist. Only the first is the governed mutation gateway; the others are parallel pipelines or a name-colliding data model. This directly extends A/F8's rival-spine finding with call-site evidence.</p>

<div class="tablewrap">
<table>
<thead><tr><th>Spine</th><th>Path · lines</th><th>Callers</th><th>Through governed_mutation?</th></tr></thead>
<tbody>
<tr>
  <td><b>GovernedExecutionSpine</b><br><span class="chip c-cg">canonical</span></td>
  <td class="path">substrate/organism/governed_spine.py · 889</td>
  <td>daemon.py, mutation_router.py, autonomous_action_gateway.py, workload_runner (dead wiring), 9 test files</td>
  <td><b>IS the canonical spine</b></td>
</tr>
<tr>
  <td><b>ConcreteExecutionSpine</b> (async 8-stage)<br><span class="chip c-sd">side-door</span></td>
  <td class="path">substrate/execution/spine.py · 522</td>
  <td>contracts/execution_protocol.py, execution/runtime/execution_spine.py (re-export), substrate/__init__.py, operator/intent_router.py, tests/test_spine_full.py</td>
  <td><b>No.</b> Writes <code>ConversationMemory.store</code> + <code>AgentMemory.log</code> directly (spine.py:389–427) with no envelope</td>
</tr>
<tr>
  <td><b>ExecutionSpine</b> (legacy sync <code>.run</code>)<br><span class="chip c-dep">deprecated · LIVE</span></td>
  <td class="path">substrate/execution/runtime/execution_spine.py · 228</td>
  <td><b>services/discord_bot.py, services/discord_message_handlers.py</b> — live production Discord path</td>
  <td><b>No.</b> Own AuthorityEngine queue (:113–127), direct memory writes (:156–201), <code>storage.put</code> session persistence (:206–210). Self-labels "legacy" yet ships</td>
</tr>
<tr>
  <td><b>Event</b> (bridge event model)<br><span class="chip c-ro">read-only</span></td>
  <td class="path">substrate/execution/bridge/event_spine.py · 206</td>
  <td>services/discord_bot.py, services/discord_message_handlers.py</td>
  <td>N/A — immutable data model. <b>Name-collides</b> with the canonical <code>substrate/organism/event_spine.py</code> pub/sub bus (A/F8, GAP-A-009)</td>
</tr>
<tr>
  <td><b>ExecutionPipeline</b> (5th path)<br><span class="chip c-gf">fragmented</span></td>
  <td class="path">substrate/execution/pipeline.py · 557</td>
  <td>worker_cell.py, daemon.py, sockets/view_socket.py, view/broadcaster.py, transports/api/app.py</td>
  <td><b>No.</b> Parallel full pipeline (understanding → mastery gate → governance → execute → proof → memory); own trace store; never emits <code>ActionEnvelope</code></td>
</tr>
</tbody>
</table>
</div>

<div class="callout">
<b>Deployment reality (A/F3).</b> The single live HTTP state authority is <span class="path">services/operator_api.py</span> on :8091 (nginx target). <code>transports/api/app.py</code> is undeployed yet its <code>_organism</code> singleton is imported by the Discord container; <code>transports/api/operator.py</code> is a dead near-duplicate that <b>NameErrors at import</b> (<code>os</code> used at :7 before <code>import os</code> at :12); the Hono <code>server.ts</code> stack is undeployed. ARCHITECTURE.md:434's "one API" claim does not match deployment. (GAP-A-004, GAP-A-013)
</div>

<h2><span class="num">02</span> THE compliance matrix</h2>

<div class="legend">
  <span class="item"><span class="chip c-cg">CG</span> canonical-governed</span>
  <span class="item"><span class="chip c-gf">GF</span> governed-but-fragmented</span>
  <span class="item"><span class="chip c-ro">RO</span> read-only</span>
  <span class="item"><span class="chip c-sd">SD</span> mutation-side-door</span>
  <span class="item"><span class="chip c-unc">UNC</span> unclear</span>
  <span class="item"><span class="chip c-dep">DEP</span> deprecated-shim</span>
  <span class="item"><span class="chip c-dm">DM</span> dormant</span>
</div>

<p>Every distinct write surface is classified below, grouped by tier. Depth: <b>FT</b> = full-trace of handler bodies/registrations; <b>G</b> = grep-evidenced. The per-file FastAPI verdicts (143 files) are rolled up in §2.7; the surfaces carrying the non-CG risk are enumerated individually.</p>

<h3>2.1 — Python mutation core (organism runtimes &amp; rival spines)</h3>
<div class="tablewrap">
<table>
<thead><tr><th>Path / surface</th><th>Mutation handlers</th><th>Class</th><th>Depth</th><th>Evidence · required remediation</th></tr></thead>
<tbody>
<tr><td class="path">governed_spine.py:197</td><td>submit / approve / reject / _execute / _verify / _rollback</td><td><span class="chip c-cg">CG</span></td><td>FT</td><td>Single mutation gateway; journal + proof + learning. <b>Keep.</b> Bound idempotency map (GAP-C1-015)</td></tr>
<tr><td class="path">mutation_router.py:93</td><td>execute / _build_envelope</td><td><span class="chip c-cg">CG</span></td><td>FT</td><td>Registry-validated choke point → <code>spine.submit</code>. <b>Keep.</b></td></tr>
<tr><td class="path">autonomous_action_gateway.py:174</td><td>submit_envelope / propose_action / block_direct_mutation</td><td><span class="chip c-cg">CG</span></td><td>FT</td><td>Policy layer in front of spine. <b>Keep.</b></td></tr>
<tr><td class="path">workload_runner.py:216</td><td>run_workload_via_gateway / create_envelope</td><td><span class="chip c-cg">CG</span></td><td>FT</td><td>Envelope path via gateway; <b>falls back to ungoverned</b> <code>run_workload</code> when gateway unwired</td></tr>
<tr><td class="path">workload_runner.py:242</td><td>run_workload</td><td><span class="chip c-gf">GF</span></td><td>FT</td><td><code>set_governed_spine</code> stores a ref (:170) that is <b>never read</b>; daemon wires it (daemon.py:327) — dead wiring. Route mutation-capable workloads through spine by default (GAP-C1-008)</td></tr>
<tr><td class="path">governed_work_runtime.py:211</td><td>submit_work</td><td><span class="chip c-sd">SD</span> · <b>BROKEN</b></td><td>FT</td><td>Parallel governance stack; calls nonexistent <code>packet_engine.create_from_intent</code> (:232) — <b>AttributeError swallowed</b> (:236); real packet never created. Fix to <code>create_packet_from_intent</code> (GAP-C1-001)</td></tr>
<tr><td class="path">governed_work_runtime.py:277</td><td>approve_work / reject_work / execute_work / cancel_work</td><td><span class="chip c-gf">GF</span></td><td>FT</td><td>Approval via ExecutionCoordinator plan state machine, not <code>spine.approve()</code>; reaches into private <code>_plan_store</code>. Collapse into one approval authority (GAP-C1-004)</td></tr>
<tr><td class="path">execution_coordinator.py:~860–1010</td><td>create_plan / approve_plan / deny_plan / enqueue_plan / dispatch_next / mark_*</td><td><span class="chip c-gf">GF</span></td><td>FT</td><td>Second full approval + lifecycle state machine with own plan store (GAP-C1-004)</td></tr>
<tr><td class="path">execution/pipeline.py:142</td><td>submit_signal</td><td><span class="chip c-gf">GF</span></td><td>FT</td><td>Third full pipeline w/ mastery gate, own proof + memory promotion; no ActionEnvelope (GAP-C1-004)</td></tr>
<tr><td class="path">worker_cell.py:19</td><td>execute</td><td><span class="chip c-gf">GF</span></td><td>FT</td><td>Routes <code>WorkerSpec</code> through ExecutionPipeline with adapter (default "shell") — mutation-capable, spine-bypassing</td></tr>
<tr><td class="path">command_runtime.py:1096</td><td>submit + approve_command / reject_command</td><td><span class="chip c-sd">SD</span></td><td>FT</td><td>Fourth "canonical entry"; non-approval commands executed inline (:1172) without envelope; own JSONL approval lifecycle (GAP-C1-004, GAP-C1-011)</td></tr>
<tr><td class="path">command_runtime.py:887</td><td>CommandRouter._process_approval</td><td><span class="chip c-sd">SD</span> · <b>BROKEN</b></td><td>FT</td><td>Calls nonexistent <code>UniversalWorkQueue.update_status</code> (queue has <code>update_packet_status</code>:237) — <b>AttributeError swallowed</b>; every packet approve/reject returns error (GAP-C1-002)</td></tr>
<tr><td class="path">command_runtime.py:738,782,713</td><td>_route_switch_profile / _route_create_objective / _route_schedule</td><td><span class="chip c-sd">SD</span></td><td>FT</td><td>Direct subsystem writes, <code>approval_state="not_required"</code>; reaches private <code>loop._candidate_queue</code>. Produce ActionEnvelopes (GAP-C1-011)</td></tr>
<tr><td class="path">command_runtime.py:1025</td><td>CommandHistory.update_status</td><td><span class="chip c-sd">SD</span></td><td>FT</td><td>Rewrites JSONL non-atomically via <code>open(path,"w")</code> — crash mid-write corrupts command state authority. Use tempfile+os.replace (GAP-C1-016)</td></tr>
<tr><td class="path">work_packet_engine.py:67,617</td><td>create_packet_from_intent / update_packet_status / persist / link_*</td><td><span class="chip c-sd">SD</span></td><td>FT</td><td>Direct JSONL packet store writes; lifecycle validated but no spine/envelope</td></tr>
<tr><td class="path">work_packet_engine.py:640</td><td>_record_outcome</td><td><span class="chip c-sd">SD</span></td><td>FT</td><td>Writes <code>InstanceRealityModel(user_id="system").record(...)</code> directly — bypasses CanonicalRealityWritePath + trust gate; hardcodes "system" (GAP-C1-007)</td></tr>
<tr><td class="path">universal_work_queue.py:63–291</td><td>ingest_* / update_packet_status / mark_resolved / suppress_duplicates</td><td><span class="chip c-sd">SD</span></td><td>G</td><td>Second writer to the same work-packet state; own <code>_save</code></td></tr>
<tr><td class="path">workcell_protocol.py:266</td><td>process_next (executes arbitrary prompt via RuntimeAdapter)</td><td><span class="chip c-sd">SD</span></td><td>FT</td><td>No envelope, no risk class, no approval; adapter may be shell/claude_code. Wrap in ActionEnvelope → spine (GAP-C1-005)</td></tr>
<tr><td class="path">workcell_daemon.py:117,251</td><td>run / _run_cycle / schedule_periodic / _persist_state</td><td><span class="chip c-sd">SD</span></td><td>G</td><td>Drives <code>process_next</code> continuously; periodic scheduler injects work with no gate (GAP-C1-005)</td></tr>
<tr><td class="path">workload_placement_policy.py:222</td><td>select_placement / persist_decision</td><td><span class="chip c-sd">SD</span></td><td>FT</td><td>JSONL decision-log append; hardcodes device ids "vps"/"windows_beast"/"fly_cockpit" (:105–125) — instance leak (GAP-C1-017)</td></tr>
<tr><td class="path">operator_loop_runtime.py:254</td><td>decide / approve / reject / execute</td><td><span class="chip c-dm">DM</span></td><td>G</td><td>Pure delegation to GovernedWorkRuntime; no callers found in transports/services/scripts</td></tr>
<tr><td class="path">governed_execution_runtime.py:117–666</td><td>(all)</td><td><span class="chip c-ro">RO</span></td><td>FT</td><td>Self-documented "no mutation, read-only coordination"</td></tr>
<tr><td class="path">execution/spine.py:388–433</td><td>ConcreteExecutionSpine — mandatory memory writes</td><td><span class="chip c-sd">SD</span></td><td>FT</td><td>Conversation + agent memory writes on every execution outside governed mutation and CanonicalWritePath (GAP-C1-018)</td></tr>
<tr><td class="path">execution/runtime/execution_spine.py:86</td><td>ExecutionSpine.run (legacy)</td><td><span class="chip c-dep">DEP</span> · LIVE</td><td>FT</td><td>Live in Discord services; own AuthorityEngine queue + direct memory writes + <code>storage.put</code>. Migrate hot path, then delete (GAP-C1-006)</td></tr>
<tr><td class="path">reality_model/canonical_reality_write.py:60</td><td>apply_mutation / _write_observation</td><td><span class="chip c-gf">GF</span></td><td>FT</td><td>Validates shape/source/confidence + trust gate then <code>InstanceRealityModel.record</code>; explicitly "does NOT call governance (caller's responsibility)" — policy engine optional at the reality choke point (GAP-C1-009)</td></tr>
<tr><td class="path">deploy_verification_worker.py:527 · projection_certification.py:295</td><td>direct InstanceRealityModel.record</td><td><span class="chip c-sd">SD</span></td><td>G</td><td>Canonical-reality writes bypassing the validated write path (GAP-C1-007)</td></tr>
</tbody>
</table>
</div>

<h3>2.2 — FastAPI cockpit routes: the non-compliant surfaces (of 143 files)</h3>
<p>Of 143 Python API files, <b>60 are fully CG</b>, 51 read-only (incl. 1 read-mostly), 14 non-route support — and <b>18 carry governance risk</b> (SD/SD-latent 9 · SD-GF 2 · GF 2 · UNC 4 · DEP 1; per-file class counts from the C2 compliance matrix, which sums to 143). The highest-risk files are tabled below. Note: <code>governed.py</code> and <code>cockpit_settings_mutations.py</code> are classed NR (non-route support) at file level in the matrix but are shown here with their module-level risk class (fail-open wrapper; third governance pipeline):</p>
<div class="tablewrap">
<table>
<thead><tr><th>File (transports/api/)</th><th class="num-col">H</th><th class="num-col">M</th><th class="num-col">Gov</th><th>Class</th><th>Why</th></tr></thead>
<tbody>
<tr><td class="path">governed.py</td><td class="num-col">0</td><td class="num-col">0</td><td class="num-col">2</td><td><span class="chip c-sd">SD</span></td><td>Canonical wrapper containing the <b>ungoverned fail-open fallback</b> (§3 lead)</td></tr>
<tr><td class="path">cockpit_workstation_control_routes.py</td><td class="num-col">28</td><td class="num-col">14</td><td class="num-col">10</td><td><span class="chip c-sd">SD</span></td><td>4 remote-terminal mutations bypass the spine entirely (§3)</td></tr>
<tr><td class="path">cockpit_autonomous_routes.py</td><td class="num-col">30</td><td class="num-col">7</td><td class="num-col">2</td><td><span class="chip c-sd">SD</span></td><td>5 of 7 ungoverned (cadence set-mode direct attr write; mislabeled merge-verify) (GAP-C2-007, GAP-C2-009)</td></tr>
<tr><td class="path">cockpit_workspace_routes.py</td><td class="num-col">15</td><td class="num-col">2</td><td class="num-col">2</td><td><span class="chip c-sd">SD-latent</span></td><td>Both file-write mutations use <b>unregistered</b> <code>filesystem_write</code>; remote-write over SSH PowerShell (GAP-C2-003)</td></tr>
<tr><td class="path">workstation.py</td><td class="num-col">6</td><td class="num-col">2</td><td class="num-col">2</td><td><span class="chip c-sd">SD-latent</span></td><td>Unregistered <code>workstation_execute</code>, <code>config_update</code> (GAP-C2-003)</td></tr>
<tr><td class="path">cockpit_proof_inspector_routes.py</td><td class="num-col">9</td><td class="num-col">2</td><td class="num-col">2</td><td><span class="chip c-sd">SD-latent</span></td><td>Unregistered <code>proof_review</code> (GAP-C2-003)</td></tr>
<tr><td class="path">cockpit_recovery_dashboard_routes.py</td><td class="num-col">8</td><td class="num-col">1</td><td class="num-col">2</td><td><span class="chip c-sd">SD-latent</span></td><td>Unregistered <code>recovery_action</code> (GAP-C2-003)</td></tr>
<tr><td class="path">cockpit_core_bootstrap_routes.py</td><td class="num-col">4</td><td class="num-col">1</td><td class="num-col">1</td><td><span class="chip c-sd">SD-latent</span></td><td>Unregistered <code>config_update</code> (GAP-C2-003)</td></tr>
<tr><td class="path">cockpit_chat_routes.py</td><td class="num-col">11</td><td class="num-col">6</td><td class="num-col">4</td><td><span class="chip c-sd">SD</span></td><td><code>/chat/upload</code> ungoverned direct file write to <code>data/chat_media/</code> (GAP-C2-011)</td></tr>
<tr><td class="path">cockpit_operator_loop_routes.py</td><td class="num-col">82</td><td class="num-col">23</td><td class="num-col">15</td><td><span class="chip c-gf">GF</span></td><td>17 registrations delegate to ungoverned handler libraries (§2.3) (GAP-C2-005)</td></tr>
<tr><td class="path">approval_routes.py</td><td class="num-col">0*</td><td class="num-col">0*</td><td class="num-col">0</td><td><span class="chip c-gf">GF</span></td><td>Direct <code>ApprovalInterceptService</code> writes (defensible — approval is the control — but no spine trace)</td></tr>
<tr><td class="path">cockpit_settings_mutations.py</td><td class="num-col">0</td><td class="num-col">0</td><td class="num-col">0</td><td><span class="chip c-gf">GF</span></td><td>Third governance pipeline: own validate→constrain→approval-gate→persist→audit, overlapping registered <code>settings_update</code> (GAP-C2-014)</td></tr>
<tr><td class="path">operator.py</td><td class="num-col">11</td><td class="num-col">4</td><td class="num-col">4</td><td><span class="chip c-dep">DEP</span></td><td>NameError at import; duplicates deployed operator_api.py (GAP-C2-008 / GAP-A-013)</td></tr>
<tr><td class="path">cockpit_organism_routes.py</td><td class="num-col">43</td><td class="num-col">10</td><td class="num-col">9</td><td><span class="chip c-cg">CG</span></td><td>All mutations governed; but <code>POST /organism/signal</code> lacks the operator-role dep its siblings carry (GAP-C2-010)</td></tr>
</tbody>
</table>
</div>
<p class="note">4 files (<code>cockpit_context_assimilation_routes.py</code>, <code>cockpit_device_routes.py</code>, <code>cockpit_push_routes.py</code>, <code>cockpit_reality_model_routes.py</code>) are <span class="chip c-unc">UNC</span> — they carry <code>governed_mutation</code> calls with no visible HTTP mutation registration (mutation vector likely GET or WebSocket), marked UNVERIFIED rather than guessed. <code>0*</code> = handler-library module (functions registered by another file's <code>add_api_route</code>).</p>

<h3>2.3 — Operator-loop handler libraries (parallel governance)</h3>
<div class="tablewrap">
<table class="compact">
<thead><tr><th>Module</th><th>Gov</th><th>Writes directly to</th><th>Class</th></tr></thead>
<tbody>
<tr><td class="path">execcoord_routes.py</td><td class="num-col">0</td><td><code>ExecutionCoordinator</code> (create/approve/deny/enqueue/dispatch)</td><td><span class="chip c-sd">SD</span>/<span class="chip c-gf">GF</span></td></tr>
<tr><td class="path">executor_routes.py</td><td class="num-col">0</td><td><code>ExecutorRuntime</code> — <b>auto-approves fail-open</b> if intercept service missing (:1242)</td><td><span class="chip c-sd">SD</span>/<span class="chip c-gf">GF</span></td></tr>
<tr><td class="path">agent_routes.py</td><td class="num-col">0</td><td><code>AgentExecutor</code> arbitrary task submit, no ActionEnvelope</td><td><span class="chip c-sd">SD</span></td></tr>
<tr><td class="path">approval_routes.py</td><td class="num-col">0</td><td><code>ApprovalInterceptService</code> approve/reject</td><td><span class="chip c-gf">GF</span></td></tr>
</tbody>
</table>
</div>

<h3>2.4 — Hono TypeScript surface (undeployed, contract-breaking)</h3>
<p>All 33 TS mutation handlers route through <code>governedMutation()</code> — but the bridge's <code>execute_fn</code> <b>echoes the payload and does nothing</b> (§3). The spine records a successful governed mutation + proof artifact while no state changes. Server is not in docker-compose/systemd/process table — <span class="chip c-dm">DORMANT</span> with a latent contract-integrity defect (GAP-C2-002, GAP-C2-012).</p>
<div class="tablewrap">
<table class="compact">
<thead><tr><th>File (transports/api/http/)</th><th class="num-col">H</th><th class="num-col">M</th><th>Verdict</th></tr></thead>
<tbody>
<tr><td class="path">routes/organism.ts</td><td class="num-col">99</td><td class="num-col">24</td><td>governed-but-effect-free; 3 lack operatorGuard (:416,441,449)</td></tr>
<tr><td class="path">routes/execution.ts</td><td class="num-col">7</td><td class="num-col">4</td><td>effect-free; all <code>state_mutate</code> incl. stop/kill; no operatorGuard</td></tr>
<tr><td class="path">routes/chat.ts</td><td class="num-col">3</td><td class="num-col">2</td><td>effect-free</td></tr>
<tr><td class="path">routes/config.ts · settings.ts · governance.ts</td><td class="num-col">15</td><td class="num-col">3</td><td>effect-free</td></tr>
<tr><td class="path">routes/knowledge.ts · system.ts</td><td class="num-col">12</td><td class="num-col">0</td><td>read-only</td></tr>
</tbody>
</table>
</div>

<h3>2.5 — Services, cron, and background paths</h3>
<div class="tablewrap">
<table>
<thead><tr><th>Path / surface</th><th>Mutation surface</th><th>Class</th><th>Evidence · remediation</th></tr></thead>
<tbody>
<tr><td class="path">services/discord_bot_commands.py</td><td>93 <code>cmd_</code> handlers; 6 governed_mutation</td><td><span class="chip c-sd">SD</span></td><td><code>gws.send_email()</code> (:546,654) &amp; calendar create (:1092) run <b>outside</b> governance; only the bookkeeping UPDATE is wrapped (GAP-C3-003). 3,113-line god file (GAP-C3-019)</td></tr>
<tr><td class="path">services/operator_api.py</td><td>4 own mutations + background tick loop</td><td><span class="chip c-gf">GF</span></td><td>Governed but all <code>mutation_name="state_mutate"</code> — no per-capability granularity (GAP-C3-015)</td></tr>
<tr><td class="path">services/cc_webhook_receiver.py</td><td>/cc-reply, /cc-prompt, /mfa-challenge → tmux CC session injection</td><td><span class="chip c-sd">SD</span></td><td>Binds <b>0.0.0.0:8765</b> with zero auth; carries MFA codes; second approval channel (§3, GAP-C3-005)</td></tr>
<tr><td class="path">scripts/agent_task_executor.py</td><td>tasks → CognitiveLoop → Notion → AgentMemory (5min cron)</td><td><span class="chip c-sd">SD</span></td><td>DB + Notion mutation + LLM output persisted, no governed_mutation, no proof (GAP-C3-006, GAP-C3-016)</td></tr>
<tr><td class="path">scripts/calendar_invite_handler.py</td><td>Auto-accept/decline external invites (15min cron)</td><td><span class="chip c-sd">SD</span></td><td>LLM-in-the-loop external L1 mutation on <code>confidence=='high'</code>, no approval envelope (§3, GAP-C3-007)</td></tr>
<tr><td class="path">scripts/scheduled/nightly_maintenance.sh</td><td><code>claude -p --allowedTools "Bash Read Write Edit …" --add-dir /opt/OS</code> (2am cron)</td><td><span class="chip c-sd">SD</span></td><td>Autonomous write+shell agent on production repo; only constraint is $0.50 budget (§3, GAP-C3-004)</td></tr>
<tr><td class="path">scripts/{call_prep,noshow_detector,notion_tasks_sync,notion_sync_poller}.py</td><td>Direct <code>INSERT/UPDATE events</code> + Notion PATCH (15min)</td><td><span class="chip c-sd">SD</span></td><td>Parallel ungoverned mutation plane; migrate behind signal ingress (GAP-C3-006)</td></tr>
<tr><td class="path">services/{goal_api,higgsfield_webhook,local_bridge_server}.py</td><td>Flask endpoints; tmux injection</td><td><span class="chip c-dm">DM</span></td><td>Unauthenticated, not in compose — one <code>python3</code> from a live side door (GAP-C3-014)</td></tr>
<tr><td class="path">services/overnight_scrape.py</td><td>4am cron → apify_scraper (missing) + 01_Inbox/03_CRM (missing)</td><td><span class="chip c-dm">DM/broken</span></td><td>Broken chain still fires nightly (GAP-C3-012)</td></tr>
<tr><td class="path">scripts/rotate_secrets.sh</td><td>Token rotation via openssl + 1Password (monthly)</td><td><span class="chip c-cg">CG</span></td><td>Governed for its domain with audit log</td></tr>
</tbody>
</table>
</div>

<h3>2.6 — Node mesh, Windows nodes, adapters, Discord, projections</h3>
<div class="tablewrap">
<table>
<thead><tr><th>Path / surface</th><th>Finding</th><th>Class</th><th>Evidence · remediation</th></tr></thead>
<tbody>
<tr><td class="path">transports/node_mesh/server.py:889</td><td>HTTP relay <code>/dispatch</code> — <code>capability.execute</code> to any node</td><td><span class="chip c-sd">SD</span></td><td><b>Fail-open when relay secret unset</b>; no risk_class, no verdict in payload (§3, GAP-C3-001, GAP-C3-009)</td></tr>
<tr><td class="path">transports/node_mesh/integration/handlers.py:56</td><td>NodeCapabilityHandler sends <code>governance_verdict_id</code> + <code>trace_id</code></td><td><span class="chip c-cg">CG</span></td><td>The governed dispatch path — control-plane side is correct</td></tr>
<tr><td class="path">nodes/windows/umh_node/client.py:452</td><td><code>risk_class = params.get("risk_class", "REVERSIBLE_WRITE")</code></td><td><span class="chip c-gf">GF</span></td><td>Risk is <b>caller-declared</b>; <code>governance_verdict_id</code> transmitted but <b>never read/validated</b> on the node (GAP-C3-002)</td></tr>
<tr><td class="path">nodes/windows/umh_node/governance.py:31</td><td><code>validate_request</code> shell/fs allowlist</td><td><span class="chip c-gf">GF</span></td><td>Shell check only <code>command.split()[0]</code>; fs check unnormalized <code>startswith</code> — <code>..</code> traversal escapes (GAP-C3-013)</td></tr>
<tr><td class="path">nodes/windows/umh_node/adapters/*</td><td>shell/fs/desktop/container actuation</td><td><span class="chip c-gf">GF</span></td><td>Raw subprocess throughout; <code>nodes/</code> <b>not</b> in CPU-gate GATED_DIRS (GAP-C3-011)</td></tr>
<tr><td class="path">adapters/github/github_operations.py</td><td>PRs/branches/merges via gh CLI</td><td><span class="chip c-cg">CG</span></td><td><b>Best-in-class:</b> emits ActionEnvelope <code>require_approval=True</code>, consumed via governed_mutation. Hardcoded "antonyfmunoz/OS" default (GAP-C3-018)</td></tr>
<tr><td class="path">adapters/google_workspace/gws_connector.py</td><td>Calendar/tasks/email/Drive; <code>send_email</code>:1074</td><td><span class="chip c-gf">GF</span></td><td>CPU gate only; no policy/approval/credential gate — enables the discord/cron side-doors above (GAP-C3-003)</td></tr>
<tr><td class="path">adapters/notion/notion_sync.py</td><td>Pages/DBs via raw requests.post/patch</td><td><span class="chip c-gf">GF</span></td><td>Side-door when called from cron (GAP-C3-006)</td></tr>
<tr><td class="path">adapters/tool_adapters/* (shell,git,fs,tmux)</td><td>Local actuation with deny-rules + risk classify</td><td><span class="chip c-gf">GF</span></td><td>Deny-list not allow-list; no approval in adapter (approval depends on socket caller)</td></tr>
<tr><td class="path">transports/discord/approval_bridge.py:68</td><td>Buttons → OperatorApprovalGate claim/resolve</td><td><span class="chip c-cg">CG</span></td><td>Correctly built cross-surface approval channel — <b>keep</b></td></tr>
<tr><td class="path">transports/discord/spine_integration_v1.py:112</td><td>Full authority→gate→dispatch→proof→ledger</td><td><span class="chip c-cg">CG</span></td><td>Builds own ExecutionAuthorityEngine w/ hardcoded capability lists (config drift)</td></tr>
<tr><td class="path">nodes/distribution/distributor.py:218</td><td><code>request_approval</code>/<code>receive_approval</code></td><td><span class="chip c-gf">GF</span></td><td>Third parallel approval registry (GAP-C3-008)</td></tr>
<tr><td class="path">projections/eos/integration/outcomes.py:40</td><td>Source-row UPDATE + INSERT umh_outcomes audit</td><td><span class="chip c-gf">GF</span></td><td>Audited but not through governed_mutation; direct psycopg2</td></tr>
<tr><td class="path">projections/eos/workflows/runner.py:29</td><td>Each workflow step via governed_mutation</td><td><span class="chip c-cg">CG</span></td><td>Correctly governed — keep</td></tr>
</tbody>
</table>
</div>

<h3>2.7 — Roll-up totals</h3>
<div class="tablewrap">
<table class="compact">
<thead><tr><th>Surface</th><th class="num-col">Files</th><th class="num-col">Handlers</th><th class="num-col">Mutations</th><th class="num-col">Governed sites</th><th>Non-CG breakdown</th></tr></thead>
<tbody>
<tr><td>FastAPI Python (deployed)</td><td class="num-col">143</td><td class="num-col">1,306</td><td class="num-col">320</td><td class="num-col">360</td><td>CG 60 · RO 51 (incl. 1 read-mostly) · NR 14 · SD/SD-latent 9 · SD-GF 2 · GF 2 · UNC 4 · DEP 1 (Σ=143; NR includes governed.py and cockpit_settings_mutations.py, which carry module-level risk — §2.2)</td></tr>
<tr><td>Hono TS (dormant)</td><td class="num-col">9</td><td class="num-col">137</td><td class="num-col">33</td><td class="num-col">33</td><td>33/33 governed but <b>0/33 execute</b> (effect-free)</td></tr>
<tr><td>services/ entrypoints</td><td class="num-col">23</td><td class="num-col">—</td><td class="num-col">—</td><td class="num-col">—</td><td>CG 1 · GF 9 · SD 3 · DM/broken 10</td></tr>
<tr><td>cron (crontab.managed)</td><td class="num-col">~20</td><td class="num-col">—</td><td class="num-col">—</td><td class="num-col">~0</td><td>Predominantly SD; 1 CG (secret rotation); CPU/lock hygiene only, zero policy gating</td></tr>
<tr><td>node mesh + Windows nodes</td><td class="num-col">—</td><td class="num-col">—</td><td class="num-col">—</td><td class="num-col">—</td><td>1 CG (governed dispatch) vs raw relay + node trust GF/SD</td></tr>
</tbody>
</table>
</div>

<h3>2.8 — Coverage limits: surfaces outside the Phase-1 audit scope (remediation pass, 2026-07-04)</h3>
<p>Hostile review of the Phase-1 ledgers found five mutation-bearing surfaces that §§2.1–2.6 never enumerated. Each was classified in a <b>targeted grep-level pass on 2026-07-04</b> — file-level pattern evidence only, no per-function data-flow audit. These surfaces are <b>excluded from the §2.7 roll-up and the §05 compliance percentages</b>, which cover only the surfaces enumerated in §§2.1–2.6. Anything below marked UNVERIFIED needs a full pass before it can be asserted either way.</p>
<div class="tablewrap">
<table>
<thead><tr><th>Path / surface</th><th>Mutation surface (grep-level)</th><th>Class</th><th>Evidence · status</th></tr></thead>
<tbody>
<tr><td class="path">substrate/composition/ (45 .py — TME runtime)</td><td><code>knowledge_gap_trigger.py:135-140</code> appends KnowledgeGap records to <code>data/umh/composition/gap_queue.jsonl</code> (queue path set at :58-59); <code>mastery/management/backlog.py:110-113,179</code> writes report artifacts via <code>write_text</code></td><td><span class="chip c-gf">GF</span></td><td>Zero <code>governed_mutation</code> calls in the package (repo grep, 2026-07-04). Not dormant: imported by <code>substrate/execution/spine.py</code>, <code>substrate/execution/mastery_gate.py</code>, <code>substrate/control_plane/actions/tme.py</code>. No Phase-1 ledger claimed this package (E2 covered only the <code>skills/</code> doc layer). Grep-level classification only — full pass queued; internals UNVERIFIED</td></tr>
<tr><td class="path">substrate/state/ (63 .py, ~20 subpackages)</td><td>15 store modules in <code>stores/</code> (task, goal, approval, permission, venture, skill, entity, entity_link, embedding, profile, preference, agent_registry, email_folder, higgsfield, context_compaction) plus session/tenancy/business/finance/lifecycle/providers/storage subpackages; 27 of 63 files carry write-capable patterns (INSERT/UPDATE/psycopg2/json.dump/write_text)</td><td><span class="chip c-unc">UNC</span></td><td>0 direct <code>governed_mutation</code> calls in the package — governance, where it exists, is applied by callers, which this audit did not trace. Only 3 of 63 files were inspected by any Phase-1 ledger (<code>canonical_memory_store_v1.py</code> B3, <code>transformation_state_ledger.py</code> B3, <code>entity_link_store.py</code> B4/D2). "Memory writes" was a mandated mutation surface; the rest of this package is an <b>uninspected write surface</b> — targeted pass queued; UNVERIFIED</td></tr>
<tr><td class="path">transports/presence/handlers/ (23 .py in package; 6 handler modules)</td><td>Command ingress: <code>voice_handler</code>, <code>intent_handler</code>, <code>cc_command_handler</code>, <code>pipeline_handler</code>, <code>substrate_command_handler</code>, <code>report_handlers</code></td><td><span class="chip c-unc">UNC</span></td><td><code>substrate_command_handler.py:878</code> routes through <code>transports/discord/spine_integration_v1</code> (CG per ledger C3) but currently sits behind the broken import chain at :49 (B1 ImportError cascade — dead until GAP-B1-001 is fixed). The other five handlers: no <code>governed_mutation</code> hits (grep 2026-07-04); <code>intent_handler</code>/<code>cc_command_handler</code> carry write-capable patterns. Per-handler governed-vs-direct classification UNVERIFIED — this is a live command-ingress transport absent from every Phase-1 ledger's coverage claim</td></tr>
<tr><td class="path">scripts/ — manual ops tier (146 .py total; 134 outside crontab.managed)</td><td>Manually runnable direct writers. Grep census (2026-07-04): 5 touch Neon (psycopg2/DATABASE_URL — e.g. <code>env_upsert.py</code>), 29 reference Notion (e.g. <code>build_notion_databases.py</code>), 40 reference Discord (e.g. <code>discord_setup_channels.py</code>), 9 issue HTTP writes (requests/httpx post/put/patch/delete), 58 unique touch ≥1 external write-capable surface, 87 write local files, 7 call <code>governed_mutation</code></td><td><span class="chip c-sd">SD</span>/<span class="chip c-unc">UNC</span></td><td>§2.5 classified only the 12 unique <code>scripts/*.py</code> referenced by <code>infra/crontab.managed</code>; the brief mandated "scripts" as a surface. The remaining 134 are a <b>bounded blind spot</b>: counts above are file-level pattern hits, not per-script audits. Ops scripts that mutate Neon/Notion/Discord outside governance are SD by construction when run; which of the 58 are live tooling vs dead one-shots is UNVERIFIED</td></tr>
<tr><td class="path">transports/cli/ (7 .py — API-key command ingress)</td><td>Thin HTTP client over the deployed FastAPI surface: 1 mutation call (<code>POST /advisor/converse</code>, <code>client.py:85</code>); all other commands GET (ping/history/agents/loops/approvals/nodes/providers)</td><td><span class="chip c-ro">RO</span></td><td>Auth = <code>X-API-Key</code> from <code>UMH_API_KEY</code> (<code>client.py:31-42</code>) — a different trust model than the Clerk-authenticated visual surfaces (GAP-F2-018). No direct DB/file writes (grep 2026-07-04); governance is whatever the server-side route applies (§2.2 classification governs). Pass-through at grep level; per-command depth UNVERIFIED</td></tr>
</tbody>
</table>
</div>
<p class="note">Related, disclosed here for completeness: nine <code>substrate/understanding/</code> subpackages (deliberation, interpretation, research, patterns, world_pulse, embedding, intelligence, signals, knowledge — ~35 of 54 .py) were outside D1's assigned slice (ontology/, world_model/, domains/, reality/) and were not audited for rival primitives or ungoverned write paths by any workstream. Full blind-spot ledger: gap-analysis §17 (Coverage Proof).</p>

<h2><span class="num">03</span> Side-door ledger — ranked by blast radius</h2>
<p>Every governance bypass, ranked most-severe first. The three leads are the fail-open wrapper, the unauthenticated mesh relay, and the effect-free proof bridge — each defeats governance systemically rather than at one endpoint.</p>

<div class="door">
  <div class="door-head"><span class="rank">SD-01 · blast radius: EVERY mutation route</span><span class="sev s-crit">critical · GAP-C1-003 / GAP-C2-001</span></div>
  <div class="title">governed_mutation() fails open to direct ungoverned execution</div>
  <p>When the organism daemon is unavailable, <code>governed_mutation()</code> executes <code>execute_fn()</code> <b>directly</b> and returns status <code>completed_ungoverned</code> — the confirmed source: <code>router = _get_router(); if router is not None: return router.execute(...)</code> then falls through to <code>output, success = execute_fn()</code>. All 360 call sites — filesystem writes, remote SSH writes (<code>cockpit_workspace_routes.py:593–609</code>), signal intake (<code>app.py:549</code>), pipeline submit (<code>app.py:712</code>) — degrade to ungoverned execution with only a <code>logger.warning</code>. No policy, no risk classification, no approval, no envelope, no rollback. <b>The trust boundary fails open.</b></p>
  <p class="ev"><b>Fix:</b> fail-closed default (503) with an explicit per-mutation-spec allowlist for degraded-mode ops, plus a durable audit record for any degraded execution.<br><b>Evidence:</b> transports/api/governed.py:91–111</p>
</div>

<div class="door">
  <div class="door-head"><span class="rank">SD-02 · blast radius: arbitrary remote code on any connected node</span><span class="sev s-crit">critical · GAP-C3-001</span></div>
  <div class="title">Node-mesh HTTP /dispatch is unauthenticated (fail-open) without relay secret</div>
  <p>Confirmed source: <code>auth_ok = (bool(relay_secret) and bool(auth_header) and hmac.compare_digest(...)) or not relay_secret</code>. When <code>UMH_MESH_RELAY_SECRET</code> is unset, the <code>or not relay_secret</code> term makes <b>every request authorized</b>. <code>_http_dispatch</code> then sends <code>capability.execute</code> (shell / filesystem / desktop actuation) to any connected node with <b>no risk_class and no governance verdict</b> in the payload. The registry deliberately defines <code>remote_node_exec</code> and <code>tmux_send</code> specs for exactly this action class; the governed sibling path carries a verdict, this one carries nothing.</p>
  <p class="ev"><b>Fix:</b> refuse <code>/dispatch</code> when the secret is unconfigured; require a governance-verdict reference on every dispatch.<br><b>Evidence:</b> transports/node_mesh/server.py:892–898, 973–1039; nodes/windows/umh_node/client.py:458</p>
</div>

<div class="door">
  <div class="door-head"><span class="rank">SD-03 · blast radius: all TS mutations (dormant surface)</span><span class="sev s-crit">critical (latent) · GAP-C2-002</span></div>
  <div class="title">TS governed bridge records mutations without executing them</div>
  <p>Confirmed source in <code>organism_bridge.py</code>: <code>def _execute_fn(): return json.dumps(mutation_payload), True</code>. Every one of the 33 Hono mutations — memory-promotion approve/reject, approval-packet decisions, kill/resume — yields a successful envelope + <b>proof artifact asserting an effect that never happened</b>. Proof-artifact integrity is broken: the spine's trace claims a state change with zero state change. Mitigated only because the server is undeployed.</p>
  <p class="ev"><b>Fix:</b> dispatch <code>mutation_payload</code> to a registered server-side executor keyed by <code>mutation_name</code>, or remove the TS mutation surface.<br><b>Evidence:</b> transports/api/organism_bridge.py:2351–2352; http/lib/governed_bridge.ts:29–55; http/routes/organism.ts:177–196</p>
</div>

<div class="door">
  <div class="door-head"><span class="rank">SD-04 · blast radius: arbitrary remote shell per HTTP call</span><span class="sev s-crit">critical · GAP-C2-004</span></div>
  <div class="title">Remote-terminal HTTP endpoints bypass the spine entirely</div>
  <p><code>POST /terminal/remote/{create,send,send-key,destroy}</code> dispatch arbitrary shell text and keystrokes to remote mesh nodes via <code>POST :8095/dispatch</code> with no governed_mutation, no risk class, no approval, no trace. Clerk+operator auth only. The local-tmux sibling <b>in the same file</b> IS governed (:508) — the remote path was simply not wired to the spine.</p>
  <p class="ev"><b>Fix:</b> wrap as <code>remote_node_exec</code>/<code>tmux_send</code> governed mutations with per-node blast-radius metadata and approval per spec.<br><b>Evidence:</b> transports/api/cockpit_workstation_control_routes.py:54–60, 278–371; mutation_registry.py:229,289</p>
</div>

<div class="door high">
  <div class="door-head"><span class="rank">SD-05 · blast radius: production repo write+shell nightly</span><span class="sev s-high">high · GAP-C3-004</span></div>
  <div class="title">Nightly cron runs an autonomous write-enabled Claude agent outside all governance</div>
  <p><code>scripts/scheduled/nightly_maintenance.sh</code> invokes <code>claude -p --allowedTools "Bash Read Write Edit Glob Grep" --add-dir /opt/OS</code> at 2am. The only constraint is <code>--max-budget-usd 0.50</code>. No governed_mutation, no proof, no approval, no rollback. Its own failure-alert path imports <code>interface.discord.discord_utils</code> — <code>interface/</code> does not exist, so alerting is dead code.</p>
  <p class="ev"><b>Fix:</b> decompose into deterministic steps through the governed spine; any agentic step behind a work-packet approval contract.<br><b>Evidence:</b> scripts/scheduled/nightly_maintenance.sh; infra/crontab.managed (nightly)</p>
</div>

<div class="door high">
  <div class="door-head"><span class="rank">SD-06 · blast radius: MFA codes + CC session control</span><span class="sev s-high">high · GAP-C3-005</span></div>
  <div class="title">cc_webhook_receiver binds 0.0.0.0:8765 with zero auth</div>
  <p><code>web.TCPSite(runner, "0.0.0.0", port)</code> — contradicting its own docstring's 127.0.0.1 claim. <code>/cc-reply</code>, <code>/cc-prompt</code>, <code>/mfa-challenge</code> are unauthenticated; <code>/cc-prompt</code> button callbacks inject responses into tmux CC sessions — a <b>second approval channel</b> parallel to OperatorApprovalGate. MFA challenge codes transit this open endpoint.</p>
  <p class="ev"><b>Fix:</b> bind loopback or require a bearer token; authenticate the MFA relay end-to-end.<br><b>Evidence:</b> services/cc_webhook_receiver.py:8, 100–229, 305–308</p>
</div>

<div class="door high">
  <div class="door-head"><span class="rank">SD-07 · blast radius: external third-party-visible actions</span><span class="sev s-high">high · GAP-C3-003 / GAP-C3-007</span></div>
  <div class="title">External mutations execute outside governance; only bookkeeping is governed</div>
  <p><code>gws.send_email()</code> runs directly (<code>discord_bot_commands.py:546,654</code>); the wrapped <code>execute_fn</code> is the subsequent internal <code>UPDATE events</code>. The trace records that an email was sent — it never gated the send. Same shape for calendar mutations. Separately, <code>calendar_invite_handler.py</code> auto-accepts/declines external invites on LLM <code>confidence=='high'</code> from cron — an externally-visible L1 mutation with an LLM in the decision loop and no approval envelope.</p>
  <p class="ev"><b>Fix:</b> the external mutation itself becomes the execute_fn (ActionEnvelope with require_approval); invite responses classified EXTERNAL_COMMUNICATION with proof artifacts.<br><b>Evidence:</b> services/discord_bot_commands.py:505–580; scripts/calendar_invite_handler.py:170–306; adapters/google_workspace/gws_connector.py:1074</p>
</div>

<div class="door high">
  <div class="door-head"><span class="rank">SD-08 · blast radius: Neon + Notion, every 5–15 min</span><span class="sev s-high">high · GAP-C3-006</span></div>
  <div class="title">The cron layer is a parallel ungoverned mutation plane</div>
  <p><code>agent_task_executor.py</code> (CognitiveLoop → complete_task → Notion → AgentMemory), <code>call_prep.py:324</code>, <code>noshow_detector.py:129</code>, <code>notion_tasks_sync.py:138–231</code>, <code>notion_sync_poller.py</code> mutate Neon <code>events</code> and Notion directly on 5–15 minute cadences. <code>cron-run</code> provides CPU/lock/secret hygiene only — zero governance gating.</p>
  <p class="ev"><b>Fix:</b> cron scripts emit signals (the <code>emit_signal.py</code> pattern) consumed by the governed spine; direct DB/Notion writes migrate behind governed contracts.<br><b>Evidence:</b> infra/crontab.managed; scripts/agent_task_executor.py:101–265; scripts/cron-run</p>
</div>

<div class="door high">
  <div class="door-head"><span class="rank">SD-09 · blast radius: node write-class actions</span><span class="sev s-high">high · GAP-C3-002</span></div>
  <div class="title">Runtime node trusts caller-declared risk class; verdict never validated</div>
  <p>The node reads <code>risk_class</code> from the request payload (default <code>REVERSIBLE_WRITE</code>); the <code>governance_verdict_id</code> is transmitted by the governed path but <b>never read or verified</b> on the node. A dispatcher can under-declare risk to slip under <code>max_risk_class</code> caps. Combined with the node's weak allowlist (<code>command.split()[0]</code> only; unnormalized path <code>startswith</code>), the permission envelope at the node trust boundary is decorative.</p>
  <p class="ev"><b>Fix:</b> node derives risk locally or verifies a signed verdict; verdict-less write-class requests rejected; argument-aware command policy + canonicalized path containment.<br><b>Evidence:</b> nodes/windows/umh_node/client.py:452–500; governance.py:31–64 (GAP-C3-013)</p>
</div>

<div class="door med">
  <div class="door-head"><span class="rank">SD-10..14 · bounded / dormant / medium blast radius</span><span class="sev s-med">medium</span></div>
  <div class="title">Remaining side-doors</div>
  <ul class="tight">
    <li><b>Ungoverned autonomous-lane endpoints</b> — cadence set-mode direct attr write, dry-run cycle, PR-factory cleanup <span class="path">cockpit_autonomous_routes.py:359–392</span> (GAP-C2-007)</li>
    <li><b>Unregistered mutation names invert governance</b> — <code>filesystem_write</code>, <code>config_update</code>, <code>proof_review</code>, <code>workstation_execute</code>, <code>recovery_action</code> fail when daemon up, succeed ungoverned when down (GAP-C2-003)</li>
    <li><b>Dormant unauthenticated services</b> — <code>goal_api.py</code>, <code>higgsfield_webhook.py</code>, <code>local_bridge_server.py</code> one command from live (GAP-C3-014)</li>
    <li><b>Chat media upload</b> — ungoverned direct write to <code>data/chat_media/</code> (bounded/validated) (GAP-C2-011)</li>
    <li><b>Canonical-reality side-doors</b> — direct <code>InstanceRealityModel.record</code> at <span class="path">work_packet_engine.py:674</span>, <span class="path">deploy_verification_worker.py:527</span>, <span class="path">projection_certification.py:295</span> (GAP-C1-007)</li>
    <li><b>Command-runtime direct routes</b> — profile/system-mode switch, objective creation, private-queue schedule (GAP-C1-011)</li>
    <li><b>Side-door AgentMemory writes</b> — cron/scraper bypass the promotion pipeline (GAP-C3-016)</li>
  </ul>
</div>

<h2><span class="num">04</span> Broken-call-path ledger</h2>
<p>Governed code paths that invoke spine/queue methods that <b>do not exist</b>. Both fail via <code>AttributeError</code> caught and logged at <code>debug</code> level — the governance path silently produces nothing while appearing to run. Verified against source.</p>
<div class="tablewrap">
<table>
<thead><tr><th>Caller</th><th>Invokes</th><th>Actual method</th><th>Consequence</th><th>Gap</th></tr></thead>
<tbody>
<tr>
  <td class="path">governed_work_runtime.py:232<br>(submit_work)</td>
  <td><code>packet_engine.create_from_intent(intent)</code></td>
  <td><code>create_packet_from_intent</code><br><span class="path">work_packet_engine.py:67</span></td>
  <td>AttributeError swallowed (:236 <code>logger.debug</code>); <code>work_id</code> becomes a raw uuid; classifier-derived risk never applied; the "mandatory DO layer" never creates real packets. <b>No test exercises submit_work</b> (GAP-C1-014)</td>
  <td><span class="sev s-crit">GAP-C1-001</span></td>
</tr>
<tr>
  <td class="path">command_runtime.py:896<br>(_process_approval)</td>
  <td><code>q.update_status(packet_id, new_status)</code></td>
  <td><code>update_packet_status</code><br><span class="path">universal_work_queue.py:237</span></td>
  <td>AttributeError swallowed; <b>every packet approve/reject through an operator command returns an error dict</b></td>
  <td><span class="sev s-crit">GAP-C1-002</span></td>
</tr>
</tbody>
</table>
</div>
<p class="note">Both confirmed by grep against source: <code>create_from_intent</code> = 0 definitions repo-wide (only <code>create_packet_from_intent</code> exists); <code>update_status</code> on UniversalWorkQueue = 0 (only <code>update_packet_status</code>). The <code>.update_status</code> calls at command_runtime.py:1190+ target <code>CommandHistory</code>, a different object, and are valid — only line 896's queue call is broken.</p>

<h2><span class="num">05</span> Totals &amp; compliance percentages</h2>
<div class="stats">
  <div class="stat good"><div class="k">FastAPI files fully CG</div><div class="v">60<small>/143</small></div></div>
  <div class="stat"><div class="k">Governed sites vs mutations</div><div class="v">360<small>/320</small></div></div>
  <div class="stat crit"><div class="k">TS mutations that execute</div><div class="v">0<small>/33</small></div></div>
  <div class="stat crit"><div class="k">Broken governed paths</div><div class="v">2</div></div>
  <div class="stat high"><div class="k">Parallel approval machines</div><div class="v">4</div></div>
  <div class="stat"><div class="k">Rival execution spines</div><div class="v">4</div></div>
</div>

<div class="tablewrap">
<table class="compact">
<thead><tr><th>Compliance measure</th><th class="num-col">Value</th><th>Reading</th></tr></thead>
<tbody>
<tr><td>Deployed FastAPI mutation handlers routed via governed_mutation (file granularity)</td><td class="num-col">clean</td><td>Pre-commit gate: 183 route/service files clean — <b>strongest-converged surface</b></td></tr>
<tr><td>FastAPI files with governance risk (SD/SD-latent/SD-GF/GF/DEP/UNC)</td><td class="num-col">18 / 143</td><td>~13% of API files carry a bypass, latent defect, or fragmentation</td></tr>
<tr><td>Hono TS mutations producing a real state change</td><td class="num-col">0%</td><td>0/33 — proof-artifact integrity broken (dormant surface)</td></tr>
<tr><td>services/ entrypoints fully canonical-governed</td><td class="num-col">1 / 23</td><td>~4% — the services tier is predominantly GF/SD/dormant</td></tr>
<tr><td>cron entries with any policy/governance gating</td><td class="num-col">~1 / 20</td><td>Only secret-rotation; the rest are a parallel mutation plane</td></tr>
<tr><td>Node dispatch paths carrying a governance verdict</td><td class="num-col">1 of 2</td><td>Governed capability-socket path vs raw fail-open relay to the same adapters</td></tr>
<tr><td>Single state authority for "what is pending approval"</td><td class="num-col">No</td><td>4 parallel approval state machines + 3 parallel approval channels</td></tr>
</tbody>
</table>
</div>

<div class="callout">
<b>The convergence gap in one line.</b> Governance is <b>real and enforced at the deployed HTTP boundary</b>, and <b>absent or bypassable everywhere the boundary is crossed by another route</b>: the fail-open wrapper below it, the mesh relay beside it, the cron/services/node planes underneath it, and two governed paths broken by typo'd method names. Converging the spine means making the transport-layer guarantee hold below the transport layer — not adding more governed routes.
</div>

<h2><span class="num">06</span> Required remediation summary</h2>
<p>Mapped to gap IDs, ordered by blast radius. Owner layer per the four-layer model: L2 = UMH platform metamodel (control plane, operation runtime, mutation contract, trust boundary); L4 = semantic grounding / state authority.</p>

<h4>Tier 1 — fail-open &amp; effect-free (fix before any further capability work)</h4>
<div class="tablewrap">
<table class="compact">
<thead><tr><th>Gap</th><th class="num-col">Sev</th><th>Remediation</th><th>Layer</th></tr></thead>
<tbody>
<tr><td>GAP-C1-003 · GAP-C2-001</td><td class="num-col"><span class="sev s-crit">crit</span></td><td><code>governed_mutation()</code> fails closed (503) with explicit degraded-mode allowlist + durable audit</td><td>L2 trust boundary</td></tr>
<tr><td>GAP-C3-001</td><td class="num-col"><span class="sev s-crit">crit</span></td><td>Mesh <code>/dispatch</code> refuses when relay secret unset; require verdict reference per dispatch</td><td>L2 trust boundary</td></tr>
<tr><td>GAP-C2-002</td><td class="num-col"><span class="sev s-crit">crit</span></td><td>TS bridge dispatches to a registered server-side executor keyed by <code>mutation_name</code>, or remove the TS mutation surface</td><td>L2 adapter contract</td></tr>
<tr><td>GAP-C2-004</td><td class="num-col"><span class="sev s-crit">crit</span></td><td>Remote-terminal endpoints wrapped as <code>remote_node_exec</code>/<code>tmux_send</code> governed mutations</td><td>L2 permission envelope</td></tr>
<tr><td>GAP-C1-001 · GAP-C1-002</td><td class="num-col"><span class="sev s-crit">crit</span></td><td>Fix the two broken method calls; stop swallowing AttributeError; add round-trip tests (GAP-C1-014)</td><td>L2 operation runtime</td></tr>
</tbody>
</table>
</div>

<h4>Tier 2 — fragmentation &amp; ungoverned planes</h4>
<div class="tablewrap">
<table class="compact">
<thead><tr><th>Gap</th><th class="num-col">Sev</th><th>Remediation</th><th>Layer</th></tr></thead>
<tbody>
<tr><td>GAP-C1-004 · GAP-C3-008</td><td class="num-col"><span class="sev s-high">high</span></td><td>One approval / pending-work state authority; the 4 machines + 3 channels become projections of it</td><td>L2 state authority</td></tr>
<tr><td>GAP-C3-006 · GAP-C3-003 · GAP-C3-007</td><td class="num-col"><span class="sev s-high">high</span></td><td>Cron + external side effects migrate behind governed mutation / signal ingress; external mutation becomes the execute_fn</td><td>L2 · L4</td></tr>
<tr><td>GAP-C2-005</td><td class="num-col"><span class="sev s-high">high</span></td><td>Operator-loop handler libraries submit envelopes internally; executor-runtime approval fallback becomes fail-closed</td><td>L2</td></tr>
<tr><td>GAP-C1-005 · GAP-C3-002 · GAP-C3-013</td><td class="num-col"><span class="sev s-high">high</span></td><td>Workcell/adapter execution wrapped in ActionEnvelope; node derives/verifies risk; argument-aware command policy + path containment</td><td>L2 permission envelope</td></tr>
<tr><td>GAP-C1-006 · GAP-A-008 · GAP-A-009</td><td class="num-col"><span class="sev s-high">high</span></td><td>Migrate Discord hot path off the legacy sync spine + rival event spine; remove conditional-governance bypass; then delete shims</td><td>L2</td></tr>
<tr><td>GAP-C2-003</td><td class="num-col"><span class="sev s-high">high</span></td><td>Every <code>mutation_name=</code> literal resolves to a registered spec; CI grep of literals vs registry</td><td>L2 capability registry</td></tr>
<tr><td>GAP-C2-006 · GAP-C3-015</td><td class="num-col"><span class="sev s-high">high</span></td><td>Retire the <code>state_mutate</code> catch-all (159 sites); per-capability specs; lint cap; spine-side high-risk-verb rejection</td><td>L2 policy engine</td></tr>
<tr><td>GAP-C3-004 · GAP-C3-005</td><td class="num-col"><span class="sev s-high">high</span></td><td>Nightly agent decomposed through the spine; cc_webhook binds loopback / requires token</td><td>L2</td></tr>
</tbody>
</table>
</div>

<h4>Tier 3 — durability, hygiene, drift</h4>
<div class="tablewrap">
<table class="compact">
<thead><tr><th>Gap</th><th class="num-col">Sev</th><th>Remediation</th><th>Layer</th></tr></thead>
<tbody>
<tr><td>GAP-C1-007 · GAP-C1-009 · GAP-C1-018</td><td class="num-col"><span class="sev s-med">med</span></td><td>Route all observation/memory writes through CanonicalRealityWritePath / promotion; the reality choke point invokes governance</td><td>L4 grounding</td></tr>
<tr><td>GAP-C1-008 · GAP-C1-011 · GAP-C1-015 · GAP-C1-016</td><td class="num-col"><span class="sev s-med">med</span></td><td>Remove dead spine wiring or use it; command routes emit envelopes; bound idempotency map; atomic JSONL writes</td><td>L2</td></tr>
<tr><td>GAP-C2-007 · GAP-C2-010 · GAP-C2-012 · GAP-C2-014 · GAP-C3-009 · GAP-C3-014</td><td class="num-col"><span class="sev s-med">med</span></td><td>Govern autonomous-lane endpoints; add operator-role dep to <code>/organism/signal</code>; retire or wire the dormant Hono/relay/service surfaces; fold the settings pipeline into a governed envelope</td><td>L2</td></tr>
<tr><td>GAP-C3-010 · GAP-C3-011 · GAP-C3-012</td><td class="num-col"><span class="sev s-med">med</span></td><td>Enforce credential gate at every authenticated actuation; add <code>nodes/</code> to CPU gate (or document exemption); remove/repair the broken nightly scrape</td><td>L2</td></tr>
<tr><td>GAP-A-004 · GAP-A-013 · GAP-C2-008</td><td class="num-col"><span class="sev s-med">med</span></td><td>One declared canonical API entrypoint; delete the dead NameError duplicate <code>operator.py</code>; correct ARCHITECTURE.md §9</td><td>L2</td></tr>
<tr><td>GAP-C1-010 · GAP-C1-012 · GAP-C1-013 · GAP-C1-017 · GAP-C2-009 · GAP-C2-013 · GAP-C3-016 · GAP-C3-017 · GAP-C3-018 · GAP-C3-019</td><td class="num-col"><span class="sev s-low">low</span></td><td>Resolve name collisions in canonical_types; fix the gate's ghost <code>saas/</code> scan + grandfather list; correct docs/registry drift; remove instance-context leaks; split the 3,113-line god file; uniform operatorGuard on TS</td><td>L2 metamodel</td></tr>
</tbody>
</table>
</div>

<hr class="soft">

<h2><span class="num">·</span> Provenance</h2>
<p class="note">Synthesized from Phase-1 evidence ledgers <b>C1</b> (Python mutation core), <b>C2</b> (API write surfaces), <b>C3</b> (non-API mutation paths), and <b>A</b> (repository architecture / entrypoint authority). All 74 cited repo paths were batch-verified to exist in the audited worktree; the four systemic defects (fail-open fallback, effect-free TS bridge, fail-open mesh relay, both broken method calls) were re-verified line-by-line against source. Gap IDs and severities are drawn from the audit index (270 total candidates across 17 workstreams). Items marked UNVERIFIED in the ledgers are carried forward as UNVERIFIED here, not asserted as fact. <b>2026-07-04 remediation pass:</b> §2.8 was added after hostile review found five mutation-bearing surfaces (substrate/composition/, substrate/state/, transports/presence/, the manual scripts/ tier, transports/cli/) absent from every Phase-1 coverage claim; §2.8 classifications are grep-level only and are excluded from the §2.7 roll-up and §05 percentages, which remain as originally computed over §§2.1–2.6.</p>

</div>
