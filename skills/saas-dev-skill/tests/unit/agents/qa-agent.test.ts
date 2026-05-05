import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

// ─── Mock dependencies ──────────────────────────────────────────────────────

const mockRunTscCheck = vi.fn();
const mockValidateImports = vi.fn();
const mockScanForNullUnsafePatterns = vi.fn();
const mockAutoFixImports = vi.fn();

vi.mock("../../../lib/react-gen/component-writer.js", () => ({
  runTscCheck: (...args: unknown[]) => mockRunTscCheck(...args),
  validateImports: (...args: unknown[]) => mockValidateImports(...args),
  scanForNullUnsafePatterns: (...args: unknown[]) => mockScanForNullUnsafePatterns(...args),
  autoFixImports: (...args: unknown[]) => mockAutoFixImports(...args),
}));

const mockStream = {
  finalMessage: vi.fn(),
};

vi.mock("@anthropic-ai/sdk", () => ({
  default: class MockAnthropic {
    messages = {
      stream: vi.fn().mockReturnValue(mockStream),
    };
  },
}));

vi.mock("../../../lib/env.js", () => ({
  getAnthropicApiKey: () => "sk-test",
  getAnthropicBaseUrl: () => "https://api.anthropic.com",
}));

// ─── Import under test ──────────────────────────────────────────────────────

import { runQAAgent } from "../../../lib/agents/qa-agent.js";
import { ArtifactStore } from "../../../lib/agents/artifact-store.js";
import type { PageOutput } from "../../../lib/agents/types.js";

// ─── Helpers ────────────────────────────────────────────────────────────────

let tmpDir: string;
let store: ArtifactStore;

function makePageOutput(name = "Dashboard"): PageOutput {
  return {
    pageName: name,
    filePath: `client/src/pages/${name.toLowerCase()}-page.tsx`,
    route: `/${name.toLowerCase()}`,
    componentCode: `import { useQuery } from "@tanstack/react-query";
export default function ${name}Page() {
  const { data, isLoading, error } = useQuery({ queryKey: ["/api/${name.toLowerCase()}"] });
  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: retry</div>;
  if (!data) return <div>No ${name.toLowerCase()} found. empty state</div>;
  return <div>${name}</div>;
}`,
    reviewScore: 0.9,
    reviewFeedback: [],
    passed: true,
    tsErrors: [],
    fixAttempts: 0,
    compiledClean: true,
    importViolations: [],
    nullSafetyIssues: [],
  };
}

function setupPageFile(page: PageOutput): void {
  const fullPath = path.join(tmpDir, page.filePath);
  const dir = path.dirname(fullPath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  fs.writeFileSync(fullPath, page.componentCode, "utf-8");
}

// ─── Setup / Teardown ───────────────────────────────────────────────────────

beforeEach(() => {
  tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "qa-agent-test-"));
  store = new ArtifactStore(tmpDir);
  vi.clearAllMocks();

  // Defaults: everything passes
  mockRunTscCheck.mockReturnValue({ clean: true, errors: [] });
  mockValidateImports.mockReturnValue({ valid: true, violations: [] });
  mockScanForNullUnsafePatterns.mockReturnValue([]);
  mockAutoFixImports.mockImplementation((code: string) => code);

  // Default mock for auto-fix Claude call
  mockStream.finalMessage.mockResolvedValue({
    content: [{ type: "text", text: "export default function Fixed() { return <div>Fixed</div>; }" }],
  });
});

afterEach(() => {
  fs.rmSync(tmpDir, { recursive: true, force: true });
});

// ─── Tests ──────────────────────────────────────────────────────────────────

describe("runQAAgent", () => {
  it("runs full validation pipeline on all page outputs", async () => {
    const page = makePageOutput("Dashboard");
    store.setPageOutputs([page]);
    setupPageFile(page);

    const report = await runQAAgent(store);

    expect(mockRunTscCheck).toHaveBeenCalled();
    expect(mockValidateImports).toHaveBeenCalledTimes(1);
    expect(mockScanForNullUnsafePatterns).toHaveBeenCalledTimes(1);

    expect(report.allPassed).toBe(true);
    expect(report.tscClean).toBe(true);
    expect(report.totalIssues).toBe(0);
    expect(report.remainingIssues).toEqual([]);
  });

  it("detects import violations and includes them in report", async () => {
    const page = makePageOutput("Dashboard");
    store.setPageOutputs([page]);
    setupPageFile(page);

    mockValidateImports.mockReturnValue({
      valid: false,
      violations: ["firebase/auth"],
    });

    // Auto-fix resolves it on first iteration
    mockRunTscCheck
      .mockReturnValueOnce({ clean: true, errors: [] })
      .mockReturnValue({ clean: true, errors: [] });

    const report = await runQAAgent(store);

    expect(report.totalIssues).toBeGreaterThan(0);
    const importIssues = report.pageResults[0].issues.filter((i) => i.category === "import");
    expect(importIssues.length).toBeGreaterThan(0);
    expect(importIssues[0].message).toContain("firebase/auth");
  });

  it("detects null-safety issues", async () => {
    const page = makePageOutput("Dashboard");
    store.setPageOutputs([page]);
    setupPageFile(page);

    mockScanForNullUnsafePatterns.mockReturnValue([
      "Line 5: Unguarded .map() call on tasks",
    ]);

    const report = await runQAAgent(store);

    expect(report.totalIssues).toBeGreaterThan(0);
    const nullIssues = report.pageResults[0].issues.filter((i) => i.category === "null-safety");
    expect(nullIssues.length).toBeGreaterThan(0);
  });

  it("detects TypeScript errors from tsc", async () => {
    const page = makePageOutput("Dashboard");
    store.setPageOutputs([page]);
    setupPageFile(page);

    mockRunTscCheck.mockReturnValue({
      clean: false,
      errors: [
        `client/src/pages/dashboard-page.tsx(5,3): error TS2304: Cannot find name 'foo'.`,
      ],
    });

    const report = await runQAAgent(store);

    expect(report.tscClean).toBe(false);
    expect(report.totalIssues).toBeGreaterThan(0);
  });

  it("auto-fix loop retries up to 3 times", async () => {
    const page = makePageOutput("Dashboard");
    store.setPageOutputs([page]);
    setupPageFile(page);

    // Each tsc call returns a different new error so the loop doesn't
    // short-circuit on "already tracked + autoFixed" issues.
    let tscCallCount = 0;
    mockRunTscCheck.mockImplementation(() => {
      tscCallCount++;
      return {
        clean: false,
        errors: [
          `client/src/pages/dashboard-page.tsx(${tscCallCount * 10},3): error TS2304: Cannot find name 'err${tscCallCount}'.`,
        ],
      };
    });

    const report = await runQAAgent(store);

    expect(report.iterations).toBe(3);
    expect(report.allPassed).toBe(false);
    expect(report.tscClean).toBe(false);
  });

  it("stops auto-fix loop early when tsc becomes clean", async () => {
    const page = makePageOutput("Dashboard");
    store.setPageOutputs([page]);
    setupPageFile(page);

    // First tsc fails, second succeeds
    mockRunTscCheck
      .mockReturnValueOnce({
        clean: false,
        errors: [
          `client/src/pages/dashboard-page.tsx(5,3): error TS2304: Cannot find name 'foo'.`,
        ],
      })
      .mockReturnValue({ clean: true, errors: [] });

    const report = await runQAAgent(store);

    expect(report.iterations).toBe(1);
    expect(report.tscClean).toBe(true);
  });

  it("writes QAReport to ArtifactStore", async () => {
    const page = makePageOutput("Dashboard");
    store.setPageOutputs([page]);
    setupPageFile(page);

    expect(store.getQAReport()).toBeNull();

    await runQAAgent(store);

    const stored = store.getQAReport();
    expect(stored).not.toBeNull();
    expect(stored!.allPassed).toBe(true);
  });

  it("handles multiple pages with mixed results", async () => {
    const dashboard = makePageOutput("Dashboard");
    const settings = makePageOutput("Settings");
    store.setPageOutputs([dashboard, settings]);
    setupPageFile(dashboard);
    setupPageFile(settings);

    // First page OK, second page has import violation
    let callCount = 0;
    mockValidateImports.mockImplementation(() => {
      callCount++;
      if (callCount === 2) {
        return { valid: false, violations: ["@mui/material"] };
      }
      return { valid: true, violations: [] };
    });

    const report = await runQAAgent(store);

    expect(report.pageResults).toHaveLength(2);
    // Dashboard should pass (no import violations)
    // Settings should have issues
    const settingsResult = report.pageResults.find((r) => r.pageName === "Settings");
    expect(settingsResult).toBeDefined();
    expect(settingsResult!.issues.length).toBeGreaterThan(0);
  });

  it("handles empty page outputs gracefully", async () => {
    store.setPageOutputs([]);

    const report = await runQAAgent(store);

    expect(report.pageResults).toEqual([]);
    expect(report.totalIssues).toBe(0);
  });

  it("handles missing page files gracefully", async () => {
    const page = makePageOutput("Dashboard");
    store.setPageOutputs([page]);
    // Intentionally do NOT create the file on disk

    const report = await runQAAgent(store);

    // Should not throw — just skip the page
    expect(report).toBeDefined();
  });
});
