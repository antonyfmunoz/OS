import { describe, it, expect } from "vitest";
import { auditTaxonomy, toSnakeCase } from "../../../lib/analytics-delivery/taxonomy-auditor.js";
import { PageSpecFull } from "../../../shared/spec-schema.js";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function makePage(overrides: Partial<{
  name: string;
  events: Array<{ name: string; trigger: string; properties?: string[]; source?: "explicit" | "inferred" }>;
  featureFlagCandidates: string[];
}>): PageSpecFull {
  const { name = "TestPage", events = [], featureFlagCandidates = [] } = overrides;
  return PageSpecFull.parse({
    name,
    route: `/${name.toLowerCase().replace(/\s+/g, "-")}`,
    purpose: "Test page",
    components: [],
    authLevel: "public",
    priority: 1,
    dependsOn: [],
    dataRequirements: [],
    apiEndpoints: [],
    validationRules: [],
    events,
    featureFlagCandidates,
  });
}

// ─── Tests: auditTaxonomy ─────────────────────────────────────────────────────

describe("auditTaxonomy", () => {
  it("Test 1: 3 pages (2 with events, 1 without) returns correct TaxonomyReport", () => {
    const pageA = makePage({
      name: "PageA",
      events: [
        { name: "Button Clicked", trigger: "click" },
        { name: "Form Submitted", trigger: "submit" },
      ],
    });
    const pageB = makePage({
      name: "PageB",
      events: [{ name: "Page Viewed", trigger: "load" }],
    });
    const pageC = makePage({ name: "PageC", events: [] });

    const report = auditTaxonomy([pageA, pageB, pageC]);

    expect(report.valid).toBe(true);
    expect(report.totalPages).toBe(3);
    expect(report.pagesWithEvents).toBe(2);
    expect(report.pagesWithoutEvents).toEqual(["PageC"]);
    expect(report.totalEvents).toBe(3);
  });

  it("Test 2: all pages with events returns pagesWithoutEvents=[] and valid=true", () => {
    const pageA = makePage({
      name: "PageA",
      events: [{ name: "Page Viewed", trigger: "load" }],
    });
    const pageB = makePage({
      name: "PageB",
      events: [{ name: "Button Clicked", trigger: "click" }],
    });

    const report = auditTaxonomy([pageA, pageB]);

    expect(report.valid).toBe(true);
    expect(report.pagesWithoutEvents).toEqual([]);
  });

  it("Test 3: empty array returns valid=false with error — does NOT throw", () => {
    expect(() => auditTaxonomy([])).not.toThrow();
    const report = auditTaxonomy([]);
    expect(report.valid).toBe(false);
    expect(report.errors.length).toBeGreaterThan(0);
    expect(report.errors[0]).toContain("no page specs provided");
    expect(report.totalPages).toBe(0);
  });

  it("Test 4: collects all featureFlagCandidates across pages into allFlagCandidates", () => {
    const pageA = makePage({
      name: "PageA",
      events: [{ name: "Page Viewed", trigger: "load" }],
      featureFlagCandidates: ["flag-a", "flag-b"],
    });
    const pageB = makePage({
      name: "PageB",
      events: [{ name: "Page Viewed", trigger: "load" }],
      featureFlagCandidates: ["flag-c"],
    });

    const report = auditTaxonomy([pageA, pageB]);

    expect(report.allFlagCandidates).toContain("flag-a");
    expect(report.allFlagCandidates).toContain("flag-b");
    expect(report.allFlagCandidates).toContain("flag-c");
  });

  it("Test 9: detects collision when two events normalize to same snake_case key", () => {
    const pageA = makePage({
      name: "PageA",
      events: [{ name: "API Error", trigger: "error" }],
    });
    const pageB = makePage({
      name: "PageB",
      events: [{ name: "api_error", trigger: "error" }],
    });

    const report = auditTaxonomy([pageA, pageB]);

    expect(report.collisions).toContain("api_error");
    expect(report.warnings.some((w) => w.includes("api_error"))).toBe(true);
  });

  it("Test 10: events already in snake_case return no collisions", () => {
    const pageA = makePage({
      name: "PageA",
      events: [
        { name: "page_viewed", trigger: "load" },
        { name: "button_clicked", trigger: "click" },
      ],
    });

    const report = auditTaxonomy([pageA]);

    expect(report.collisions).toEqual([]);
  });
});

// ─── Tests: toSnakeCase ───────────────────────────────────────────────────────

describe("toSnakeCase", () => {
  it("Test 5: 'Page Viewed' returns 'page_viewed'", () => {
    expect(toSnakeCase("Page Viewed")).toBe("page_viewed");
  });

  it("Test 6: 'form-submitted' returns 'form_submitted'", () => {
    expect(toSnakeCase("form-submitted")).toBe("form_submitted");
  });

  it("Test 7: 'Button Click!' returns 'button_click'", () => {
    expect(toSnakeCase("Button Click!")).toBe("button_click");
  });

  it("Test 8: '  Mixed CASE--name  ' returns 'mixed_case_name'", () => {
    expect(toSnakeCase("  Mixed CASE--name  ")).toBe("mixed_case_name");
  });
});
