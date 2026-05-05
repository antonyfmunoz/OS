import { describe, it, expect } from "vitest";
import { resolveRowToSpecPage } from "../../../lib/orchestrator/phases/integration-adapter.js";
import type { SpecOutput, PageSpecFull } from "@shared/spec-schema.js";

// Minimal PageSpecFull factory — only fills the fields the resolver reads
// (and the ones the type demands).
function pageSpec(name: string, route: string): PageSpecFull {
  return {
    name,
    route,
    purpose: "",
    components: [],
    authLevel: "authenticated",
    priority: 1,
    dependsOn: [],
    specVersion: 1,
    source: "explicit",
    dataRequirements: [],
    apiEndpoints: [],
    validationRules: [],
    events: [],
    featureFlagCandidates: [],
  };
}

function spec(names: string[]): SpecOutput {
  return {
    pages: names.map((n) => pageSpec(n, `/${n.toLowerCase()}`)),
    sharedComponents: [],
    suggestedOrder: names.map((n) => `/${n.toLowerCase()}`),
    backendSpec: { endpoints: [], drizzleTableHints: [], backgroundJobs: [], mismatches: [] },
  };
}

describe("resolveRowToSpecPage — react-gen row → spec page lookup", () => {
  it("matches by pageName, ignoring stale pageIndex", () => {
    // Spec reordered: what used to be at index 5 is now at index 7
    const s = spec([
      "Login",
      "Signup",
      "ForgotPassword",
      "ResetPassword",
      "CompanySetup",
      "PortfolioList",
      "PortfolioDetail",
      "CommandCenter",
    ]);

    // react-gen row was written when CommandCenter was at index 5
    const staleRow = { pageIndex: 5, pageName: "CommandCenter" };

    const result = resolveRowToSpecPage(staleRow, s);
    expect(result).not.toBeNull();
    expect(result!.page.name).toBe("CommandCenter");
    // Current position in the reordered spec is 7, not the stored 5
    expect(result!.currentSpecIndex).toBe(7);
  });

  it("returns null when the row references a page that no longer exists in the spec", () => {
    const s = spec(["Login", "PortfolioList", "CommandCenter"]);
    // PortfolioDashboard was removed from the spec when PortfolioList replaced it
    const orphanedRow = { pageIndex: 1, pageName: "PortfolioDashboard" };

    expect(resolveRowToSpecPage(orphanedRow, s)).toBeNull();
  });

  it("returns the exact same page reference held in spec.pages", () => {
    const s = spec(["Login", "Settings"]);
    const row = { pageIndex: 99, pageName: "Settings" };
    const result = resolveRowToSpecPage(row, s);

    expect(result).not.toBeNull();
    // Identity check — we want the live spec page, not a copy
    expect(result!.page).toBe(s.pages[1]);
  });

  it("handles the exact drift pattern from the portfolio hierarchy rollout", () => {
    // Before: 13 pages, PortfolioDashboard at index 5
    // After:  14 pages, PortfolioList at index 5, PortfolioDetail at index 6,
    //         all subsequent pages shifted by +1
    const afterSpec = spec([
      "Login",          // 0
      "Signup",         // 1
      "ForgotPassword", // 2
      "ResetPassword",  // 3
      "CompanySetup",   // 4
      "PortfolioList",  // 5 (new)
      "PortfolioDetail",// 6 (new)
      "CommandCenter",  // 7 (was 6)
      "OrgChart",       // 8 (was 7)
      "AgentChat",      // 9 (was 8)
      "TaskBoard",      // 10 (was 9)
      "Workflows",      // 11 (was 10)
      "Settings",       // 12 (was 11)
      "NotFound",       // 13 (was 12)
    ]);

    // A react-gen row written against the OLD spec, when NotFound was at index 12
    const staleNotFound = { pageIndex: 12, pageName: "NotFound" };
    const resolvedNotFound = resolveRowToSpecPage(staleNotFound, afterSpec);
    expect(resolvedNotFound?.page.name).toBe("NotFound");
    expect(resolvedNotFound?.currentSpecIndex).toBe(13);

    // A react-gen row for a now-removed page
    const oldPortfolioDashboard = { pageIndex: 5, pageName: "PortfolioDashboard" };
    expect(resolveRowToSpecPage(oldPortfolioDashboard, afterSpec)).toBeNull();

    // A correctly-placed row that happens to still share its old index
    const login = { pageIndex: 0, pageName: "Login" };
    const resolvedLogin = resolveRowToSpecPage(login, afterSpec);
    expect(resolvedLogin?.page.name).toBe("Login");
    expect(resolvedLogin?.currentSpecIndex).toBe(0);
  });
});
