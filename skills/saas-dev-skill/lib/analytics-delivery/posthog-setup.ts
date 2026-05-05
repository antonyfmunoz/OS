import type { TaxonomyReport } from "./types.js";
import { toSnakeCase } from "./taxonomy-auditor.js";

// ─── checkPostHogSetup ────────────────────────────────────────────────────────

/**
 * Checks which PostHog env vars are present in the provided env object.
 * Takes env as parameter (not process.env directly) for testability.
 *
 * Three vars required per D-03:
 * - VITE_POSTHOG_API_KEY: Project API Key (client-side capture)
 * - POSTHOG_PERSONAL_API_KEY: Personal API Key (management API for flag creation)
 * - POSTHOG_PROJECT_ID: numeric project ID for REST API calls
 */
export function checkPostHogSetup(
  env: Record<string, string | undefined>
): { apiKeyPresent: boolean; personalApiKeyPresent: boolean; projectIdPresent: boolean } {
  return {
    apiKeyPresent: Boolean(env.VITE_POSTHOG_API_KEY),
    personalApiKeyPresent: Boolean(env.POSTHOG_PERSONAL_API_KEY),
    projectIdPresent: Boolean(env.POSTHOG_PROJECT_ID),
  };
}

// ─── generateSetupGuide ───────────────────────────────────────────────────────

/**
 * Returns a markdown-formatted setup guide with numbered steps.
 * Addresses review concern about credential type ambiguity:
 * explicitly distinguishes Project API Key (phc_) from Personal API Key (phx_).
 */
export function generateSetupGuide(): string {
  return `# PostHog Setup Guide

## Required: Project API Key (for client-side event capture)

1. Create a PostHog account at https://posthog.com (free tier available)
2. Create a new project in PostHog
3. Copy your **Project API Key** (prefix: \`phc_\`) from Project Settings > Project API Key
4. Add to your .env file:
   \`\`\`
   VITE_POSTHOG_API_KEY=phc_your_project_api_key
   VITE_POSTHOG_HOST=https://app.posthog.com
   \`\`\`

## Optional: Personal API Key (for feature flag management via API)

5. Go to Settings > Personal API Keys
6. Create a new key with "Feature Flags" scope (prefix: \`phx_\`)
7. Find your numeric Project ID in Project Settings > Project ID
8. Add to your .env file:
   \`\`\`
   POSTHOG_PERSONAL_API_KEY=phx_your_personal_api_key
   POSTHOG_PROJECT_ID=your_numeric_project_id
   \`\`\`
9. Restart your development server after adding env vars

## Key Differences

| Key | Prefix | Where it goes | Purpose |
|-----|--------|---------------|---------|
| Project API Key | phc_ | VITE_POSTHOG_API_KEY (client-side) | Captures events from the browser |
| Personal API Key | phx_ | POSTHOG_PERSONAL_API_KEY (server/script only) | Creates feature flags via management API |

Note: Without the Personal API Key, feature flags will not be auto-created.
Client-side event capture works with only the Project API Key.
`;
}

// ─── generateDashboardGuide ───────────────────────────────────────────────────

/**
 * Returns a markdown guide for setting up the baseline PostHog dashboard per D-16.
 * Includes instructions for creating PostHog UI widgets — not programmatic dashboard
 * creation (PostHog dashboard API is undocumented/unstable).
 */
export function generateDashboardGuide(taxonomyReport: TaxonomyReport): string {
  // Extract unique page names from allEvents
  const pageNames = [...new Set(taxonomyReport.allEvents.map((e) => e.pageName))];
  const pageNameList = pageNames.length > 0
    ? pageNames.map((name) => `  - ${name}`).join("\n")
    : "  - (no pages with events found)";

  // Extract unique event names
  const eventNames = [...new Set(taxonomyReport.allEvents.map((e) => e.eventName))];
  const eventNameList = eventNames.length > 0
    ? eventNames.map((name) => `  - \`${name}\``).join("\n")
    : "  - (no custom events found)";

  return `# PostHog Dashboard Setup Guide

Follow these steps in the PostHog UI to create the baseline D-16 dashboard.

## Step 1: Create a New Dashboard

1. Go to your PostHog project at https://app.posthog.com
2. Navigate to **Dashboards** in the left sidebar
3. Click **New dashboard** and name it "Product Analytics"

---

## Widget 1: Page Views

Tracks how many times each page is viewed.

1. Click **Add insight** on your dashboard
2. Select **Trends** insight type
3. Filter by event: \`$pageview\`
4. Add breakdown: \`$current_url\` or \`$pathname\`
5. This dashboard covers these pages:
${pageNameList}
6. Save insight as "Page Views per Page"

---

## Widget 2: Event Counts

Tracks your custom events over time.

1. Click **Add insight** on your dashboard
2. Select **Trends** insight type
3. Add each custom event as a separate series:
${eventNameList}
4. Set time range to **Last 30 days**
5. Save insight as "Custom Event Counts"

---

## Widget 3: Error Tracking

Tracks frontend exceptions automatically.

1. Go to **Session Replay** settings
2. Enable **Exception autocapture** (captures unhandled JS errors)
3. Return to your dashboard and click **Add insight**
4. Select **Trends** insight type
5. Filter by event: \`$exception\`
6. Save insight as "Error Tracking"

---

## Widget 4: User Retention

Tracks how many users return after their first visit.

1. Click **Add insight** on your dashboard
2. Select **Retention** insight type
3. Set **Start event**: \`$pageview\`
4. Set **Return event**: \`$pageview\`
5. Note: Meaningful retention data requires \`posthog.identify()\` to be wired
   so PostHog can track returning users across sessions
6. Save insight as "User Retention"

---

## Notes

- PostHog free tier includes up to 1 million events per month
- Data appears in PostHog within a few minutes of the first event capture
- Enable **Session Replay** for additional debugging context (separate configuration)
`;
}

// ─── createFeatureFlags ───────────────────────────────────────────────────────

/**
 * Creates feature flags in PostHog via the REST API per D-15.
 * Addresses review concern: failures are surfaced as flagWarnings (NOT silent).
 *
 * @param flags - Flag names to create (will be snake_case normalized)
 * @param personalApiKey - PostHog Personal API Key (phx_ prefix)
 * @param projectId - PostHog numeric project ID
 * @param fetchFn - Fetch function (injectable for testing, defaults to global fetch)
 */
export async function createFeatureFlags(
  flags: string[],
  personalApiKey: string,
  projectId: string,
  fetchFn: typeof fetch = fetch
): Promise<{ flagsCreated: string[]; flagsFailed: string[]; flagWarnings: string[] }> {
  const flagsCreated: string[] = [];
  const flagsFailed: string[] = [];
  const flagWarnings: string[] = [];

  for (const flag of flags) {
    const snakeCaseName = toSnakeCase(flag);

    try {
      const res = await fetchFn(
        `https://app.posthog.com/api/projects/${projectId}/feature_flags/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${personalApiKey}`,
          },
          body: JSON.stringify({
            key: snakeCaseName,
            name: flag,
            active: false,
            filters: {
              groups: [{ rollout_percentage: 0 }],
            },
          }),
        }
      );

      const responseText = await res.text();

      if (res.ok) {
        flagsCreated.push(snakeCaseName);
      } else {
        flagsFailed.push(snakeCaseName);
        // Surface failure as warning — NON-BLOCKING but NOT SILENT
        flagWarnings.push(
          `Failed to create flag '${snakeCaseName}': HTTP ${res.status} — ${responseText}`
        );
      }
    } catch (err) {
      flagsFailed.push(snakeCaseName);
      const message = err instanceof Error ? err.message : String(err);
      flagWarnings.push(
        `Failed to create flag '${snakeCaseName}': network error — ${message}`
      );
    }
  }

  return { flagsCreated, flagsFailed, flagWarnings };
}
