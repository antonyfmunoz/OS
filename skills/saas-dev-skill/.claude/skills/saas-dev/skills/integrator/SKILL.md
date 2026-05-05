---
name: saas-dev:integrator
description: Takes generated React TSX from Phase 3 (react-gen) and integrates it as working React pages — wiring routes into App.tsx, adding sidebar nav items, and managing the git branch lifecycle. Use after react-gen completes with generated pages.
---

# Skill: saas-dev:integrator

Takes generated React TSX from Phase 3 (react-gen) and integrates it as working React pages with proper routing, navigation, and atomic git commits.

## Prerequisites

- Phase 3 (react-gen) complete: `pipeline_pages` table has rows with `phase="react-gen"` AND `status="complete"`
- `AI_INTEGRATIONS_ANTHROPIC_API_KEY` configured in .env — required for HTML-to-TSX translation
- `DATABASE_URL` configured for Neon PostgreSQL
- `git` CLI available in PATH
- `gh` CLI available in PATH (fallback: manual PR instructions printed if absent)

## Inputs

- `projectRoot: string` — absolute path to the SaaS project root
- `appTsxPath: string` — path to `client/src/App.tsx`
- `sidebarPath: string` — path to `client/src/components/sidebar.tsx`
- `projectId: string` — pipeline project ID for database queries

## Module Map

All modules live under `lib/code-integrator/`:

| Module | Export | Role |
|--------|--------|------|
| `lib/code-integrator/brownfield-audit.ts` | `auditBrownfield` | Snapshot existing routes, pages, nav items, shadcn components |
| `lib/code-integrator/html-to-shadcn.ts` | `translateHtmlToShadcn` | Claude AI translation: HTML → React TSX with shadcn/ui |
| `lib/code-integrator/page-writer.ts` | `writePage`, `ensureShadcnComponents`, `checkFileConflict` | Write translated TSX to disk, auto-install missing shadcn components, detect file conflicts |
| `lib/code-integrator/route-injector.ts` | `injectRoute`, `detectRouteConflict` | Insert ProtectedRoute + optional CompanyGate into App.tsx |
| `lib/code-integrator/nav-injector.ts` | `injectNavItem` | Insert remixicon nav item into sidebar.tsx |
| `lib/code-integrator/git-workflow.ts` | `createBranch`, `commitPage`, `pushAndCreatePR`, `detectBaseBranch` | Branch creation, per-page atomic commits, push and PR creation |
| `lib/code-integrator/codex-review.ts` | `reviewWithCodex`, `parseCodexReview` | Codex-style review of translated TSX (Plan 04-04) |
| `lib/code-integrator/skill-reviews.ts` | `queryCodeReviewSkill`, `querySimplifySkill`, `queryVerificationSkill` | code-review / simplify / verification skill wrappers (Plan 04-04) |
| `lib/code-integrator/types.ts` | `BrownfieldInventory`, `RouteInjectionInput`, `NavInjectionInput`, `PageIntegrationResult`, `RouteConflict`, `ConflictResolution` | Shared type contracts |

## Pipeline

### Step 1 — Initialize

Determine the correct base branch and create the integration branch.

```typescript
import { detectBaseBranch, createBranch } from "../../lib/code-integrator/git-workflow.js";
import { loadProjectConfig } from "../../lib/project-config.js";

const config = loadProjectConfig(projectRoot);

// D-16: detect base branch from project config + filesystem markers.
// markerFiles and fallbackBranch are project-specific and live in caller code,
// not in git-workflow itself. Example below shows the EntrepreneurOS-style
// gating; other projects pass their own markers (or none).
const baseBranch = await detectBaseBranch(projectRoot, {
  markerFiles: [
    "client/src/lib/company-guard.tsx",
    "client/src/hooks/use-company.ts",
  ],
  fallbackBranch: "feature/company-system",
  defaultBranch: config.defaultBranch,
});

const featureBranch = `${config.featureBranchPrefix}ui-integration`;
await createBranch(baseBranch, featureBranch);
// Runs: git checkout {baseBranch} && git checkout -b {featureBranch}
```

Then load pages to integrate from the database:

```typescript
// Query pipeline_pages where phase="react-gen" AND status="complete" AND projectId matches
const pages = await db
  .select()
  .from(pipelinePages)
  .where(
    and(
      eq(pipelinePages.projectId, projectId),
      eq(pipelinePages.phase, "react-gen"),
      eq(pipelinePages.status, "complete"),
    ),
  );
```

### Step 2 — Brownfield Audit

Snapshot the existing codebase state before writing anything. Store as `inventory` for all subsequent steps.

```typescript
import { auditBrownfield } from "../../lib/code-integrator/brownfield-audit.js";

const inventory = await auditBrownfield(projectRoot);
// Reads App.tsx for existing routes (ProtectedRoute blocks, path= attrs)
// Reads sidebar.tsx for existing nav items (href= and span text)
// Reads components.json for installed shadcn components
// Reads client/src/pages/ for existing page files
```

Inventory structure (per D-11, D-12):
- `existingRoutes[].path` — all registered route paths
- `existingNavItems[].href` — all nav item hrefs
- `installedShadcnComponents[]` — shadcn component names already installed
- `existingPages[].fileName` — existing page file names

### Step 3 — Per-Page Integration Loop

For each page from Step 1, execute the full integration pipeline:

#### 3a. Fetch HTML

```typescript
const htmlResponse = await fetch(page.uiGenOutput.htmlUrl);

// Per Research Pitfall 1: check for URL expiry
if (htmlResponse.status === 403 || htmlResponse.status === 410) {
  console.error(`URL expired for page ${page.pageName}. Re-run Phase 3 for this page or paste HTML directly.`);
  continue; // skip this page, escalate to user
}

const htmlContent = await htmlResponse.text();
```

#### 3b. Translate HTML to TSX

```typescript
import { translateHtmlToShadcn } from "../../lib/code-integrator/html-to-shadcn.js";

const translationResult = await translateHtmlToShadcn({
  htmlContent,
  pageName: page.pageName,
  pageRoute: page.pageRoute,
  installedComponents: inventory.installedShadcnComponents,
  authLevel: page.authLevel ?? "authenticated", // D-01, D-04
});
// Returns { tsxContent, extractedImports, layoutWrapped }
// Post-translation guard strips useQuery/useMutation/fetch/axios (Pitfall 2)
```

#### 3b-1. Codex Code Review (Plan 04-04)

Run a Codex-style review immediately after translation. Critical findings prompt the user to fix-and-continue, retry with stricter instructions, or skip the page. Fail-open: review unavailability never blocks the pipeline.

```typescript
import { reviewWithCodex } from "../../lib/code-integrator/codex-review.js";

const codexReview = await reviewWithCodex(
  translationResult.tsxContent,
  page.pageName,
);

if (!codexReview.passed) {
  console.log("Codex review findings:");
  for (const issue of codexReview.issues) {
    console.log(`  [${issue.severity}] ${issue.description}`);
  }

  const criticals = codexReview.issues.filter((i) => i.severity === "critical");
  if (criticals.length > 0) {
    console.log("\n⚠ Critical issues found. Options:");
    console.log("  1. Fix manually and continue");
    console.log("  2. Retry translation with stricter instructions");
    console.log("  3. Skip this page");
    // Wait for user decision (orchestrator-level prompt).
    // On retry: re-call translateHtmlToShadcn with `criticals` appended as context.
  }
}
```

#### 3b-2. Code-Review + Simplify Pass (Plan 04-04)

Best-effort secondary review. Both queries fail-open and never block.

```typescript
import {
  queryCodeReviewSkill,
  querySimplifySkill,
} from "../../lib/code-integrator/skill-reviews.js";

const [codeReview, simplifyReview] = await Promise.all([
  queryCodeReviewSkill(translationResult.tsxContent),
  querySimplifySkill(translationResult.tsxContent),
]);

if (codeReview) console.log("Code review findings:\n" + codeReview);
if (simplifyReview) console.log("Simplification opportunities:\n" + simplifyReview);
```

#### 3c. Ensure shadcn Components

```typescript
import { ensureShadcnComponents } from "../../lib/code-integrator/page-writer.js";

await ensureShadcnComponents({
  projectRoot,
  extractedImports: translationResult.extractedImports,
  installedComponents: inventory.installedShadcnComponents,
});
// Per D-03: checks existence before running npx shadcn@latest add
// Updates inventory.installedShadcnComponents in-place
```

#### 3d. Route Conflict Check

```typescript
import { detectRouteConflict } from "../../lib/code-integrator/route-injector.js";

const routeConflict = detectRouteConflict(
  page.pageRoute,
  componentName,
  inventory, // D-10
);

if (routeConflict) {
  // Show both sides to user
  console.log(`Route conflict at ${page.pageRoute}:`);
  console.log(`  Existing: ${routeConflict.existingComponent} (${routeConflict.existingFile})`);
  console.log(`  New: ${routeConflict.newComponent}`);

  const choice = await promptUser("Resolve conflict: [replace/merge/skip]");
  if (choice === "skip") continue;
  // "replace" and "merge" handled in step 3e
}
```

#### 3e. File Conflict Check and Write (D-10)

```typescript
import { checkFileConflict, writePage } from "../../lib/code-integrator/page-writer.js";

const fileConflict = await checkFileConflict({ projectRoot, pageName: page.pageName });

if (fileConflict.exists) {
  // D-10: show existing file and new translated content
  console.log(`File already exists: ${fileConflict.existingPath}`);

  const choice = await promptUser("File exists. Resolve: [replace/merge/skip]");

  if (choice === "skip") continue;

  if (choice === "replace") {
    pageFile = await writePage({
      projectRoot,
      pageName: page.pageName,
      tsxContent: translationResult.tsxContent,
      overwrite: true,
    });
  } else if (choice === "merge") {
    // AI smart-merge: send both existing and new to Claude
    const existingContent = await readFile(fileConflict.existingPath, "utf-8");
    const mergedContent = await mergeWithClaude(existingContent, translationResult.tsxContent);
    pageFile = await writePage({
      projectRoot,
      pageName: page.pageName,
      tsxContent: mergedContent,
      overwrite: true,
    });
  }
} else {
  // No conflict — write normally per D-05
  pageFile = await writePage({
    projectRoot,
    pageName: page.pageName,
    tsxContent: translationResult.tsxContent,
  });
}
```

#### 3f. Inject Route

```typescript
import { injectRoute } from "../../lib/code-integrator/route-injector.js";

// Determine if page needs CompanyGate (D-07, D-08)
// isStandalone=true for auth/onboarding pages that should not be wrapped
const isStandalone = page.authLevel === "public";

await injectRoute({
  appTsxPath,
  componentName,
  importPath: `@/pages/${kebabCase(page.pageName)}`,
  routePath: page.pageRoute,
  wrapCompanyGate: !isStandalone,
  isStandalone,
});
```

#### 3g. Inject Nav Item

```typescript
import { injectNavItem } from "../../lib/code-integrator/nav-injector.js";

// D-09: select remixicon class based on page semantics (Pitfall 7 — must be ri-* not lucide)
const iconClass = selectRemixIcon(page.pageName);
// Examples: reports -> ri-bar-chart-line, settings -> ri-settings-3-line,
//           users -> ri-user-line, analytics -> ri-line-chart-line

await injectNavItem({
  sidebarPath,
  label: page.pageName,
  href: page.pageRoute,
  iconClass,
});
```

#### 3f-1. Verification Before Completion (Plan 04-04)

Run the `superpowers:verification-before-completion` checklist before committing. Fail-open: an unavailable check never blocks the commit.

```typescript
import { queryVerificationSkill } from "../../lib/code-integrator/skill-reviews.js";

const verification = await queryVerificationSkill({
  pageFile,
  routePath: page.pageRoute,
  componentsUsed: translationResult.extractedImports,
});

if (!verification.passed) {
  console.log("Verification issues:");
  for (const issue of verification.issues) {
    console.log(`  - ${issue}`);
  }
  // Escalate to user before committing — they may want to inspect or fix.
}
```

#### 3h. Commit Page (D-14)

```typescript
import { commitPage } from "../../lib/code-integrator/git-workflow.js";

const commitHash = await commitPage(
  page.pageName,
  [
    pageFile,                     // translated TSX page file
    appTsxPath,                   // App.tsx with new route injected
    sidebarPath,                  // sidebar.tsx with new nav item
    ...installedPackageJsonPaths, // package.json if shadcn components were installed
  ],
);
// Commits: "feat(ui): integrate {pageName} page"
// Returns short commit hash (e.g. "abc1234")
```

#### 3i. Update Inventory

After each page, update inventory to prevent false negatives in subsequent pages:

```typescript
inventory.existingRoutes.push({
  path: page.pageRoute,
  componentName,
  filePath: pageFile,
  isProtected: true,
  hasCompanyGate: !isStandalone,
});

inventory.existingNavItems.push({
  label: page.pageName,
  href: page.pageRoute,
  iconClass,
});

inventory.existingPages.push({
  fileName: path.basename(pageFile),
  filePath: pageFile,
  exportName: componentName,
});
```

#### 3j. Write Integration Phase Output

```typescript
await db
  .insert(pipelinePages)
  .values({
    projectId,
    pageName: page.pageName,
    phase: "integration",
    status: "complete",
    output: JSON.stringify({
      pageName: page.pageName,
      pageFile,
      routePath: page.pageRoute,
      committed: true,
      commitHash,
    } satisfies IntegrationPhaseOutput),
  });
```

### Step 4 — Push and PR (D-13, D-15)

After all pages are integrated:

```typescript
import { pushAndCreatePR } from "../../lib/code-integrator/git-workflow.js";

try {
  const prUrl = await pushAndCreatePR(
    featureBranch,
    integratedPages.map((p) => p.pageName),
  );
  console.log(`PR created: ${prUrl}`);
} catch (err) {
  // gh CLI unavailable — print manual instructions
  console.log("gh CLI not available. Create PR manually:");
  console.log(`  git push -u origin ${featureBranch}`);
  console.log(`  Then open a PR from ${featureBranch} -> ${baseBranch}`);
}
```

### Step 5 — Completion Summary

Print a summary table of all integrated pages:

```
Integration complete. Pages integrated:

| Page         | Route         | Commit  | Nav Added |
|--------------|---------------|---------|-----------|
| Reports      | /reports      | abc1234 | yes       |
| Analytics    | /analytics    | def5678 | yes       |
```

## Icon Selection Guide

Use remixicon classes (ri-* format) — sidebar uses remixicon not Lucide React (Pitfall 7).

| Page type | Icon class |
|-----------|-----------|
| Analytics, Charts | `ri-bar-chart-line` or `ri-line-chart-line` |
| Users, Team | `ri-user-line` or `ri-team-line` |
| Settings | `ri-settings-3-line` |
| Reports | `ri-file-chart-line` |
| Dashboard, Home | `ri-dashboard-line` |
| Documents | `ri-file-list-3-line` |
| Messages, Chat | `ri-chat-3-line` |
| Calendar, Schedule | `ri-calendar-line` |
| Billing, Payments | `ri-bank-card-line` |
| Integrations | `ri-plug-line` |
| Notifications | `ri-notification-line` |
| CRM, Contacts | `ri-user-star-line` |
| Tasks | `ri-task-line` |
| Other | `ri-layout-line` |

## Pitfalls

### Pitfall 1: Generated File Freshness
React-gen output files in client/src/pages/ may be stale from a prior run. Verify file timestamps before integration.
- If 403 or 410: notify user to re-run Phase 3 for that page OR paste HTML directly.
- Never silently fail — escalate to user so they can unblock.

### Pitfall 2: Claude Generates Data-Fetching Code
Post-translation, Claude may add `useQuery`, `useMutation`, `fetch`, or `axios` calls.
`translateHtmlToShadcn` runs a guard pass after initial translation:
1. First, one re-prompt with stricter instructions forbidding data fetching
2. Final fallback: regex strip of patterns matching `useQuery|useMutation|fetch\(|axios`

### Pitfall 3: Route Collision (D-10)
Always call `detectRouteConflict` before `injectRoute`. The BrownfieldInventory is updated
incrementally after each page (step 3i) so in-loop collisions are also detected.

### Pitfall 4: File Already Exists (D-10)
Always call `checkFileConflict` before `writePage`. Present user with replace/merge/skip choice.
Never overwrite silently — existing files may have manual edits.

### Pitfall 5: shadcn Interactive Prompt
`ensureShadcnComponents` checks component existence before running `npx shadcn@latest add`.
Do not run the install command if the component is already present — it triggers an interactive
confirmation prompt that blocks execution.

### Pitfall 6: Base Branch Selection (D-16)
`detectBaseBranch` is fully config-driven. Callers pass `markerFiles`,
`fallbackBranch`, and `defaultBranch`. The function checks whether all marker
files exist on the current working tree:
- If yes: returns `defaultBranch` (the dependency work is already in place)
- If no, and the fallback branch exists: returns `fallbackBranch` (dependency
  work still lives there)
- Otherwise: returns `defaultBranch`

The marker files and fallback branch shown above (`company-guard.tsx`,
`feature/company-system`) are an example from EntrepreneurOS. Other projects
pass their own — or pass `{ defaultBranch: config.defaultBranch }` alone to
skip the marker dance entirely.

### Pitfall 7: Sidebar Uses remixicon Not Lucide
The sidebar uses `<i className="ri-*">` elements from the remixicon library.
Do NOT inject Lucide React `<Icon />` components into the nav item template.
The `injectNavItem` function generates `<i className="${input.iconClass}">` — pass ri-* class strings.

## Error Handling

| Error | Recoverable | Action |
|-------|-------------|--------|
| ENV_MISSING (AI_INTEGRATIONS_ANTHROPIC_API_KEY) | No | Print error, abort pipeline |
| HTML_URL_EXPIRED (403/410 from htmlUrl) | Yes | Skip page, notify user to re-run Phase 3 or paste HTML |
| ROUTE_CONFLICT | Yes | D-10: show options, user decides replace/merge/skip |
| FILE_EXISTS | Yes | D-10: checkFileConflict + user decides replace/merge/skip |
| GH_CLI_MISSING | Yes | Print manual `git push` + PR creation instructions |
| TRANSLATION_FAILED | Yes | Retry once with stricter prompt, then escalate to user |
| SHADCN_INSTALL_FAILED | Yes | Log warning, continue — component may still render |
| SIDEBAR_ANCHOR_MISSING | No | Halt page integration, report sidebar.tsx needs manual inspection |
| APP_TSX_ANCHOR_MISSING | No | Halt page integration, report App.tsx needs manual inspection |

## Database Operations

**Read:**
```sql
SELECT * FROM pipeline_pages
WHERE project_id = $projectId
  AND phase = 'react-gen'
  AND status = 'complete';
```

**Write (per page):**
```typescript
INSERT INTO pipeline_pages (project_id, page_name, phase, status, output)
VALUES ($projectId, $pageName, 'integration', 'complete', $integrationOutput);
```

`output` is JSON-encoded `IntegrationPhaseOutput` (from `lib/code-integrator/types.ts`).
