import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtemp, writeFile, readFile, rm } from "fs/promises";
import { tmpdir } from "os";
import { join } from "path";
import { injectNavItem } from "../../../lib/code-integrator/nav-injector.js";
import type { NavInjectionInput } from "../../../lib/code-integrator/types.js";

const MOCK_SIDEBAR_TSX = `import { Link, useLocation } from "wouter";
import { cn } from "@/lib/utils";

export function Sidebar() {
  const [location] = useLocation();

  return (
    <nav className="p-4">
      <ul className="space-y-2">
        <li>
          <Link href="/">
            <div className={cn(
              "flex items-center space-x-2 p-2 rounded-md cursor-pointer",
              location === "/"
                ? "bg-blue-50 text-primary font-medium"
                : "hover:bg-gray-100 text-gray-700"
            )}>
              <i className="ri-dashboard-line"></i>
              <span>Dashboard</span>
            </div>
          </Link>
        </li>
        <li>
          <Link href="/tasks">
            <div className={cn(
              "flex items-center space-x-2 p-2 rounded-md cursor-pointer",
              location === "/tasks"
                ? "bg-blue-50 text-primary font-medium"
                : "hover:bg-gray-100 text-gray-700"
            )}>
              <i className="ri-task-line"></i>
              <span>Task Board</span>
            </div>
          </Link>
        </li>
      </ul>
    </nav>
  );
}
`;

let tmpDir: string;
let sidebarPath: string;

describe("injectNavItem", () => {
  beforeEach(async () => {
    tmpDir = await mkdtemp(join(tmpdir(), "nav-injector-test-"));
    sidebarPath = join(tmpDir, "sidebar.tsx");
    await writeFile(sidebarPath, MOCK_SIDEBAR_TSX, "utf-8");
  });

  afterEach(async () => {
    await rm(tmpDir, { recursive: true, force: true });
  });

  it("inserts nav item before the closing </ul>", async () => {
    const input: NavInjectionInput = {
      sidebarPath,
      label: "Reports",
      href: "/reports",
      iconClass: "ri-bar-chart-line",
    };

    await injectNavItem(input);
    const result = await readFile(sidebarPath, "utf-8");

    // New item should appear before </ul>
    const newItemIndex = result.indexOf('href="/reports"');
    const closingUlIndex = result.indexOf("</ul>");
    expect(newItemIndex).toBeGreaterThan(-1);
    expect(newItemIndex).toBeLessThan(closingUlIndex);
  });

  it("nav item has correct structure with Link, div, icon and label", async () => {
    const input: NavInjectionInput = {
      sidebarPath,
      label: "Reports",
      href: "/reports",
      iconClass: "ri-bar-chart-line",
    };

    await injectNavItem(input);
    const result = await readFile(sidebarPath, "utf-8");

    // Check Link with href
    expect(result).toContain('href="/reports"');
    // Check div with cn() class utility
    expect(result).toContain("cn(");
    // Check icon with correct remixicon class
    expect(result).toContain('"ri-bar-chart-line"');
    // Check label span
    expect(result).toContain("<span>Reports</span>");
  });

  it("uses location variable for active state detection", async () => {
    const input: NavInjectionInput = {
      sidebarPath,
      label: "Reports",
      href: "/reports",
      iconClass: "ri-bar-chart-line",
    };

    await injectNavItem(input);
    const result = await readFile(sidebarPath, "utf-8");

    // Should use location variable for active state
    expect(result).toContain('location === "/reports"');
  });

  it("Phase A idempotency: re-running with same href is a no-op", async () => {
    const input: NavInjectionInput = {
      sidebarPath,
      label: "Reports",
      href: "/reports",
      iconClass: "ri-bar-chart-line",
    };

    await injectNavItem(input);
    const after1 = await readFile(sidebarPath, "utf-8");
    await injectNavItem(input);
    const after2 = await readFile(sidebarPath, "utf-8");

    expect(after2).toBe(after1);
    const matches = after2.match(/href="\/reports"/g) ?? [];
    expect(matches.length).toBe(1);
  });

  it("preserves all existing nav items after injection", async () => {
    const input: NavInjectionInput = {
      sidebarPath,
      label: "Reports",
      href: "/reports",
      iconClass: "ri-bar-chart-line",
    };

    await injectNavItem(input);
    const result = await readFile(sidebarPath, "utf-8");

    // Original Dashboard nav item still present
    expect(result).toContain('href="/"');
    expect(result).toContain("<span>Dashboard</span>");
    // Original Task Board nav item still present
    expect(result).toContain('href="/tasks"');
    expect(result).toContain("<span>Task Board</span>");
  });
});
