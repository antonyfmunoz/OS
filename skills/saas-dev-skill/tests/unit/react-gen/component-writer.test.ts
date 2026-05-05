import { describe, it, expect, vi, beforeEach } from "vitest";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";

const TMP_REPO = fs.mkdtempSync(path.join(os.tmpdir(), "component-writer-test-"));

// ─── Mock Claude ─────────────────────────────────────────────────────────────

const mockStream = {
  finalMessage: vi.fn(),
};

vi.mock("@anthropic-ai/sdk", () => {
  return {
    default: class {
      messages = {
        stream: () => mockStream,
      };
    },
  };
});

vi.mock("../../../lib/env.js", () => ({
  getAnthropicApiKey: () => "sk-test",
  getAnthropicBaseUrl: () => "https://api.anthropic.com",
}));

// Mock child_process to avoid real tsc calls in tests
const mockExecSync = vi.fn();
vi.mock("node:child_process", () => ({
  execSync: (...args: unknown[]) => mockExecSync(...args),
}));

import {
  writeReactComponent,
  autoFixImports,
  validateImports,
  scanForNullUnsafePatterns,
  runTscCheck,
  type ComponentWriterInput,
} from "../../../lib/react-gen/component-writer.js";

function makeInput(overrides: Partial<ComponentWriterInput> = {}): ComponentWriterInput {
  return {
    page: {
      name: "Dashboard",
      route: "/dashboard",
      purpose: "Main dashboard",
      components: ["StatsCard", "RecentActivity"],
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
    },
    pageCopy: {
      pageName: "Dashboard",
      pageHeading: "Command Center",
      pageSubheading: "Your operational overview",
      sections: [],
      ctas: [{ id: "create-task", label: "Create Task", context: "header" }],
      emptyState: "No data yet. Start by creating your first task.",
      errorMessages: { fetch: "Failed to load dashboard data" },
      placeholders: {},
      helperText: {},
      successMessages: {},
      navLabel: "Dashboard",
    },
    designSystem: "# Design System\nMinimal and clean.",
    brandVoice: "Direct, commanding, operator-focused.",
    sharedComponentPaths: { UniversalLayout: "@/components/universal-layout" },
    projectBrief: {
      productName: "TestApp",
      productDescription: "A test app",
      productVision: "",
      targetUsers: ["developers"],
      jobsToBeDone: [],
      brandVoice: "",
      designSystem: "",
      techStack: { frontend: "react", buildTool: "vite", styling: "tailwind", componentLib: "shadcn/ui", language: "typescript" },
      authProvider: "firebase",
      dbProvider: "neon",
      deployTarget: "vps",
      spec: { pages: [], sharedComponents: [], suggestedOrder: [] },
      isGreenfield: true,
      existingCodeScanned: false,
      sourceDocs: [],
    },
    projectRoot: TMP_REPO,
    ...overrides,
  };
}

const VALID_COMPONENT = `import { useQuery } from "@tanstack/react-query";

export default function DashboardPage() {
  return <div>Dashboard</div>;
}`;

beforeEach(() => {
  vi.clearAllMocks();
  // Default: tsc passes clean
  mockExecSync.mockReturnValue("");
  // Default: generation returns valid component, review returns passing score
  mockStream.finalMessage
    .mockResolvedValueOnce({ content: [{ type: "text", text: VALID_COMPONENT }] })
    .mockResolvedValueOnce({ content: [{ type: "text", text: '{ "score": 0.9, "feedback": [] }' }] });
});

// ─── writeReactComponent integration tests ───────────────────────────────────

describe("writeReactComponent", () => {
  it("returns ComponentWriterOutput with correct shape including new fields", async () => {
    const result = await writeReactComponent(makeInput());

    expect(result.pageName).toBe("Dashboard");
    expect(result.filePath).toContain("dashboard-page.tsx");
    expect(result.componentCode).toContain("export default function");
    expect(typeof result.reviewScore).toBe("number");
    expect(Array.isArray(result.reviewFeedback)).toBe(true);
    expect(typeof result.passed).toBe("boolean");
    expect(typeof result.retried).toBe("boolean");
    // New fields
    expect(Array.isArray(result.tsErrors)).toBe(true);
    expect(typeof result.fixAttempts).toBe("number");
    expect(typeof result.compiledClean).toBe("boolean");
    expect(Array.isArray(result.importViolations)).toBe(true);
    expect(Array.isArray(result.nullSafetyIssues)).toBe(true);
  });

  it("writes file to correct path", async () => {
    const result = await writeReactComponent(makeInput());
    const expectedPath = path.join(TMP_REPO, "client", "src", "pages", "dashboard-page.tsx");
    expect(result.filePath).toBe(expectedPath);
    expect(fs.existsSync(expectedPath)).toBe(true);
  });

  it("validates against banned imports and retries", async () => {
    const BAD_COMPONENT = `import Link from "next/link";
export default function DashboardPage() { return <div />; }`;

    mockStream.finalMessage
      .mockReset()
      .mockResolvedValueOnce({ content: [{ type: "text", text: BAD_COMPONENT }] })
      // Retry generation
      .mockResolvedValueOnce({ content: [{ type: "text", text: VALID_COMPONENT }] })
      // Review
      .mockResolvedValueOnce({ content: [{ type: "text", text: '{ "score": 0.85, "feedback": [] }' }] });

    const result = await writeReactComponent(makeInput());
    expect(result.retried).toBe(true);
  });

  it("validates against gradient strings and retries", async () => {
    const GRADIENT_COMPONENT = `export default function DashboardPage() {
  return <div style={{ background: "linear-gradient(to right, #000, #fff)" }} />;
}`;

    mockStream.finalMessage
      .mockReset()
      .mockResolvedValueOnce({ content: [{ type: "text", text: GRADIENT_COMPONENT }] })
      .mockResolvedValueOnce({ content: [{ type: "text", text: VALID_COMPONENT }] })
      .mockResolvedValueOnce({ content: [{ type: "text", text: '{ "score": 0.9, "feedback": [] }' }] });

    const result = await writeReactComponent(makeInput());
    expect(result.retried).toBe(true);
  });

  it("retries on low review score", async () => {
    mockStream.finalMessage
      .mockReset()
      .mockResolvedValueOnce({ content: [{ type: "text", text: VALID_COMPONENT }] })
      .mockResolvedValueOnce({ content: [{ type: "text", text: '{ "score": 0.5, "feedback": ["Missing loading state"] }' }] })
      .mockResolvedValueOnce({ content: [{ type: "text", text: VALID_COMPONENT }] })
      .mockResolvedValueOnce({ content: [{ type: "text", text: '{ "score": 0.9, "feedback": [] }' }] });

    const result = await writeReactComponent(makeInput());
    expect(result.retried).toBe(true);
    expect(result.reviewScore).toBe(0.9);
  });

  it("marks as passed when score >= 0.8 and tsc clean", async () => {
    const result = await writeReactComponent(makeInput());
    expect(result.passed).toBe(true);
    expect(result.compiledClean).toBe(true);
    expect(result.reviewScore).toBe(0.9);
  });

  it("marks as failed when tsc has errors even if review passes", async () => {
    // tsc fails
    mockExecSync.mockImplementation(() => {
      const err = new Error("tsc failed") as Error & { stdout: string; stderr: string };
      err.stdout = "client/src/pages/dashboard-page.tsx(5,3): error TS2304: Cannot find name 'foo'.";
      err.stderr = "";
      throw err;
    });

    mockStream.finalMessage
      .mockReset()
      // Initial generation
      .mockResolvedValueOnce({ content: [{ type: "text", text: VALID_COMPONENT }] })
      // Review
      .mockResolvedValueOnce({ content: [{ type: "text", text: '{ "score": 0.9, "feedback": [] }' }] })
      // 3 fix attempts
      .mockResolvedValueOnce({ content: [{ type: "text", text: VALID_COMPONENT }] })
      .mockResolvedValueOnce({ content: [{ type: "text", text: VALID_COMPONENT }] })
      .mockResolvedValueOnce({ content: [{ type: "text", text: VALID_COMPONENT }] });

    const result = await writeReactComponent(makeInput());
    expect(result.passed).toBe(false);
    expect(result.compiledClean).toBe(false);
    expect(result.fixAttempts).toBe(3);
    expect(result.tsErrors.length).toBeGreaterThan(0);
  });

  it("fixes tsc errors within max attempts", async () => {
    let callCount = 0;
    mockExecSync.mockImplementation(() => {
      callCount++;
      if (callCount <= 1) {
        // First call fails
        const err = new Error("tsc failed") as Error & { stdout: string; stderr: string };
        err.stdout = "client/src/pages/dashboard-page.tsx(5,3): error TS2304: Cannot find name 'foo'.";
        err.stderr = "";
        throw err;
      }
      // Second call succeeds
      return "";
    });

    mockStream.finalMessage
      .mockReset()
      .mockResolvedValueOnce({ content: [{ type: "text", text: VALID_COMPONENT }] })
      .mockResolvedValueOnce({ content: [{ type: "text", text: '{ "score": 0.9, "feedback": [] }' }] })
      // One fix attempt
      .mockResolvedValueOnce({ content: [{ type: "text", text: VALID_COMPONENT }] });

    const result = await writeReactComponent(makeInput());
    expect(result.passed).toBe(true);
    expect(result.compiledClean).toBe(true);
    expect(result.fixAttempts).toBe(1);
  });

  it("auto-fixes firebase imports before validation", async () => {
    const FIREBASE_COMPONENT = `import { signInWithPopup } from "firebase/auth";

export default function DashboardPage() {
  return <div>Dashboard</div>;
}`;

    mockStream.finalMessage
      .mockReset()
      .mockResolvedValueOnce({ content: [{ type: "text", text: FIREBASE_COMPONENT }] })
      .mockResolvedValueOnce({ content: [{ type: "text", text: '{ "score": 0.9, "feedback": [] }' }] });

    const result = await writeReactComponent(makeInput());
    // Auto-fix should have handled it — check the written code doesn't contain firebase
    expect(result.componentCode).not.toContain("firebase/auth");
    expect(result.importViolations).toEqual([]);
  });
});

// ─── autoFixImports unit tests ───────────────────────────────────────────────

describe("autoFixImports", () => {
  it("replaces firebase/auth with @clerk/clerk-react", () => {
    const code = `import { signInWithPopup } from 'firebase/auth';`;
    const fixed = autoFixImports(code);
    expect(fixed).toContain("@clerk/clerk-react");
    expect(fixed).not.toContain("firebase/auth");
  });

  it("replaces next/link with wouter", () => {
    const code = `import Link from 'next/link';`;
    const fixed = autoFixImports(code);
    expect(fixed).toContain("wouter");
    expect(fixed).not.toContain("next/link");
  });

  it("replaces next/router with wouter", () => {
    const code = `import { useRouter } from 'next/router';`;
    const fixed = autoFixImports(code);
    expect(fixed).toContain("wouter");
    expect(fixed).not.toContain("next/router");
  });

  it("replaces posthog-js/react with posthog-js", () => {
    const code = `import { usePostHog } from 'posthog-js/react';`;
    const fixed = autoFixImports(code);
    expect(fixed).toContain("from 'posthog-js'");
    expect(fixed).not.toContain("posthog-js/react");
  });

  it("replaces react-router-dom with wouter", () => {
    const code = `import { BrowserRouter, Link } from 'react-router-dom';`;
    const fixed = autoFixImports(code);
    expect(fixed).toContain("wouter");
    expect(fixed).not.toContain("react-router-dom");
  });

  it("does not modify allowed imports", () => {
    const code = `import { useState } from 'react';
import { Button } from '@/components/ui/button';`;
    const fixed = autoFixImports(code);
    expect(fixed).toBe(code);
  });
});

// ─── validateImports unit tests ──────────────────────────────────────────────

describe("validateImports", () => {
  it("passes for all allowed imports", () => {
    const code = `import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'wouter';
import { useUser } from '@clerk/clerk-react';
import { ArrowRight } from 'lucide-react';`;
    const result = validateImports(code);
    expect(result.valid).toBe(true);
    expect(result.violations).toEqual([]);
  });

  it("flags forbidden imports", () => {
    const code = `import { signIn } from 'firebase/auth';
import { Box } from '@mui/material';`;
    const result = validateImports(code);
    expect(result.valid).toBe(false);
    expect(result.violations).toContain("firebase/auth");
    expect(result.violations).toContain("@mui/material");
  });

  it("allows relative imports", () => {
    const code = `import { helper } from './utils';
import { config } from '../config';`;
    const result = validateImports(code);
    expect(result.valid).toBe(true);
  });

  it("allows framer-motion, recharts, date-fns", () => {
    const code = `import { motion } from 'framer-motion';
import { LineChart } from 'recharts';
import { format } from 'date-fns';`;
    const result = validateImports(code);
    expect(result.valid).toBe(true);
  });

  it("flags unknown third-party imports", () => {
    const code = `import confetti from 'canvas-confetti';`;
    const result = validateImports(code);
    expect(result.valid).toBe(false);
    expect(result.violations).toContain("canvas-confetti");
  });
});

// ─── scanForNullUnsafePatterns unit tests ────────────────────────────────────

describe("scanForNullUnsafePatterns", () => {
  it("detects unguarded .map() calls", () => {
    const code = `const items = data;
items.map(x => x.name);`;
    const issues = scanForNullUnsafePatterns(code);
    expect(issues.length).toBeGreaterThan(0);
    expect(issues[0]).toContain(".map()");
  });

  it("detects unguarded .filter() calls", () => {
    const code = `const result = tasks.filter(t => t.done);`;
    const issues = scanForNullUnsafePatterns(code);
    expect(issues.length).toBeGreaterThan(0);
    expect(issues[0]).toContain(".filter()");
  });

  it("detects unguarded .reduce() calls", () => {
    const code = `const total = values.reduce((a, b) => a + b, 0);`;
    const issues = scanForNullUnsafePatterns(code);
    expect(issues.length).toBeGreaterThan(0);
    expect(issues[0]).toContain(".reduce()");
  });

  it("allows guarded patterns with nullish coalescing", () => {
    const code = `(items ?? []).map(x => x.name);`;
    const issues = scanForNullUnsafePatterns(code);
    expect(issues).toEqual([]);
  });

  it("allows safe prefixes like Object, Array, JSON", () => {
    const code = `Object.keys(data).map(k => k);
Array.from(set).filter(x => x);
JSON.stringify(data).length;`;
    const issues = scanForNullUnsafePatterns(code);
    expect(issues).toEqual([]);
  });

  it("skips import lines", () => {
    const code = `import { items } from './data';
// items.map is fine in imports`;
    const issues = scanForNullUnsafePatterns(code);
    expect(issues).toEqual([]);
  });

  it("detects unguarded .length access", () => {
    const code = `if (tasks.length > 0) { doSomething(); }`;
    const issues = scanForNullUnsafePatterns(code);
    expect(issues.length).toBeGreaterThan(0);
    expect(issues[0]).toContain(".length");
  });
});

// ─── runTscCheck unit tests ──────────────────────────────────────────────────

describe("runTscCheck", () => {
  it("returns clean when tsc succeeds", () => {
    mockExecSync.mockReturnValue("");
    const result = runTscCheck("/fake/root");
    expect(result.clean).toBe(true);
    expect(result.errors).toEqual([]);
  });

  it("returns errors when tsc fails", () => {
    mockExecSync.mockImplementation(() => {
      const err = new Error("tsc failed") as Error & { stdout: string; stderr: string };
      err.stdout = `client/src/pages/dashboard-page.tsx(5,3): error TS2304: Cannot find name 'foo'.
client/src/pages/dashboard-page.tsx(10,7): error TS2339: Property 'bar' does not exist.`;
      err.stderr = "";
      throw err;
    });
    const result = runTscCheck("/fake/root");
    expect(result.clean).toBe(false);
    expect(result.errors).toHaveLength(2);
    expect(result.errors[0]).toContain("error TS2304");
    expect(result.errors[1]).toContain("error TS2339");
  });
});
