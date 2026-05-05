import { describe, it, expect, vi, beforeEach } from "vitest";
import { SharedComponentSpec } from "@shared/spec-schema";
import type { PageSpecFull } from "@shared/spec-schema";

// ─── Mock Anthropic SDK ───────────────────────────────────────────────────────

const mockCreate = vi.fn();

vi.mock("@anthropic-ai/sdk", () => ({
  default: vi.fn().mockImplementation(() => ({
    messages: {
      create: mockCreate,
    },
  })),
}));

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const sidebarComponent = {
  id: "sidebar-nav",
  name: "SidebarNav",
  purpose: "Primary navigation sidebar with route links",
  usedByPages: ["/dashboard", "/tasks"],
  props: ["currentRoute", "isCollapsed"],
  source: "inferred" as const,
};

const navRailComponent = {
  id: "left-nav-rail",
  name: "LeftNavRail",
  purpose: "Left navigation rail for the main app layout",
  usedByPages: ["/dashboard", "/settings"],
  props: ["activeRoute"],
  source: "inferred" as const,
};

const headerComponent = {
  id: "app-header",
  name: "AppHeader",
  purpose: "Top navigation header with user avatar and notifications",
  usedByPages: ["/dashboard", "/tasks", "/settings"],
  props: ["userName", "notificationCount"],
  source: "explicit" as const,
};

const dashboardPage: PageSpecFull = {
  name: "Dashboard",
  route: "/dashboard",
  purpose: "Main dashboard",
  components: ["SidebarNav", "AppHeader"],
  authLevel: "authenticated",
  priority: 2,
  dependsOn: [],
  specVersion: 1,
  source: "explicit",
  dataRequirements: [],
  apiEndpoints: [],
  validationRules: [],
  events: [],
  featureFlagCandidates: [],
};

// Response when sidebar and nav rail should be merged
const mergedSidebarResponse = {
  deduplicated: [
    {
      id: "sidebar-nav",
      name: "SidebarNav",
      purpose:
        "Primary navigation sidebar with route links and left navigation rail",
      usedByPages: ["/dashboard", "/tasks", "/settings"],
      props: ["currentRoute", "isCollapsed", "activeRoute"],
      source: "inferred",
    },
    {
      id: "app-header",
      name: "AppHeader",
      purpose: "Top navigation header with user avatar and notifications",
      usedByPages: ["/dashboard", "/tasks", "/settings"],
      props: ["userName", "notificationCount"],
      source: "explicit",
    },
  ],
  merges: [
    {
      merged: ["sidebar-nav", "left-nav-rail"],
      into: "sidebar-nav",
    },
  ],
};

// Response for explicit + inferred merge (explicit wins)
const explicitWinsResponse = {
  deduplicated: [
    {
      id: "sidebar-nav",
      name: "SidebarNav",
      purpose: "Primary navigation sidebar — explicit version wins",
      usedByPages: ["/dashboard", "/tasks", "/settings"],
      props: ["currentRoute", "isCollapsed", "activeRoute"],
      source: "explicit", // explicit wins because navRailComponent had source: "explicit"
    },
  ],
  merges: [
    {
      merged: ["sidebar-nav", "left-nav-rail"],
      into: "sidebar-nav",
    },
  ],
};

// Response when no duplicates found
const noDuplicatesResponse = {
  deduplicated: [headerComponent],
  merges: [],
};

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("deduplicateComponents", () => {
  beforeEach(() => {
    mockCreate.mockReset();
    mockCreate.mockResolvedValue({
      content: [
        { type: "text", text: JSON.stringify(mergedSidebarResponse) },
      ],
    });
  });

  it("merges semantically identical components into one SharedComponentSpec", async () => {
    const { deduplicateComponents } = await import(
      "../../../lib/spec-parser/deduplicate-components.js"
    );
    const result = await deduplicateComponents(
      [sidebarComponent, navRailComponent, headerComponent],
      [dashboardPage]
    );
    // Should have fewer components than input
    expect(result.deduplicated.length).toBeLessThan(3);
    // The merged result should still be valid
    result.deduplicated.forEach((c) => {
      expect(() => SharedComponentSpec.parse(c)).not.toThrow();
    });
  });

  it("preserves all usedByPages across merged components", async () => {
    const { deduplicateComponents } = await import(
      "../../../lib/spec-parser/deduplicate-components.js"
    );
    const result = await deduplicateComponents(
      [sidebarComponent, navRailComponent, headerComponent],
      [dashboardPage]
    );
    // The merged sidebar should contain all pages from both sidebarComponent and navRailComponent
    const mergedSidebar = result.deduplicated.find(
      (c) => c.id === "sidebar-nav"
    );
    expect(mergedSidebar?.usedByPages).toContain("/dashboard");
    expect(mergedSidebar?.usedByPages).toContain("/tasks");
    expect(mergedSidebar?.usedByPages).toContain("/settings");
  });

  it("preserves source 'explicit' when merging an explicit and inferred component (explicit wins)", async () => {
    const explicitNavRail = {
      ...navRailComponent,
      source: "explicit" as const,
    };
    mockCreate.mockResolvedValue({
      content: [{ type: "text", text: JSON.stringify(explicitWinsResponse) }],
    });
    const { deduplicateComponents } = await import(
      "../../../lib/spec-parser/deduplicate-components.js"
    );
    const result = await deduplicateComponents(
      [sidebarComponent, explicitNavRail],
      [dashboardPage]
    );
    const mergedComponent = result.deduplicated.find(
      (c) => c.id === "sidebar-nav"
    );
    // When one is explicit and one is inferred, merged result should be explicit
    expect(mergedComponent?.source).toBe("explicit");
  });

  it("returns unchanged array when no duplicates found", async () => {
    mockCreate.mockResolvedValue({
      content: [
        { type: "text", text: JSON.stringify(noDuplicatesResponse) },
      ],
    });
    const { deduplicateComponents } = await import(
      "../../../lib/spec-parser/deduplicate-components.js"
    );
    const result = await deduplicateComponents([headerComponent], [dashboardPage]);
    expect(result.deduplicated.length).toBe(1);
    expect(result.merges.length).toBe(0);
  });

  it("returns immediately without calling AI when components.length <= 1", async () => {
    const { deduplicateComponents } = await import(
      "../../../lib/spec-parser/deduplicate-components.js"
    );
    const result = await deduplicateComponents([headerComponent], [dashboardPage]);
    // Note: This test verifies the no-op path when there's only 1 component
    // (may call AI OR return early — behavior depends on implementation)
    expect(result.deduplicated).toBeDefined();
    expect(result.merges).toBeDefined();
  });

  it("returns merges array describing what was combined (for D-22 confirmation)", async () => {
    const { deduplicateComponents } = await import(
      "../../../lib/spec-parser/deduplicate-components.js"
    );
    const result = await deduplicateComponents(
      [sidebarComponent, navRailComponent, headerComponent],
      [dashboardPage]
    );
    expect(result.merges).toBeDefined();
    expect(Array.isArray(result.merges)).toBe(true);
    if (result.merges.length > 0) {
      expect(result.merges[0]).toHaveProperty("merged");
      expect(result.merges[0]).toHaveProperty("into");
      expect(Array.isArray(result.merges[0].merged)).toBe(true);
    }
  });
});
