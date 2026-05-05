import { describe, it, expect, vi } from "vitest";
import {
  checkPostHogSetup,
  generateSetupGuide,
  createFeatureFlags,
  generateDashboardGuide,
} from "../../../lib/analytics-delivery/posthog-setup.js";
import type { TaxonomyReport } from "../../../lib/analytics-delivery/types.js";

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const fullEnv = {
  VITE_POSTHOG_API_KEY: "phc_test_key",
  POSTHOG_PERSONAL_API_KEY: "phx_test_key",
  POSTHOG_PROJECT_ID: "12345",
};

const emptyEnv: Record<string, string | undefined> = {};

const mockTaxonomyReport: TaxonomyReport = {
  valid: true,
  errors: [],
  warnings: [],
  totalPages: 2,
  pagesWithEvents: 2,
  pagesWithoutEvents: [],
  totalEvents: 4,
  allEvents: [
    { pageName: "Dashboard", eventName: "dashboard_viewed", originalName: "dashboard viewed", trigger: "load" },
    { pageName: "Dashboard", eventName: "export_clicked", originalName: "export clicked", trigger: "click" },
    { pageName: "Settings", eventName: "settings_viewed", originalName: "settings viewed", trigger: "page_view" },
    { pageName: "Settings", eventName: "save_settings", originalName: "save settings", trigger: "submit" },
  ],
  allFlagCandidates: ["new_dashboard", "beta_export"],
  collisions: [],
};

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("checkPostHogSetup", () => {
  it("Test 1: returns apiKeyPresent=true when VITE_POSTHOG_API_KEY is set", () => {
    const result = checkPostHogSetup(fullEnv);
    expect(result.apiKeyPresent).toBe(true);
  });

  it("Test 2: returns all false when no env vars set", () => {
    const result = checkPostHogSetup(emptyEnv);
    expect(result.apiKeyPresent).toBe(false);
    expect(result.personalApiKeyPresent).toBe(false);
    expect(result.projectIdPresent).toBe(false);
  });

  it("returns personalApiKeyPresent=true when POSTHOG_PERSONAL_API_KEY is set", () => {
    const result = checkPostHogSetup(fullEnv);
    expect(result.personalApiKeyPresent).toBe(true);
  });

  it("returns projectIdPresent=true when POSTHOG_PROJECT_ID is set", () => {
    const result = checkPostHogSetup(fullEnv);
    expect(result.projectIdPresent).toBe(true);
  });
});

describe("generateSetupGuide", () => {
  it("Test 3: returns string with numbered steps, posthog.com, and all required env var names", () => {
    const guide = generateSetupGuide();
    expect(guide).toContain("1.");
    expect(guide).toContain("posthog.com");
    expect(guide).toContain("VITE_POSTHOG_API_KEY");
    expect(guide).toContain("POSTHOG_PERSONAL_API_KEY");
    expect(guide).toContain("POSTHOG_PROJECT_ID");
  });

  it("Test 4: distinguishes Project API Key (phc_ prefix) from Personal API Key (phx_ prefix)", () => {
    const guide = generateSetupGuide();
    expect(guide).toContain("Project API Key");
    expect(guide).toContain("Personal API Key");
    expect(guide).toContain("phc_");
    expect(guide).toContain("phx_");
  });

  it("Test 12: mentions phc_ prefix for Project API Key and phx_ prefix for Personal API Key", () => {
    const guide = generateSetupGuide();
    expect(guide).toContain("phc_");
    expect(guide).toContain("phx_");
  });
});

describe("createFeatureFlags", () => {
  it("Test 5: with mocked fetch (200 OK) returns flagsCreated=['flag_one','flag_two'], empty failed and warnings", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      text: async () => "{}",
    });

    const result = await createFeatureFlags(
      ["flag one", "flag two"],
      "phx_test_key",
      "12345",
      mockFetch as unknown as typeof fetch
    );

    expect(result.flagsCreated).toEqual(["flag_one", "flag_two"]);
    expect(result.flagsFailed).toEqual([]);
    expect(result.flagWarnings).toEqual([]);
  });

  it("Test 6: with mocked fetch (400 error) returns flagsFailed populated and flagWarnings with descriptive message", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      text: async () => "Bad Request",
    });

    const result = await createFeatureFlags(
      ["flag one"],
      "phx_test_key",
      "12345",
      mockFetch as unknown as typeof fetch
    );

    expect(result.flagsCreated).toEqual([]);
    expect(result.flagsFailed).toEqual(["flag_one"]);
    expect(result.flagWarnings).toHaveLength(1);
    expect(result.flagWarnings[0]).toContain("flag_one");
    expect(result.flagWarnings[0]).toContain("400");
  });

  it("Test 7: normalizes flag names to snake_case", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      text: async () => "{}",
    });

    const result = await createFeatureFlags(
      ["My Feature Flag"],
      "phx_test_key",
      "12345",
      mockFetch as unknown as typeof fetch
    );

    expect(result.flagsCreated).toContain("my_feature_flag");
  });

  it("Test 8: sends POST to correct PostHog API URL with Authorization Bearer header", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      text: async () => "{}",
    });

    await createFeatureFlags(
      ["test flag"],
      "phx_my_key",
      "99999",
      mockFetch as unknown as typeof fetch
    );

    expect(mockFetch).toHaveBeenCalledWith(
      "https://app.posthog.com/api/projects/99999/feature_flags/",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          Authorization: "Bearer phx_my_key",
        }),
      })
    );
  });

  it("Test 9: request body contains active=false and rollout_percentage=0", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      text: async () => "{}",
    });

    await createFeatureFlags(
      ["beta feature"],
      "phx_key",
      "12345",
      mockFetch as unknown as typeof fetch
    );

    const callArgs = mockFetch.mock.calls[0];
    const body = JSON.parse(callArgs[1].body);
    expect(body.active).toBe(false);
    expect(body.filters.groups[0].rollout_percentage).toBe(0);
  });
});

describe("generateDashboardGuide", () => {
  it("Test 10: returns markdown with Page Views, Event Counts, Error Tracking, User Retention sections", () => {
    const guide = generateDashboardGuide(mockTaxonomyReport);
    expect(guide).toContain("Page Views");
    expect(guide).toContain("Event Counts");
    expect(guide).toContain("Error Tracking");
    expect(guide).toContain("User Retention");
  });

  it("Test 11: includes page names from TaxonomyReport in the guide", () => {
    const guide = generateDashboardGuide(mockTaxonomyReport);
    expect(guide).toContain("Dashboard");
    expect(guide).toContain("Settings");
  });
});
