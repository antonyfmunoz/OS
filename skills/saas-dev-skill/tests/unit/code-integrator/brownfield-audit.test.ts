import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtemp, mkdir, writeFile, rm } from "fs/promises";
import { tmpdir } from "os";
import { join } from "path";
import { auditBrownfield } from "../../../lib/code-integrator/brownfield-audit.js";
import { BrownfieldInventorySchema } from "../../../lib/code-integrator/types.js";

// ─── Test Fixtures ────────────────────────────────────────────────────────────

const MOCK_APP_TSX = `
import Dashboard from "@/pages/dashboard";
import AuthPage from "@/pages/auth-page";
import { ProtectedRoute } from "@/lib/protected-route";
import { CompanyGate } from "@/lib/company-guard";
import CompanySetupPage from "@/pages/company-setup-page";

function Router() {
  return (
    <Switch>
      <ProtectedRoute path="/home">
        {() => (
          <CompanyGate>
            <Dashboard />
          </CompanyGate>
        )}
      </ProtectedRoute>
      <ProtectedRoute path="/company-setup" component={CompanySetupPage} />
    </Switch>
  );
}
`.trim();

const MOCK_SIDEBAR_TSX = `
import { Link } from "wouter";

export function Sidebar() {
  return (
    <nav>
      <ul>
        <li>
          <Link href="/home">
            <div>
              <i className="ri-home-4-line"></i>
              <span>Home</span>
            </div>
          </Link>
        </li>
        <li>
          <Link href="/tasks">
            <div>
              <i className="ri-task-line"></i>
              <span>Tasks</span>
            </div>
          </Link>
        </li>
      </ul>
    </nav>
  );
}
`.trim();

const MOCK_DASHBOARD = `
import React from "react";

export default function Dashboard() {
  return <div>Dashboard</div>;
}
`.trim();

const MOCK_AUTH_PAGE = `
import React from "react";

export default function AuthPage() {
  return <div>Auth</div>;
}
`.trim();

const MOCK_USE_AUTH = `
import { useContext } from "react";

export function useAuth() {
  return useContext(AuthContext);
}
`.trim();

const MOCK_AGENT_CARD = `
import React from "react";

export function AgentCard() {
  return <div>Agent</div>;
}
`.trim();

// ─── Test Setup ───────────────────────────────────────────────────────────────

let tempDir: string;

beforeEach(async () => {
  tempDir = await mkdtemp(join(tmpdir(), "brownfield-test-"));

  // Create mock directory structure
  await mkdir(join(tempDir, "client", "src", "pages"), { recursive: true });
  await mkdir(join(tempDir, "client", "src", "components", "ui"), { recursive: true });
  await mkdir(join(tempDir, "client", "src", "hooks"), { recursive: true });

  // Write App.tsx
  await writeFile(join(tempDir, "client", "src", "App.tsx"), MOCK_APP_TSX, "utf8");

  // Write sidebar.tsx
  await writeFile(join(tempDir, "client", "src", "components", "sidebar.tsx"), MOCK_SIDEBAR_TSX, "utf8");

  // Write page files
  await writeFile(join(tempDir, "client", "src", "pages", "dashboard.tsx"), MOCK_DASHBOARD, "utf8");
  await writeFile(join(tempDir, "client", "src", "pages", "auth-page.tsx"), MOCK_AUTH_PAGE, "utf8");

  // Write ui components
  await writeFile(join(tempDir, "client", "src", "components", "ui", "button.tsx"), "", "utf8");
  await writeFile(join(tempDir, "client", "src", "components", "ui", "card.tsx"), "", "utf8");
  await writeFile(join(tempDir, "client", "src", "components", "ui", "dialog.tsx"), "", "utf8");

  // Write hooks
  await writeFile(join(tempDir, "client", "src", "hooks", "use-auth.tsx"), MOCK_USE_AUTH, "utf8");

  // Write shared component
  await writeFile(join(tempDir, "client", "src", "components", "agent-card.tsx"), MOCK_AGENT_CARD, "utf8");
});

afterEach(async () => {
  await rm(tempDir, { recursive: true, force: true });
});

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("auditBrownfield", () => {
  it("returns a valid BrownfieldInventory that passes schema validation", async () => {
    const result = await auditBrownfield(tempDir);
    expect(() => BrownfieldInventorySchema.parse(result)).not.toThrow();
  });

  it("extracts existing routes from App.tsx ProtectedRoute entries", async () => {
    const result = await auditBrownfield(tempDir);
    expect(result.existingRoutes.length).toBeGreaterThanOrEqual(2);

    const homeRoute = result.existingRoutes.find((r) => r.path === "/home");
    expect(homeRoute).toBeDefined();
    expect(homeRoute?.isProtected).toBe(true);
    expect(homeRoute?.hasCompanyGate).toBe(true);

    const setupRoute = result.existingRoutes.find((r) => r.path === "/company-setup");
    expect(setupRoute).toBeDefined();
    expect(setupRoute?.isProtected).toBe(true);
    expect(setupRoute?.hasCompanyGate).toBe(false);
  });

  it("lists existing page files from client/src/pages/", async () => {
    const result = await auditBrownfield(tempDir);
    const fileNames = result.existingPages.map((p) => p.fileName);
    expect(fileNames).toContain("dashboard.tsx");
    expect(fileNames).toContain("auth-page.tsx");
  });

  it("lists installed shadcn components from client/src/components/ui/", async () => {
    const result = await auditBrownfield(tempDir);
    expect(result.installedShadcnComponents).toContain("button");
    expect(result.installedShadcnComponents).toContain("card");
    expect(result.installedShadcnComponents).toContain("dialog");
  });

  it("extracts nav items from sidebar.tsx with label, href, and iconClass", async () => {
    const result = await auditBrownfield(tempDir);
    expect(result.existingNavItems.length).toBeGreaterThanOrEqual(2);

    const homeNav = result.existingNavItems.find((n) => n.href === "/home");
    expect(homeNav).toBeDefined();
    expect(homeNav?.label).toBe("Home");
    expect(homeNav?.iconClass).toBe("ri-home-4-line");

    const tasksNav = result.existingNavItems.find((n) => n.href === "/tasks");
    expect(tasksNav).toBeDefined();
    expect(tasksNav?.label).toBe("Tasks");
    expect(tasksNav?.iconClass).toBe("ri-task-line");
  });

  it("lists existing shared components (top-level tsx, not ui/ subdirectory)", async () => {
    const result = await auditBrownfield(tempDir);
    expect(result.existingSharedComponents).toContain("agent-card.tsx");
    // sidebar.tsx is in components root too
    expect(result.existingSharedComponents).toContain("sidebar.tsx");
    // ui components should NOT be in shared components
    expect(result.existingSharedComponents).not.toContain("button.tsx");
  });

  it("lists existing hooks from client/src/hooks/", async () => {
    const result = await auditBrownfield(tempDir);
    expect(result.existingHooks).toContain("use-auth.tsx");
  });
});
