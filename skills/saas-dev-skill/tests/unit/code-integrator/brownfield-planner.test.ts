import { describe, it, expect } from "vitest";
import {
  planBrownfieldIntegration,
  renderIntegrationPlanMarkdown,
} from "../../../lib/code-integrator/brownfield-planner.js";
import type { BrownfieldInventory } from "../../../lib/code-integrator/types.js";
import type { PageSpecFull } from "@shared/spec-schema.js";

function makePage(name: string, route: string): PageSpecFull {
  return {
    name,
    route,
    authLevel: "authenticated",
    description: "",
    layout: { type: "standard" },
    components: [],
    data: { entities: [] },
    events: [],
  } as unknown as PageSpecFull;
}

function emptyInventory(): BrownfieldInventory {
  return {
    existingRoutes: [],
    existingPages: [],
    installedShadcnComponents: [],
    existingNavItems: [],
    existingSharedComponents: [],
    existingHooks: [],
  };
}

describe("planBrownfieldIntegration", () => {
  it("create: nothing in repo → fresh creation", () => {
    const plan = planBrownfieldIntegration({
      specPages: [makePage("Reports", "/reports")],
      inventory: emptyInventory(),
    });
    expect(plan.entries).toHaveLength(1);
    expect(plan.entries[0].mode).toBe("create");
    expect(plan.entries[0].targetFile).toBe("reports-page.tsx");
  });

  it("skip: same route AND same component identifier already wired", () => {
    const inv = emptyInventory();
    inv.existingRoutes.push({
      path: "/reports",
      componentName: "Reports",
      filePath: "client/src/pages/reports.tsx",
      isProtected: true,
      hasCompanyGate: false,
    });
    inv.existingPages.push({
      fileName: "reports.tsx",
      filePath: "client/src/pages/reports.tsx",
      exportName: "Reports",
    });

    const plan = planBrownfieldIntegration({
      specPages: [makePage("Reports", "/reports")],
      inventory: inv,
    });
    expect(plan.entries[0].mode).toBe("skip");
  });

  it("replace: same route, no preserved behavior in existing source", () => {
    const inv = emptyInventory();
    inv.existingRoutes.push({
      path: "/reports",
      componentName: "OldReports",
      filePath: "client/src/pages/old-reports.tsx",
      isProtected: true,
      hasCompanyGate: false,
    });
    inv.existingPages.push({
      fileName: "old-reports.tsx",
      filePath: "client/src/pages/old-reports.tsx",
      exportName: "OldReports",
    });

    const plan = planBrownfieldIntegration({
      specPages: [makePage("Reports", "/reports")],
      inventory: inv,
      pageSources: { "old-reports.tsx": "export default function OldReports() { return null; }" },
    });
    expect(plan.entries[0].mode).toBe("replace");
    expect(plan.entries[0].existingFile).toBe("client/src/pages/old-reports.tsx");
    expect(plan.entries[0].needsReview).toBe(false);
  });

  it("merge: same route AND existing source uses Firebase auth", () => {
    const inv = emptyInventory();
    inv.existingRoutes.push({
      path: "/auth",
      componentName: "AuthPage",
      filePath: "client/src/pages/auth-page.tsx",
      isProtected: false,
      hasCompanyGate: false,
    });
    inv.existingPages.push({
      fileName: "auth-page.tsx",
      filePath: "client/src/pages/auth-page.tsx",
      exportName: "AuthPage",
    });

    const plan = planBrownfieldIntegration({
      specPages: [makePage("Login", "/auth")],
      inventory: inv,
      pageSources: {
        "auth-page.tsx": `import { signInWithPopup } from "firebase/auth"; export default function AuthPage() {}`,
      },
    });
    expect(plan.entries[0].mode).toBe("merge");
    expect(plan.entries[0].needsReview).toBe(true);
  });

  it("supplement: name matches existing page but route is different", () => {
    const inv = emptyInventory();
    inv.existingPages.push({
      fileName: "dashboard.tsx",
      filePath: "client/src/pages/dashboard.tsx",
      exportName: "Dashboard",
    });

    const plan = planBrownfieldIntegration({
      specPages: [makePage("Dashboard", "/admin/dashboard")],
      inventory: inv,
    });
    expect(plan.entries[0].mode).toBe("supplement");
  });

  it("orphan pages: existing pages no spec entry mapped to are surfaced", () => {
    const inv = emptyInventory();
    inv.existingPages.push({
      fileName: "legacy-page.tsx",
      filePath: "client/src/pages/legacy-page.tsx",
      exportName: "LegacyPage",
    });

    const plan = planBrownfieldIntegration({
      specPages: [makePage("Reports", "/reports")],
      inventory: inv,
    });
    expect(plan.orphanPages).toHaveLength(1);
    expect(plan.orphanPages[0].fileName).toBe("legacy-page.tsx");
  });
});

describe("renderIntegrationPlanMarkdown", () => {
  it("renders summary counts and per-page sections", () => {
    const inv = emptyInventory();
    const plan = planBrownfieldIntegration({
      specPages: [makePage("Reports", "/reports"), makePage("Settings", "/settings")],
      inventory: inv,
    });
    const md = renderIntegrationPlanMarkdown(plan);
    expect(md).toContain("# Brownfield Integration Plan");
    expect(md).toContain("create:     2");
    expect(md).toContain("Reports → `/reports`");
    expect(md).toContain("Settings → `/settings`");
  });
});
