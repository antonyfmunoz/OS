import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtemp, mkdir, writeFile, readFile, rm } from "fs/promises";
import { tmpdir } from "os";
import { join } from "path";
import { injectRoute, detectRouteConflict } from "../../../lib/code-integrator/route-injector.js";
import type { RouteInjectionInput } from "../../../lib/code-integrator/types.js";
import type { BrownfieldInventory } from "../../../lib/code-integrator/types.js";

const MOCK_APP_TSX = `import { Switch, Route } from "wouter";
import { queryClient } from "./lib/queryClient";
import NotFound from "@/pages/not-found";
import Dashboard from "@/pages/dashboard";
import AuthPage from "@/pages/auth-page";
import { AuthProvider } from "@/hooks/use-auth";
import { ProtectedRoute } from "@/lib/protected-route";

function Router() {
  return (
    <Switch>
      <ProtectedRoute path="/" component={Dashboard} />
      <Route path="/auth" component={AuthPage} />
      <Route component={NotFound} />
    </Switch>
  );
}

export default App;
`;

let tmpDir: string;
let appTsxPath: string;

describe("injectRoute", () => {
  beforeEach(async () => {
    tmpDir = await mkdtemp(join(tmpdir(), "route-injector-test-"));
    appTsxPath = join(tmpDir, "App.tsx");
    await writeFile(appTsxPath, MOCK_APP_TSX, "utf-8");
  });

  afterEach(async () => {
    await rm(tmpDir, { recursive: true, force: true });
  });

  it("injects import at top of file (after last existing import)", async () => {
    const input: RouteInjectionInput = {
      appTsxPath,
      componentName: "ReportsPage",
      importPath: "@/pages/reports-page",
      routePath: "/reports",
      wrapCompanyGate: true,
      isStandalone: false,
    };

    await injectRoute(input);
    const result = await readFile(appTsxPath, "utf-8");

    expect(result).toContain('import ReportsPage from "@/pages/reports-page";');
  });

  it("inserts company-gated route before NotFound (wrapCompanyGate=true)", async () => {
    const input: RouteInjectionInput = {
      appTsxPath,
      componentName: "ReportsPage",
      importPath: "@/pages/reports-page",
      routePath: "/reports",
      wrapCompanyGate: true,
      isStandalone: false,
    };

    await injectRoute(input);
    const result = await readFile(appTsxPath, "utf-8");

    // Route should have CompanyGate wrapper
    expect(result).toContain('<ProtectedRoute path="/reports">');
    expect(result).toContain("<CompanyGate>");
    expect(result).toContain("<ReportsPage />");

    // Route should appear before NotFound
    const routeIndex = result.indexOf('<ProtectedRoute path="/reports">');
    const notFoundIndex = result.indexOf("<Route component={NotFound}");
    expect(routeIndex).toBeLessThan(notFoundIndex);
    expect(routeIndex).toBeGreaterThan(-1);
  });

  it("inserts standalone route (wrapCompanyGate=false, isStandalone=true)", async () => {
    const input: RouteInjectionInput = {
      appTsxPath,
      componentName: "OnboardingPage",
      importPath: "@/pages/onboarding-page",
      routePath: "/onboarding",
      wrapCompanyGate: false,
      isStandalone: true,
    };

    await injectRoute(input);
    const result = await readFile(appTsxPath, "utf-8");

    expect(result).toContain('<ProtectedRoute path="/onboarding" component={OnboardingPage} />');
    // Should NOT have CompanyGate wrapper
    expect(result).not.toContain("<CompanyGate>");
  });

  it("Phase A idempotency: re-running with same route+import is a no-op", async () => {
    const input: RouteInjectionInput = {
      appTsxPath,
      componentName: "ReportsPage",
      importPath: "@/pages/reports-page",
      routePath: "/reports",
      wrapCompanyGate: true,
      isStandalone: false,
    };

    await injectRoute(input);
    const after1 = await readFile(appTsxPath, "utf-8");
    await injectRoute(input);
    const after2 = await readFile(appTsxPath, "utf-8");

    expect(after2).toBe(after1);
    // Only one ProtectedRoute for /reports — no duplication.
    const matches = after2.match(/<ProtectedRoute path="\/reports">/g) ?? [];
    expect(matches.length).toBe(1);
  });

  it("preserves all existing content after injection", async () => {
    const input: RouteInjectionInput = {
      appTsxPath,
      componentName: "ReportsPage",
      importPath: "@/pages/reports-page",
      routePath: "/reports",
      wrapCompanyGate: true,
      isStandalone: false,
    };

    await injectRoute(input);
    const result = await readFile(appTsxPath, "utf-8");

    // Original imports still present
    expect(result).toContain('import Dashboard from "@/pages/dashboard"');
    expect(result).toContain('import AuthPage from "@/pages/auth-page"');
    // Original routes still present
    expect(result).toContain('<ProtectedRoute path="/" component={Dashboard} />');
    expect(result).toContain('<Route path="/auth" component={AuthPage} />');
    // NotFound anchor still present
    expect(result).toContain("<Route component={NotFound} />");
  });
});

describe("detectRouteConflict", () => {
  const mockInventory: BrownfieldInventory = {
    existingRoutes: [
      {
        path: "/reports",
        componentName: "OldReportsPage",
        filePath: "client/src/pages/old-reports-page.tsx",
        isProtected: true,
        hasCompanyGate: false,
      },
      {
        path: "/dashboard",
        componentName: "Dashboard",
        filePath: "client/src/pages/dashboard.tsx",
        isProtected: true,
        hasCompanyGate: false,
      },
    ],
    existingPages: [],
    installedShadcnComponents: [],
    existingNavItems: [],
    existingSharedComponents: [],
    existingHooks: [],
  };

  it("finds route collision when path matches existing route", () => {
    const result = detectRouteConflict("/reports", "NewReportsPage", mockInventory);

    expect(result).not.toBeNull();
    expect(result?.routePath).toBe("/reports");
    expect(result?.existingComponent).toBe("OldReportsPage");
    expect(result?.existingFile).toBe("client/src/pages/old-reports-page.tsx");
    expect(result?.newComponent).toBe("NewReportsPage");
  });

  it("returns null for new route with no conflict", () => {
    const result = detectRouteConflict("/analytics", "AnalyticsPage", mockInventory);

    expect(result).toBeNull();
  });
});
