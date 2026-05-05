import { describe, it, expect } from "vitest";
import { analyzeGaps, hasBlockingGaps } from "../../../lib/spec-parser/gap-analyzer";
import { formatGapReport } from "../../../lib/spec-parser/spec-approval";
import type { SpecOutput } from "@shared/spec-schema";

// ─── Helpers ─────────────────────────────────────────────────────────────────

function makeMinimalPage(overrides: Record<string, unknown> = {}) {
  return {
    name: "TestPage",
    route: "/test",
    purpose: "A test page",
    components: ["Header"],
    authLevel: "public" as const,
    priority: 1,
    dependsOn: [],
    specVersion: 1,
    source: "explicit" as const,
    dataRequirements: [],
    apiEndpoints: [],
    validationRules: [],
    events: [],
    featureFlagCandidates: [],
    ...overrides,
  };
}

function makeSpec(pages: ReturnType<typeof makeMinimalPage>[], extras: Partial<SpecOutput> = {}): SpecOutput {
  return {
    pages,
    sharedComponents: [],
    suggestedOrder: pages.map((p) => p.route),
    ...extras,
  };
}

// ─── Missing Onboarding Detection ────────────────────────────────────────────

describe("missing onboarding detection", () => {
  it("flags blocking gap when signup exists but no onboarding", async () => {
    const spec = makeSpec([
      makeMinimalPage({ name: "Signup", route: "/signup" }),
      makeMinimalPage({ name: "Dashboard", route: "/dashboard", authLevel: "authenticated" }),
    ]);

    const gaps = await analyzeGaps(spec, { skipLlm: true });
    const onboardingGap = gaps.missingFlows.find((g) => g.category === "missing-flow" && g.description.includes("onboarding"));
    expect(onboardingGap).toBeDefined();
    expect(onboardingGap!.severity).toBe("blocking");
  });

  it("does not flag when onboarding page exists", async () => {
    const spec = makeSpec([
      makeMinimalPage({ name: "Signup", route: "/signup" }),
      makeMinimalPage({ name: "Onboarding", route: "/onboarding", authLevel: "authenticated" }),
      makeMinimalPage({ name: "Dashboard", route: "/dashboard", authLevel: "authenticated" }),
    ]);

    const gaps = await analyzeGaps(spec, { skipLlm: true });
    const onboardingGap = gaps.missingFlows.find((g) => g.description.includes("onboarding"));
    expect(onboardingGap).toBeUndefined();
  });

  it("does not flag when welcome page exists", async () => {
    const spec = makeSpec([
      makeMinimalPage({ name: "Register", route: "/register" }),
      makeMinimalPage({ name: "Welcome", route: "/welcome", authLevel: "authenticated" }),
    ]);

    const gaps = await analyzeGaps(spec, { skipLlm: true });
    const onboardingGap = gaps.missingFlows.find((g) => g.description.includes("onboarding"));
    expect(onboardingGap).toBeUndefined();
  });
});

// ─── Missing 404 Detection ───────────────────────────────────────────────────

describe("missing 404 detection", () => {
  it("flags recommended gap when no 404 page exists", async () => {
    const spec = makeSpec([
      makeMinimalPage({ name: "Home", route: "/" }),
    ]);

    const gaps = await analyzeGaps(spec, { skipLlm: true });
    const notFoundGap = gaps.missingPages.find((g) => g.description.includes("404"));
    expect(notFoundGap).toBeDefined();
    expect(notFoundGap!.severity).toBe("recommended");
  });

  it("does not flag when not-found page exists", async () => {
    const spec = makeSpec([
      makeMinimalPage({ name: "Home", route: "/" }),
      makeMinimalPage({ name: "NotFound", route: "/not-found" }),
    ]);

    const gaps = await analyzeGaps(spec, { skipLlm: true });
    const notFoundGap = gaps.missingPages.find((g) => g.description.includes("404"));
    expect(notFoundGap).toBeUndefined();
  });
});

// ─── Empty State Gaps ────────────────────────────────────────────────────────

describe("empty state gaps per page", () => {
  it("flags pages with dataRequirements but no emptyState", async () => {
    const spec = makeSpec([
      makeMinimalPage({
        name: "Dashboard",
        route: "/dashboard",
        dataRequirements: [{ component: "Chart", fields: ["revenue"] }],
        // no emptyState
      }),
    ]);

    const gaps = await analyzeGaps(spec, { skipLlm: true });
    const emptyGap = gaps.missingStates.find(
      (g) => g.category === "missing-state" && g.description.includes("emptyState") && g.affectedPages.includes("/dashboard"),
    );
    expect(emptyGap).toBeDefined();
    expect(emptyGap!.severity).toBe("recommended");
  });

  it("does not flag pages with emptyState defined", async () => {
    const spec = makeSpec([
      makeMinimalPage({
        name: "Dashboard",
        route: "/dashboard",
        dataRequirements: [{ component: "Chart", fields: ["revenue"] }],
        emptyState: "Shows placeholder chart with sample data",
      }),
    ]);

    const gaps = await analyzeGaps(spec, { skipLlm: true });
    const emptyGap = gaps.missingStates.find(
      (g) => g.description.includes("emptyState") && g.affectedPages.includes("/dashboard"),
    );
    expect(emptyGap).toBeUndefined();
  });
});

// ─── Auth Gap Detection ──────────────────────────────────────────────────────

describe("auth gap detection", () => {
  it("flags blocking gap when signup exists but no password reset", async () => {
    const spec = makeSpec([
      makeMinimalPage({ name: "Login", route: "/login" }),
      makeMinimalPage({ name: "Signup", route: "/signup" }),
      makeMinimalPage({ name: "Dashboard", route: "/dashboard", authLevel: "authenticated" }),
    ]);

    const gaps = await analyzeGaps(spec, { skipLlm: true });
    const authGap = gaps.missingFlows.find((g) => g.category === "auth-gap");
    expect(authGap).toBeDefined();
    expect(authGap!.severity).toBe("blocking");
  });

  it("does not flag when forgot-password page exists", async () => {
    const spec = makeSpec([
      makeMinimalPage({ name: "Login", route: "/login" }),
      makeMinimalPage({ name: "Signup", route: "/signup" }),
      makeMinimalPage({ name: "ForgotPassword", route: "/forgot-password" }),
      makeMinimalPage({ name: "Dashboard", route: "/dashboard", authLevel: "authenticated" }),
    ]);

    const gaps = await analyzeGaps(spec, { skipLlm: true });
    const authGap = gaps.missingFlows.find((g) => g.category === "auth-gap");
    expect(authGap).toBeUndefined();
  });
});

// ─── Orphaned Routes ─────────────────────────────────────────────────────────

describe("orphaned route detection", () => {
  it("flags blocking gap for dependsOn route that does not exist", async () => {
    const spec = makeSpec([
      makeMinimalPage({ name: "Detail", route: "/detail", dependsOn: ["/list"] }),
    ]);

    const gaps = await analyzeGaps(spec, { skipLlm: true });
    const orphan = gaps.missingPages.find((g) => g.category === "orphaned-route");
    expect(orphan).toBeDefined();
    expect(orphan!.severity).toBe("blocking");
    expect(orphan!.description).toContain("/list");
  });
});

// ─── hasBlockingGaps ─────────────────────────────────────────────────────────

describe("hasBlockingGaps", () => {
  it("returns true when blocking gaps exist", async () => {
    const spec = makeSpec([
      makeMinimalPage({ name: "Signup", route: "/signup" }),
      makeMinimalPage({ name: "Dashboard", route: "/dashboard", authLevel: "authenticated" }),
    ]);

    const gaps = await analyzeGaps(spec, { skipLlm: true });
    expect(hasBlockingGaps(gaps)).toBe(true);
  });

  it("returns false when no blocking gaps exist", async () => {
    const spec = makeSpec([
      makeMinimalPage({ name: "Home", route: "/" }),
      makeMinimalPage({ name: "NotFound", route: "/not-found" }),
    ]);

    const gaps = await analyzeGaps(spec, { skipLlm: true });
    expect(hasBlockingGaps(gaps)).toBe(false);
  });
});

// ─── formatGapReport ─────────────────────────────────────────────────────────

describe("formatGapReport", () => {
  it("produces a non-empty report string", async () => {
    const spec = makeSpec([
      makeMinimalPage({ name: "Signup", route: "/signup" }),
      makeMinimalPage({ name: "Dashboard", route: "/dashboard", authLevel: "authenticated" }),
    ]);

    const gaps = await analyzeGaps(spec, { skipLlm: true });
    const report = formatGapReport(spec, gaps);
    expect(report.length).toBeGreaterThan(0);
    expect(report).toContain("Spec Gap Analysis");
    expect(report).toContain("Blocking Issues");
  });

  it("shows no-blocking message when spec is clean", async () => {
    const spec = makeSpec([
      makeMinimalPage({ name: "Home", route: "/" }),
      makeMinimalPage({ name: "NotFound", route: "/not-found" }),
    ]);

    const gaps = await analyzeGaps(spec, { skipLlm: true });
    const report = formatGapReport(spec, gaps);
    expect(report).toContain("No blocking issues found");
  });
});

// ─── Spec With No Gaps ──────────────────────────────────────────────────────

describe("spec with no gaps", () => {
  it("produces empty arrays for a well-defined spec", async () => {
    const spec = makeSpec([
      makeMinimalPage({ name: "Login", route: "/login" }),
      makeMinimalPage({ name: "Signup", route: "/signup" }),
      makeMinimalPage({ name: "ForgotPassword", route: "/forgot-password" }),
      makeMinimalPage({
        name: "Onboarding",
        route: "/onboarding",
        authLevel: "authenticated",
      }),
      makeMinimalPage({
        name: "Dashboard",
        route: "/dashboard",
        authLevel: "authenticated",
        dataRequirements: [{ component: "Chart", fields: ["revenue"] }],
        apiEndpoints: [{ endpoint: "GET /api/metrics", source: "explicit" }],
        emptyState: "Shows getting started guide",
        errorState: "Shows error with retry button",
        mobileConsiderations: "Stacks vertically",
      }),
      makeMinimalPage({
        name: "Settings",
        route: "/settings",
        authLevel: "authenticated",
      }),
      makeMinimalPage({ name: "NotFound", route: "/not-found" }),
    ]);

    const gaps = await analyzeGaps(spec, { skipLlm: true });
    expect(gaps.missingPages).toHaveLength(0);
    expect(gaps.missingFlows).toHaveLength(0);
    expect(gaps.missingStates).toHaveLength(0);
    expect(gaps.assumptions).toHaveLength(0);
    expect(gaps.suggestions).toHaveLength(0);
    expect(gaps.questions).toHaveLength(0);
    expect(hasBlockingGaps(gaps)).toBe(false);
  });
});
