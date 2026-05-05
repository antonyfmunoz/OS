import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

// ─── Mock writeReactComponent ───────────────────────────────────────────────

const mockWriteReactComponent = vi.fn();

vi.mock("../../../lib/react-gen/component-writer.js", () => ({
  writeReactComponent: (...args: unknown[]) => mockWriteReactComponent(...args),
}));

// ─── Import under test ──────────────────────────────────────────────────────

import { runPageAgent } from "../../../lib/agents/page-agent.js";
import { ArtifactStore } from "../../../lib/agents/artifact-store.js";
import type { PageOutput, DesignSystem, ComponentInterface } from "../../../lib/agents/types.js";
import type { ProjectBrief } from "../../../lib/intake/types.js";
import type { PageSpecFull } from "@shared/spec-schema.js";
import type { ProjectCopy } from "../../../lib/copy-planner/types.js";

// ─── Helpers ────────────────────────────────────────────────────────────────

let tmpDir: string;
let store: ArtifactStore;

function makeBrief(): ProjectBrief {
  return {
    productName: "TestApp",
    productDescription: "A test application",
    productVision: "",
    targetUsers: ["developers"],
    jobsToBeDone: [],
    brandVoice: "Bold and direct.",
    designSystem: "# Fallback Design System\nMinimal.",
    techStack: { frontend: "react", buildTool: "vite", styling: "tailwind", componentLib: "shadcn/ui", language: "typescript" },
    authProvider: "clerk",
    dbProvider: "neon",
    deployTarget: "vps",
    spec: { pages: [], sharedComponents: [], suggestedOrder: [] },
    isGreenfield: true,
    existingCodeScanned: false,
    sourceDocs: [],
  };
}

function makePageSpec(name = "Dashboard"): PageSpecFull {
  return {
    name,
    route: `/${name.toLowerCase()}`,
    purpose: `${name} page`,
    components: ["Sidebar"],
    authLevel: "authenticated",
    priority: 1,
    dependsOn: [],
    specVersion: 1,
    source: "explicit" as const,
    dataRequirements: [],
    apiEndpoints: [],
    validationRules: [],
    events: [],
    featureFlagCandidates: [],
  };
}

function makeWriterOutput(pageName = "Dashboard"): {
  pageName: string;
  filePath: string;
  componentCode: string;
  reviewScore: number;
  reviewFeedback: string[];
  passed: boolean;
  retried: boolean;
  tsErrors: string[];
  fixAttempts: number;
  compiledClean: boolean;
  importViolations: string[];
  nullSafetyIssues: string[];
} {
  return {
    pageName,
    filePath: path.join(tmpDir, "client", "src", "pages", `${pageName.toLowerCase()}-page.tsx`),
    componentCode: `export default function ${pageName}Page() { return <div>${pageName}</div>; }`,
    reviewScore: 0.9,
    reviewFeedback: [],
    passed: true,
    retried: false,
    tsErrors: [],
    fixAttempts: 0,
    compiledClean: true,
    importViolations: [],
    nullSafetyIssues: [],
  };
}

function makeDesignSystem(): DesignSystem {
  return {
    tokens: {
      colors: { primary: "#3b82f6" },
      typography: { fontFamily: "Inter", fontSizes: { base: "1rem" }, fontWeights: { normal: 400 }, lineHeights: { normal: "1.5" } },
      spacing: { "1": "0.25rem" },
      borderRadius: { md: "0.375rem" },
      shadows: { sm: "0 1px 2px rgba(0,0,0,0.05)" },
      breakpoints: { sm: "640px" },
    },
    tailwindConfigPath: "tailwind.config.ts",
    cssCustomPropertiesPath: "client/src/styles/design-system.css",
    componentDesignGuidePath: ".planning/artifacts/COMPONENT_DESIGN_GUIDE.md",
    aesthetic: "Clean and minimal",
    colorMode: "light",
  };
}

function makeProjectCopy(): ProjectCopy {
  return {
    pages: [
      {
        pageName: "Dashboard",
        pageHeading: "Command Center",
        pageSubheading: "Your overview",
        sections: [],
        ctas: [{ id: "cta-1", label: "Go", context: "header" }],
        emptyState: "No data",
        errorMessages: { fetch: "Failed" },
        placeholders: {},
        helperText: {},
        successMessages: {},
        navLabel: "Dashboard",
      },
    ],
    generatedAt: new Date().toISOString(),
    brandVoiceHash: "abc123",
  };
}

// ─── Setup / Teardown ───────────────────────────────────────────────────────

beforeEach(() => {
  tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "page-agent-test-"));
  store = new ArtifactStore(tmpDir);
  vi.clearAllMocks();

  mockWriteReactComponent.mockResolvedValue(makeWriterOutput());
});

afterEach(() => {
  fs.rmSync(tmpDir, { recursive: true, force: true });
});

// ─── Tests ──────────────────────────────────────────────────────────────────

describe("runPageAgent", () => {
  it("reads all context from ArtifactStore", async () => {
    // Set up store with all context artifacts
    const ds = makeDesignSystem();
    store.setDesignSystem(ds);
    store.writeProjectFile(
      ".planning/artifacts/COMPONENT_DESIGN_GUIDE.md",
      "# Component Guide\nUse bg-primary for buttons.",
    );
    store.setComponentPaths({ Sidebar: "@/components/sidebar" });
    store.setComponentInterfaces([
      { name: "Sidebar", filePath: "client/src/components/sidebar.tsx", exportName: "Sidebar", props: [{ name: "collapsed", type: "boolean", optional: true }], dependsOn: [] },
    ]);
    store.setProjectCopy(makeProjectCopy());

    await runPageAgent(makePageSpec(), makeBrief(), store);

    // Verify writeReactComponent was called with enriched context
    expect(mockWriteReactComponent).toHaveBeenCalledTimes(1);
    const input = mockWriteReactComponent.mock.calls[0][0];

    // Should have loaded design guide from file
    expect(input.designSystem).toContain("Component Guide");
    // Should include component interfaces
    expect(input.designSystem).toContain("AVAILABLE SHARED COMPONENT INTERFACES");
    expect(input.designSystem).toContain("Sidebar");
    // Should have component paths
    expect(input.sharedComponentPaths).toEqual({ Sidebar: "@/components/sidebar" });
    // Should have page copy
    expect(input.pageCopy).not.toBeNull();
    expect(input.pageCopy.pageName).toBe("Dashboard");
  });

  it("passes correct ComponentWriterInput to writeReactComponent", async () => {
    await runPageAgent(makePageSpec("Settings"), makeBrief(), store);

    expect(mockWriteReactComponent).toHaveBeenCalledTimes(1);
    const input = mockWriteReactComponent.mock.calls[0][0];

    expect(input.page.name).toBe("Settings");
    expect(input.page.route).toBe("/settings");
    expect(input.brandVoice).toBe("Bold and direct.");
    expect(input.projectBrief.productName).toBe("TestApp");
    expect(input.projectRoot).toBe(store.getProjectRoot());
  });

  it("writes PageOutput to ArtifactStore", async () => {
    expect(store.getPageOutputs()).toBeNull();

    await runPageAgent(makePageSpec(), makeBrief(), store);

    const outputs = store.getPageOutputs();
    expect(outputs).not.toBeNull();
    expect(outputs).toHaveLength(1);
    expect(outputs![0].pageName).toBe("Dashboard");
    expect(outputs![0].route).toBe("/dashboard");
    expect(outputs![0].passed).toBe(true);
  });

  it("returns PageOutput with correct shape", async () => {
    const result = await runPageAgent(makePageSpec(), makeBrief(), store);

    expect(result.pageName).toBe("Dashboard");
    expect(result.route).toBe("/dashboard");
    expect(result.componentCode).toContain("Dashboard");
    expect(result.reviewScore).toBe(0.9);
    expect(result.passed).toBe(true);
    expect(result.compiledClean).toBe(true);
    expect(Array.isArray(result.tsErrors)).toBe(true);
    expect(Array.isArray(result.importViolations)).toBe(true);
    expect(Array.isArray(result.nullSafetyIssues)).toBe(true);
  });

  it("falls back to brief.designSystem when no design system artifact exists", async () => {
    await runPageAgent(makePageSpec(), makeBrief(), store);

    const input = mockWriteReactComponent.mock.calls[0][0];
    expect(input.designSystem).toContain("Fallback Design System");
  });

  it("passes pageCopy as null when no project copy matches the page", async () => {
    // Set project copy for a different page
    const copy = makeProjectCopy();
    copy.pages[0].pageName = "Settings";
    store.setProjectCopy(copy);

    await runPageAgent(makePageSpec("Dashboard"), makeBrief(), store);

    const input = mockWriteReactComponent.mock.calls[0][0];
    expect(input.pageCopy).toBeNull();
  });

  it("passes priorPageSummary when provided", async () => {
    const prior = 'Prior page "Login" at route /login scored 0.85/10.';
    await runPageAgent(makePageSpec(), makeBrief(), store, prior);

    const input = mockWriteReactComponent.mock.calls[0][0];
    expect(input.priorPageSummary).toBe(prior);
  });

  it("handles empty component paths and interfaces", async () => {
    await runPageAgent(makePageSpec(), makeBrief(), store);

    const input = mockWriteReactComponent.mock.calls[0][0];
    expect(input.sharedComponentPaths).toEqual({});
  });
});
