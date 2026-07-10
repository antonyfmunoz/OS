---
type: codewiki-dir
dir: .github
---

# `.github/` — the sole CI workflow: mobile cockpit build (web → iOS → Android)

**1 file · 2,680 bytes · [Full file inventory](../inventory/dot-github.md)**

## Purpose
`.github/` contains one file, `.github/workflows/mobile-build.yml` (92 lines) — the only
GitHub Actions workflow in the repository. It builds the cockpit as a mobile app: a web
bundle via Vite, then a Capacitor-synced iOS archive and Android debug APK. CI in UMH is
deliberately minimal — the heavy verification lives in local pre-commit gates and runtime
checks, not in cloud CI. This workflow exists purely to produce mobile artifacts from the
`cockpit/` frontend.

## How it fits
This is repository automation, outside the code-layer stack. It touches only `cockpit/`
(the Electron/web/mobile operator UI) and is triggered on pushes to `main` that modify
`cockpit/**`, plus manual `workflow_dispatch`. It does not run the Python test suite, lint
gates, or the substrate qualification suites — those are enforced by local pre-commit hooks
(`scripts/check_*.py`) and the Docker deploy gates, not by this workflow.

## Structure
One workflow, three jobs in a fan-out/fan-in graph:

| Job | Runner | Role |
|---|---|---|
| `build-web` | `ubuntu-latest` | `npm ci --legacy-peer-deps` → `vite build --config vite.web.config.ts`; uploads `cockpit/dist-web/` as the `dist-web` artifact |
| `build-ios` | `macos-latest` | `needs: build-web`; downloads `dist-web`, `npx cap sync ios`, `xcodebuild archive` (unsigned) → uploads `App.xcarchive` |
| `build-android` | `ubuntu-latest` | `needs: build-web`; downloads `dist-web`, `npx cap sync android`, `./gradlew assembleDebug` → uploads `app-debug.apk` |

## Data & state
The `build-web` job passes its output to the two mobile jobs via the `dist-web` GitHub
artifact — the mobile jobs never rebuild the web bundle, they consume it. Build env vars for
the web bundle: `VITE_CLERK_PUBLISHABLE_KEY` (from repo secrets), `VITE_API_URL=/api/umh`,
`VITE_AI_NAME=DEX`.

## Gotchas
- **`--legacy-peer-deps` is mandatory on every `npm ci`** in this workflow — the cockpit's
  dependency tree has peer-dependency conflicts that a plain `npm ci` rejects. All three jobs
  set it.
- **iOS builds are unsigned** (`CODE_SIGNING_ALLOWED=NO`, empty identity) — this produces an
  archive for inspection/CI validation, not a distributable signed IPA.
- The only injected secret is `VITE_CLERK_PUBLISHABLE_KEY` — a *publishable* (client-side)
  Clerk key, safe to expose in the bundle. No server secrets flow through CI.
- **This does not deploy anything.** The cockpit is deployed to Fly.io (`umh-cockpit` app)
  via `bash cockpit/deploy.sh` — never `flyctl deploy` directly (Cockpit Deploy Gate law).
  CI only builds artifacts; deployment is a separate, gated local action.

## See also
- [`cockpit/`](cockpit.md) — the frontend this workflow builds
- [services-runtime](../services-runtime.md) — Fly.io cockpit deployment
- [`_root-files`](_root-files.md) — root build/deploy files
- [conventions](../conventions.md)
