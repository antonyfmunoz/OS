---
name: saas-dev:analytics-delivery
description: Instruments PostHog analytics (events, feature flags, error tracking) and generates deployment infrastructure (Docker, CI/CD, platform configs) for the finished SaaS app. Use when executing Phase 6 (analytics-delivery) of the SaaS development pipeline.
---

# Skill: saas-dev:analytics-delivery

Takes PageSpec analytics layers and the user's hosting choice, instruments PostHog capture calls into page components, creates feature flags via API, generates Dockerfile + .dockerignore + platform configs + GitHub Actions CI/CD, and executes deployment with preflight validation and explicit confirmation gate.

## Prerequisites

- Phase 5 (saas-dev:backend-wirer) complete
- Phase 2 (saas-dev:spec-parser) complete with PageSpec analytics layers in `pipeline_pages`
- `posthog-js` installed as dependency (`npm install posthog-js`)
- `VITE_POSTHOG_API_KEY` (Project API Key, prefix `phc_`) in `.env` — or system generates a setup guide
- Optional: `POSTHOG_PERSONAL_API_KEY` (prefix `phx_`) + `POSTHOG_PROJECT_ID` for feature flag creation via API

## Inputs

- `projectRoot: string` — absolute path to SaaS project repo
- `runId: string` — pipeline run ID (query `pipeline_pages` for PageSpec analytics layers)
- `hostingTarget: HostingTarget` — user's chosen hosting platform (`railway` | `render` | `fly` | `custom`)

## Module Map

All modules live under `lib/analytics-delivery/`:

| Module | Export | Role |
|--------|--------|------|
| `lib/analytics-delivery/types.ts` | All shared types | `TaxonomyReport`, `AnalyticsInjection`, `DeployConfig`, `HostingTarget`, `EnvVarEntry`, `DeployRunnerResult`, `DeployOutcome`, `PostHogSetupResult`, `PreflightResult` |
| `lib/analytics-delivery/taxonomy-auditor.ts` | `auditTaxonomy`, `toSnakeCase` | Read PageSpec analytics layers, validate completeness, detect collisions (distinct names that normalize to same snake_case), produce `TaxonomyReport` |
| `lib/analytics-delivery/analytics-injector.ts` | `generateAnalyticsInjections`, `buildProviderCode`, `buildIdentifyCode` | Code-mod injection of `posthog.capture()` into page components. Load events get auto-injectable `useEffect` (with `useRef` dedupe for React 18 strict mode). Click/submit events get structured `manualCaptures` with copy-paste-ready `captureSnippet` |
| `lib/analytics-delivery/posthog-setup.ts` | `checkPostHogSetup`, `generateSetupGuide`, `createFeatureFlags`, `generateDashboardGuide` | Detect PostHog config (distinguishes Project API Key `phc_` from Personal API Key `phx_`), generate setup guide, create feature flags via API (failures surfaced as `flagWarnings` — non-blocking), generate baseline dashboard setup instructions |
| `lib/analytics-delivery/env-scanner.ts` | `scanEnvVars`, `generateEnvExample` | Scan all env var references (dot-notation, bracket-notation, Vite `import.meta.env` patterns), produce `.env.example` with `REQUIRED` / `OPTIONAL` markers |
| `lib/analytics-delivery/docker-config-generator.ts` | `generateDockerConfig`, `generateHostingMenu` | Multi-stage Dockerfile + `.dockerignore` + platform config generation (`railway.toml` / `render.yaml` / `fly.toml` / `docker-compose.yml`). `PORT` env var supported for Railway/Render/Fly runtime injection |
| `lib/analytics-delivery/github-actions-generator.ts` | `generateCIWorkflow`, `generateCDWorkflow` | CI workflow (type-check + test + build, runs on every PR push) and CD workflow (staging auto-deploy on merge to main, production requires manual approval gate via GitHub environment protection rule) |
| `lib/analytics-delivery/deploy-runner.ts` | `runDeploy`, `checkCLIAvailable`, `preflightDeploy` | Preflight validation (secrets + CLI), confirmation gate, platform CLI execution with structured `DeployOutcome` (`skipped` / `deployed` / `failed-preflight` / `failed-runtime`) |

## Pipeline

**Step 1 — Taxonomy Audit (ANLYT-01)**

Read PageSpec analytics layers from `pipeline_pages` (same query pattern as Phase 5):

```typescript
const pages = await db.select().from(pipelinePages)
  .where(and(eq(pipelinePages.runId, runId), eq(pipelinePages.phase, "spec"), eq(pipelinePages.status, "complete")));
const pageSpecs = pages.map(p => PageSpecFullSchema.parse(JSON.parse(p.output)));
const taxonomyReport = auditTaxonomy(pageSpecs.map(p => p.analytics));
```

- If `taxonomyReport.valid` is `false`: surface errors to user and abort
- If `taxonomyReport.pagesWithoutEvents` is non-empty: present report to user, ask to continue or abort
- If `taxonomyReport.collisions` is non-empty: present collision warnings (e.g., `"API Error"` and `"api_error"` collapse to same key) — user decides to proceed or fix
- Gate: user must confirm taxonomy before proceeding

**Step 2 — PostHog Setup Check (D-03)**

```typescript
const setupResult = checkPostHogSetup(process.env);
if (!setupResult.apiKeyPresent) {
  const guide = generateSetupGuide();
  // present guide to user — distinguishes Project API Key (phc_, required) from Personal API Key (phx_, optional)
  // checkpoint:human-action — user adds VITE_POSTHOG_API_KEY to .env
  // re-check until apiKeyPresent=true
}
// Install posthog-js if not already present: npm install posthog-js
```

**Step 3 — Analytics Instrumentation (ANLYT-02)**

```typescript
const injections = generateAnalyticsInjections(pageSpecs, projectRoot);
const providerCode = buildProviderCode(process.env.VITE_POSTHOG_API_KEY!);
// inject PostHogProvider into App.tsx
const authProvider = detectAuthProvider(projectRoot); // check use-auth.tsx for firebase
if (authProvider) {
  const identifyCode = buildIdentifyCode(authProvider);
  // inject identify code into use-auth.tsx
}
```

For each `AnalyticsInjection`:
- Inject `importCode` + `hookCode` + `captureCode` (auto-injectable load events with `useRef(false)` dedupe)
- For `manualCaptures`: present copy-paste-ready `captureSnippet` to user with target handler context
- All injections are additive (append-model) — never modify existing code

**Step 4 — Feature Flags + Dashboard Guide (ANLYT-03, D-15, D-16)**

```typescript
if (process.env.POSTHOG_PERSONAL_API_KEY && process.env.POSTHOG_PROJECT_ID) {
  const flagResult = await createFeatureFlags(taxonomyReport.allFlagCandidates);
  if (flagResult.flagsFailed.length > 0) {
    // display flagWarnings to user — non-blocking but NOT silent
  }
} else {
  // skip with warning, document manual flag creation steps
}
const dashboardGuide = generateDashboardGuide(taxonomyReport);
// write to docs/posthog-dashboard-setup.md
```

**Step 5 — Env Scanner (D-11)**

```typescript
const envVars = scanEnvVars(projectRoot);
const envExample = generateEnvExample(envVars, {
  extraVars: ["VITE_POSTHOG_API_KEY", "POSTHOG_PERSONAL_API_KEY", "POSTHOG_PROJECT_ID"]
});
// write .env.example to project root (with REQUIRED markers)
```

`generateEnvExample` always injects `VITE_POSTHOG_API_KEY` (client) and `POSTHOG_PERSONAL_API_KEY` (server) per D-03 regardless of scan results.

**Step 6 — Hosting Decision (DEPLOY-01)**

```typescript
const menu = generateHostingMenu();
// present menu to user with trade-offs table (cost, complexity, scaling, vendor lock-in)
// checkpoint:decision — user picks target (railway | render | fly | custom)
// store hostingTarget for remaining steps
```

**Step 7 — Config Generation (DEPLOY-02, DEPLOY-03)**

```typescript
const deployConfig = generateDockerConfig(hostingTarget);
// write Dockerfile, .dockerignore, and platform config (railway.toml / render.yaml / fly.toml / docker-compose.yml)
const ciWorkflow = generateCIWorkflow();
// write .github/workflows/ci.yml
const cdWorkflow = generateCDWorkflow(hostingTarget);
// write .github/workflows/cd.yml
```

If target is not `custom`: document GitHub environment setup (Settings > Environments > `production` > Required Reviewers) per D-13.

**Step 8 — Preflight Validation (DEPLOY-04 pre-check)**

```typescript
const preflight = preflightDeploy(hostingTarget, process.env);
if (!preflight.ready) {
  // present missingSecrets and missingCLI with install instructions to user
  // gate: preflight must pass before deploy attempt
}
```

**Step 9 — Deploy (DEPLOY-04, DEPLOY-05)**

```typescript
// checkpoint:human-verify — confirm deployment
const result = runDeploy(hostingTarget, confirmed, { env: process.env });
// present DeployRunnerResult with structured outcome:
// deployed | failed-preflight | failed-runtime | skipped
```

## Checkpoints

4 human interaction points in this phase:

| Step | Type | Trigger |
|------|------|---------|
| Step 1 | `checkpoint:human-verify` | Taxonomy review — user confirms event coverage or aborts to fix gaps |
| Step 2 | `checkpoint:human-action` | PostHog setup — user adds `VITE_POSTHOG_API_KEY` to `.env` (only fires if key missing) |
| Step 6 | `checkpoint:decision` | Hosting decision — user picks `railway` / `render` / `fly` / `custom` |
| Step 9 | `checkpoint:human-verify` | Deployment confirmation — explicit gate per DEPLOY-05 before any CLI execution |

## Error Handling

| Error | Cause | Recovery |
|-------|-------|----------|
| PostHog API failures (flag creation) | Invalid `POSTHOG_PERSONAL_API_KEY` or network error | Non-blocking — surface as `flagWarnings` in `PostHogSetupResult.flagWarnings`, continue |
| CLI not found | `flyctl`, `railway` binary missing from PATH | `preflightDeploy` catches via `checkCLIAvailable`, presents install instructions (`CLI_INSTALL_INSTRUCTIONS`), blocks deploy |
| Missing secrets | `RAILWAY_TOKEN`, `FLY_API_TOKEN`, `RENDER_DEPLOY_HOOK_URL` absent from env | `preflightDeploy` catches via `REQUIRED_SECRETS` check, lists missing vars, `outcome: "failed-preflight"` |
| Build failures | `tsc --noEmit` or Vite build error | Escalate to user with error output — do not attempt deploy |
| Missing env vars (`VITE_POSTHOG_API_KEY`) | Not in `.env` | Generate setup guide, gate at Step 2 until resolved |
| Empty pageSpecs | No pages in `pipeline_pages` for `runId` | `auditTaxonomy` returns `valid=false` with error message — structured result, not throw |
| Collision detection | Distinct event names normalize to same snake_case key | `auditTaxonomy` returns `collisions` array with warning messages — user decides to proceed or fix |
| Runtime deploy error | Platform CLI exits non-zero | `runDeploy` catches, returns `outcome: "failed-runtime"` with error message |

## Output

**Modified files:**
- `client/src/App.tsx` — PostHogProvider wraps app
- `client/src/pages/*.tsx` — `posthog.capture()` injected into page components
- `client/src/hooks/use-auth.tsx` — `posthog.identify()` on auth state change (if auth detected)

**Generated files:**
- `.env.example` — all env vars with REQUIRED / OPTIONAL markers
- `Dockerfile` — multi-stage build (Vite + esbuild build stage, Node.js 20 production runtime)
- `.dockerignore` — excludes node_modules, .env, dist from Docker build context
- Platform config — `railway.toml` / `render.yaml` / `fly.toml` / `docker-compose.yml`
- `.github/workflows/ci.yml` — type-check + test + build on every PR push
- `.github/workflows/cd.yml` — staging auto-deploy + production manual gate
- `docs/posthog-dashboard-setup.md` — baseline dashboard setup instructions

**API side effects:**
- PostHog feature flags created (if `POSTHOG_PERSONAL_API_KEY` + `POSTHOG_PROJECT_ID` present)

**Deployment:**
- App deployed to chosen platform (if confirmed and preflight passes — `outcome: "deployed"`)
