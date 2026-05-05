import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

// ─── Mock all agent functions ───────────────────────────────────────────────

const mockRunProductIntelAgent = vi.fn();
const mockRunArchitectureAgent = vi.fn();
const mockRunDesignSystemAgent = vi.fn();
const mockRunCopyAgent = vi.fn();
const mockRunComponentLibraryAgent = vi.fn();
const mockRunPageAgent = vi.fn();
const mockRunBackendAgent = vi.fn();
const mockRunQAAgent = vi.fn();
const mockRunIntake = vi.fn();
const mockLoadProjectConfig = vi.fn();
const mockEnsureLivePreviewServer = vi.fn();
const mockInjectBuildOverlay = vi.fn();
const mockRemoveBuildOverlay = vi.fn();

vi.mock("../../../lib/agents/product-intel-agent.js", () => ({
  runProductIntelAgent: (...args: unknown[]) => mockRunProductIntelAgent(...args),
}));
vi.mock("../../../lib/agents/architecture-agent.js", () => ({
  runArchitectureAgent: (...args: unknown[]) => mockRunArchitectureAgent(...args),
}));
vi.mock("../../../lib/agents/design-system-agent.js", () => ({
  runDesignSystemAgent: (...args: unknown[]) => mockRunDesignSystemAgent(...args),
}));
vi.mock("../../../lib/agents/copy-agent.js", () => ({
  runCopyAgent: (...args: unknown[]) => mockRunCopyAgent(...args),
}));
vi.mock("../../../lib/agents/component-library-agent.js", () => ({
  runComponentLibraryAgent: (...args: unknown[]) => mockRunComponentLibraryAgent(...args),
}));
vi.mock("../../../lib/agents/page-agent.js", () => ({
  runPageAgent: (...args: unknown[]) => mockRunPageAgent(...args),
}));
vi.mock("../../../lib/agents/backend-agent.js", () => ({
  runBackendAgent: (...args: unknown[]) => mockRunBackendAgent(...args),
}));
vi.mock("../../../lib/agents/qa-agent.js", () => ({
  runQAAgent: (...args: unknown[]) => mockRunQAAgent(...args),
}));
vi.mock("../../../lib/intake/intake-orchestrator.js", () => ({
  runIntake: (...args: unknown[]) => mockRunIntake(...args),
}));
vi.mock("../../../lib/project-config.js", () => ({
  loadProjectConfig: (...args: unknown[]) => mockLoadProjectConfig(...args),
}));
vi.mock("../../../lib/react-gen/live-preview-server.js", () => ({
  ensureLivePreviewServer: (...args: unknown[]) => mockEnsureLivePreviewServer(...args),
}));
vi.mock("../../../lib/react-gen/build-status-overlay.js", () => ({
  injectBuildOverlay: (...args: unknown[]) => mockInjectBuildOverlay(...args),
  removeBuildOverlay: (...args: unknown[]) => mockRemoveBuildOverlay(...args),
}));
vi.mock("../../../lib/react-gen/edit-mode.js", () => ({
  editPage: vi.fn().mockResolvedValue({
    editApplied: true,
    compiledClean: true,
    fixAttempts: 0,
  }),
}));

const mockExecSync = vi.fn();
vi.mock("node:child_process", () => ({
  execSync: (...args: unknown[]) => mockExecSync(...args),
}));

// ─── Import under test ──────────────────────────────────────────────────────

import { PMOrchestrator } from "../../../lib/agents/pm-orchestrator.js";
import { ArtifactStore } from "../../../lib/agents/artifact-store.js";
import type { ProjectBrief } from "../../../lib/intake/types.js";
import type {
  ProductInsights,
  SystemArchitecture,
  DesignSystem,
  QAReport,
  PageOutput,
  BackendRoute,
} from "../../../lib/agents/types.js";
import type { ProjectCopy } from "../../../lib/copy-planner/types.js";

// ─── Helpers ────────────────────────────────────────────────────────────────

let tmpDir: string;

function makeBrief(pageCount = 2): ProjectBrief {
  const pages = Array.from({ length: pageCount }, (_, i) => ({
    name: `Page${i}`,
    route: `/page-${i}`,
    purpose: `Page ${i}`,
    components: [],
    authLevel: "authenticated" as const,
    priority: 1,
    dependsOn: [],
    specVersion: 1,
    source: "explicit" as const,
    dataRequirements: [],
    apiEndpoints: [],
    validationRules: [],
    events: [],
    featureFlagCandidates: [],
  }));

  return {
    productName: "TestApp",
    productDescription: "A test application",
    productVision: "",
    targetUsers: ["developers"],
    jobsToBeDone: [],
    brandVoice: "",
    designSystem: "",
    techStack: { frontend: "react", buildTool: "vite", styling: "tailwind", componentLib: "shadcn/ui", language: "typescript" },
    authProvider: "clerk",
    dbProvider: "neon",
    deployTarget: "vps",
    spec: { pages, sharedComponents: [], suggestedOrder: pages.map((p) => p.route) },
    isGreenfield: true,
    existingCodeScanned: false,
    sourceDocs: [],
  };
}

function makeInsights(): ProductInsights {
  return {
    productCategory: "saas",
    targetUserProfile: "developers",
    competitiveIntel: null,
    designRecommendations: [],
    copyRecommendations: [],
    architectureRecommendations: [],
    marketPositioning: "Developer tools",
  };
}

function makeArchitecture(): SystemArchitecture {
  return {
    dataModel: { entities: [], relationships: [], enums: [] },
    apiContracts: [],
    pages: [],
    componentHierarchy: [],
    userFlows: [],
  };
}

function makeDesignSystem(): DesignSystem {
  return {
    tokens: {
      colors: { primary: "#3b82f6" },
      typography: { fontFamily: "Inter", fontSizes: {}, fontWeights: {}, lineHeights: {} },
      spacing: {},
      borderRadius: {},
      shadows: {},
      breakpoints: {},
    },
    tailwindConfigPath: "tailwind.config.ts",
    cssCustomPropertiesPath: "client/src/styles/design-system.css",
    componentDesignGuidePath: ".planning/artifacts/COMPONENT_DESIGN_GUIDE.md",
    aesthetic: "Clean",
    colorMode: "light",
  };
}

function makeProjectCopy(): ProjectCopy {
  return {
    pages: [],
    generatedAt: new Date().toISOString(),
    brandVoiceHash: "abc",
  };
}

function makePageOutput(name: string): PageOutput {
  return {
    pageName: name,
    filePath: `client/src/pages/${name.toLowerCase()}-page.tsx`,
    route: `/${name.toLowerCase()}`,
    componentCode: `export default function ${name}Page() { return <div />; }`,
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

function makeQAReport(allPassed = true): QAReport {
  return {
    allPassed,
    totalIssues: allPassed ? 0 : 3,
    issuesFixed: 0,
    remainingIssues: allPassed ? [] : [{ file: "test.tsx", severity: "error", category: "typescript", message: "TS error", autoFixed: false }],
    iterations: allPassed ? 0 : 3,
    tscClean: allPassed,
    pageResults: [],
  };
}

function setupDefaultMocks(): void {
  mockEnsureLivePreviewServer.mockResolvedValue({ port: 5173, close: vi.fn() });
  mockInjectBuildOverlay.mockResolvedValue(undefined);
  mockRemoveBuildOverlay.mockResolvedValue(undefined);

  mockRunProductIntelAgent.mockResolvedValue(makeInsights());
  mockRunArchitectureAgent.mockResolvedValue(makeArchitecture());
  mockRunDesignSystemAgent.mockResolvedValue(makeDesignSystem());
  mockRunCopyAgent.mockResolvedValue(makeProjectCopy());
  mockRunComponentLibraryAgent.mockResolvedValue({ Button: "@/components/ui/button" });
  mockRunPageAgent.mockImplementation(async (pageSpec: { name: string }) => makePageOutput(pageSpec.name));
  mockRunBackendAgent.mockResolvedValue([]);
  mockRunQAAgent.mockResolvedValue(makeQAReport());

  // Pre-flight: tsc passes by default
  mockExecSync.mockReturnValue(Buffer.from(""));
}

function setupEnvForPreflight(): void {
  process.env.DATABASE_URL = "postgresql://test:test@localhost:5432/test";
  process.env.ANTHROPIC_API_KEY = "sk-test-key";
}

// ─── Setup / Teardown ───────────────────────────────────────────────────────

let savedEnv: Record<string, string | undefined>;

beforeEach(() => {
  tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "pm-orchestrator-test-"));
  vi.clearAllMocks();
  // Suppress console.log during tests
  vi.spyOn(console, "log").mockImplementation(() => {});
  // Prevent Windows EINVAL from colons in filenames (agent names like "page:Page0")
  vi.spyOn(ArtifactStore.prototype, "setAgentResult").mockImplementation(() => {});
  // Save env state
  savedEnv = { DATABASE_URL: process.env.DATABASE_URL, ANTHROPIC_API_KEY: process.env.ANTHROPIC_API_KEY, AI_INTEGRATIONS_ANTHROPIC_API_KEY: process.env.AI_INTEGRATIONS_ANTHROPIC_API_KEY };
  setupDefaultMocks();
  setupEnvForPreflight();
});

afterEach(() => {
  fs.rmSync(tmpDir, { recursive: true, force: true });
  // Restore env state
  for (const [key, val] of Object.entries(savedEnv)) {
    if (val === undefined) delete process.env[key];
    else process.env[key] = val;
  }
  vi.restoreAllMocks();
});

// ─── Tests ──────────────────────────────────────────────────────────────────

describe("PMOrchestrator", () => {
  describe("runBuild", () => {
    it("executes agents in correct wave order", async () => {
      const callOrder: string[] = [];
      mockRunProductIntelAgent.mockImplementation(async () => {
        callOrder.push("product-intel");
        return makeInsights();
      });
      mockRunArchitectureAgent.mockImplementation(async () => {
        callOrder.push("architecture");
        return makeArchitecture();
      });
      mockRunDesignSystemAgent.mockImplementation(async () => {
        callOrder.push("design-system");
        return makeDesignSystem();
      });
      mockRunCopyAgent.mockImplementation(async () => {
        callOrder.push("copy");
        return makeProjectCopy();
      });
      mockRunComponentLibraryAgent.mockImplementation(async () => {
        callOrder.push("component-library");
        return {};
      });
      mockRunPageAgent.mockImplementation(async (pageSpec: { name: string }) => {
        callOrder.push(`page-${pageSpec.name}`);
        return makePageOutput(pageSpec.name);
      });
      mockRunBackendAgent.mockImplementation(async () => {
        callOrder.push("backend");
        return [];
      });
      mockRunQAAgent.mockImplementation(async () => {
        callOrder.push("qa");
        return makeQAReport();
      });

      const orchestrator = new PMOrchestrator(tmpDir);
      await orchestrator.runBuild(makeBrief());

      // Wave 1: product-intel runs first
      const intelIdx = callOrder.indexOf("product-intel");
      expect(intelIdx).toBe(0);

      // Wave 2: architecture and design-system run after product-intel
      const archIdx = callOrder.indexOf("architecture");
      const dsIdx = callOrder.indexOf("design-system");
      expect(archIdx).toBeGreaterThan(intelIdx);
      expect(dsIdx).toBeGreaterThan(intelIdx);

      // Wave 3: copy and component-library run after wave 2
      const copyIdx = callOrder.indexOf("copy");
      const compIdx = callOrder.indexOf("component-library");
      expect(copyIdx).toBeGreaterThan(Math.max(archIdx, dsIdx));
      expect(compIdx).toBeGreaterThan(Math.max(archIdx, dsIdx));

      // Wave 4: pages and backend run after wave 3
      const page0Idx = callOrder.indexOf("page-Page0");
      const backendIdx = callOrder.indexOf("backend");
      expect(page0Idx).toBeGreaterThan(Math.max(copyIdx, compIdx));
      expect(backendIdx).toBeGreaterThan(Math.max(copyIdx, compIdx));

      // Wave 5: QA runs last
      const qaIdx = callOrder.indexOf("qa");
      expect(qaIdx).toBe(callOrder.length - 1);
    });

    it("runs parallel agents concurrently within each wave", async () => {
      let maxConcurrentWave2 = 0;
      let currentConcurrentWave2 = 0;

      mockRunArchitectureAgent.mockImplementation(async () => {
        currentConcurrentWave2++;
        maxConcurrentWave2 = Math.max(maxConcurrentWave2, currentConcurrentWave2);
        await new Promise((r) => setTimeout(r, 50));
        currentConcurrentWave2--;
        return makeArchitecture();
      });
      mockRunDesignSystemAgent.mockImplementation(async () => {
        currentConcurrentWave2++;
        maxConcurrentWave2 = Math.max(maxConcurrentWave2, currentConcurrentWave2);
        await new Promise((r) => setTimeout(r, 50));
        currentConcurrentWave2--;
        return makeDesignSystem();
      });

      const orchestrator = new PMOrchestrator(tmpDir);
      await orchestrator.runBuild(makeBrief());

      // Both should have been running concurrently
      expect(maxConcurrentWave2).toBe(2);
    });

    it("updates build state after each wave", async () => {
      const orchestrator = new PMOrchestrator(tmpDir);
      await orchestrator.runBuild(makeBrief());

      const status = orchestrator.getStatus();
      expect(status).not.toBeNull();
      expect(status!.checkpoints.length).toBeGreaterThan(0);
      // Should have checkpoints for product-intel, architecture, component-library, pages, qa
      const phases = status!.checkpoints.map((c) => c.phase);
      expect(phases).toContain("product-intel");
      expect(phases).toContain("architecture");
      expect(phases).toContain("pages");
      expect(phases).toContain("qa");
    });

    it("QA agent runs last", async () => {
      const callOrder: string[] = [];
      mockRunQAAgent.mockImplementation(async () => {
        callOrder.push("qa");
        return makeQAReport();
      });
      mockRunPageAgent.mockImplementation(async (pageSpec: { name: string }) => {
        callOrder.push(`page-${pageSpec.name}`);
        return makePageOutput(pageSpec.name);
      });
      mockRunBackendAgent.mockImplementation(async () => {
        callOrder.push("backend");
        return [];
      });

      const orchestrator = new PMOrchestrator(tmpDir);
      await orchestrator.runBuild(makeBrief());

      const qaIdx = callOrder.indexOf("qa");
      expect(qaIdx).toBe(callOrder.length - 1);
    });

    it("returns success when all agents pass and QA is clean", async () => {
      const orchestrator = new PMOrchestrator(tmpDir);
      const result = await orchestrator.runBuild(makeBrief());

      expect(result.success).toBe(true);
      expect(result.errors).toEqual([]);
      expect(result.qaReport).not.toBeNull();
      expect(result.qaReport!.allPassed).toBe(true);
      expect(result.pagesBuilt).toBe(2);
    });

    it("aborts build when architecture agent fails (critical agent)", async () => {
      mockRunArchitectureAgent.mockRejectedValue(new Error("Architecture generation failed"));

      const orchestrator = new PMOrchestrator(tmpDir);
      const result = await orchestrator.runBuild(makeBrief());

      expect(result.success).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
      expect(result.errors.some((e) => e.toLowerCase().includes("architecture"))).toBe(true);

      // Page agent and QA should NOT have been called
      expect(mockRunPageAgent).not.toHaveBeenCalled();
      expect(mockRunQAAgent).not.toHaveBeenCalled();
    });

    it("aborts build when design-system agent fails (critical agent)", async () => {
      mockRunDesignSystemAgent.mockRejectedValue(new Error("Design system generation failed"));

      const orchestrator = new PMOrchestrator(tmpDir);
      const result = await orchestrator.runBuild(makeBrief());

      expect(result.success).toBe(false);
      expect(result.errors.some((e) => e.toLowerCase().includes("design system"))).toBe(true);

      // Later agents should NOT have been called
      expect(mockRunPageAgent).not.toHaveBeenCalled();
    });

    it("continues when product-intel agent fails (non-critical)", async () => {
      mockRunProductIntelAgent.mockRejectedValue(new Error("Intel failed"));

      const orchestrator = new PMOrchestrator(tmpDir);
      const result = await orchestrator.runBuild(makeBrief());

      // Should still succeed because product-intel is non-critical
      expect(result.success).toBe(true);
      expect(mockRunArchitectureAgent).toHaveBeenCalled();
      expect(mockRunPageAgent).toHaveBeenCalled();
    });

    it("continues when copy agent fails (non-critical)", async () => {
      mockRunCopyAgent.mockRejectedValue(new Error("Copy failed"));

      const orchestrator = new PMOrchestrator(tmpDir);
      const result = await orchestrator.runBuild(makeBrief());

      expect(result.success).toBe(true);
      expect(mockRunPageAgent).toHaveBeenCalled();
    });

    it("reports failed pages in errors but still runs QA", async () => {
      mockRunPageAgent.mockRejectedValue(new Error("Page generation failed"));

      const orchestrator = new PMOrchestrator(tmpDir);
      const result = await orchestrator.runBuild(makeBrief());

      // Pages failed, so errors should be reported
      expect(result.errors.length).toBeGreaterThan(0);
      // QA should still run
      expect(mockRunQAAgent).toHaveBeenCalled();
    });

    it("reports QA failures as BUILD FAILED with specific issues", async () => {
      mockRunQAAgent.mockResolvedValue(makeQAReport(false));

      const orchestrator = new PMOrchestrator(tmpDir);
      const result = await orchestrator.runBuild(makeBrief());

      expect(result.success).toBe(false);
      expect(result.qaReport).not.toBeNull();
      expect(result.qaReport!.allPassed).toBe(false);
      expect(result.errors.some((e) => e.includes("BUILD FAILED"))).toBe(true);
      expect(result.errors.some((e) => e.includes("QA did not pass"))).toBe(true);
    });

    it("persists build state to artifact store", async () => {
      const orchestrator = new PMOrchestrator(tmpDir);
      await orchestrator.runBuild(makeBrief());

      // Check that build state was written
      const artifactsDir = path.join(tmpDir, ".planning", "artifacts");
      const buildStatePath = path.join(artifactsDir, "build-state.json");
      expect(fs.existsSync(buildStatePath)).toBe(true);

      const buildStatusPath = path.join(artifactsDir, "build-status.json");
      expect(fs.existsSync(buildStatusPath)).toBe(true);
    });
  });

  describe("runIntake", () => {
    it("runs intake phase and persists brief", async () => {
      const brief = makeBrief();
      mockLoadProjectConfig.mockReturnValue({ projectId: "test", projectRoot: tmpDir });
      mockRunIntake.mockResolvedValue({ brief, mode: "greenfield" });

      const orchestrator = new PMOrchestrator(tmpDir);
      const result = await orchestrator.runIntake();

      expect(result.productName).toBe("TestApp");
      expect(mockRunIntake).toHaveBeenCalledTimes(1);
    });
  });

  describe("getStatus", () => {
    it("returns null before build starts", () => {
      const orchestrator = new PMOrchestrator(tmpDir);
      expect(orchestrator.getStatus()).toBeNull();
    });

    it("returns build state after build completes", async () => {
      const orchestrator = new PMOrchestrator(tmpDir);
      await orchestrator.runBuild(makeBrief());

      const status = orchestrator.getStatus();
      expect(status).not.toBeNull();
      expect(status!.brief).not.toBeNull();
      expect(status!.status.phase).toBe("complete");
    });

    it("returns failed status after critical failure", async () => {
      mockRunArchitectureAgent.mockRejectedValue(new Error("fail"));

      const orchestrator = new PMOrchestrator(tmpDir);
      await orchestrator.runBuild(makeBrief());

      const status = orchestrator.getStatus();
      expect(status).not.toBeNull();
      expect(status!.status.phase).toBe("failed");
    });
  });

  describe("preFlightCheck", () => {
    it("passes when all env vars and tsc are clean", () => {
      const orchestrator = new PMOrchestrator(tmpDir);
      const result = orchestrator.preFlightCheck();

      expect(result.passed).toBe(true);
      expect(result.checks.every((c) => c.passed)).toBe(true);
    });

    it("fails when DATABASE_URL is missing", () => {
      delete process.env.DATABASE_URL;

      const orchestrator = new PMOrchestrator(tmpDir);
      const result = orchestrator.preFlightCheck();

      expect(result.passed).toBe(false);
      const dbCheck = result.checks.find((c) => c.name === "env:DATABASE_URL");
      expect(dbCheck?.passed).toBe(false);
    });

    it("fails when no Anthropic API key is set", () => {
      delete process.env.ANTHROPIC_API_KEY;
      delete process.env.AI_INTEGRATIONS_ANTHROPIC_API_KEY;

      const orchestrator = new PMOrchestrator(tmpDir);
      const result = orchestrator.preFlightCheck();

      expect(result.passed).toBe(false);
      const apiCheck = result.checks.find((c) => c.name === "env:ANTHROPIC_API_KEY");
      expect(apiCheck?.passed).toBe(false);
    });

    it("fails when tsc has errors", () => {
      const err = new Error("tsc failed") as Error & { stderr: string };
      err.stderr = "error TS2304: Cannot find name\nerror TS2345: Type mismatch";
      mockExecSync.mockImplementation(() => { throw err; });

      const orchestrator = new PMOrchestrator(tmpDir);
      const result = orchestrator.preFlightCheck();

      expect(result.passed).toBe(false);
      const tscCheck = result.checks.find((c) => c.name === "tsc:noEmit");
      expect(tscCheck?.passed).toBe(false);
      expect(tscCheck?.message).toContain("error");
    });

    it("stops build immediately when preflight fails", async () => {
      delete process.env.DATABASE_URL;

      const orchestrator = new PMOrchestrator(tmpDir);
      const result = await orchestrator.runBuild(makeBrief());

      expect(result.success).toBe(false);
      expect(result.errors.some((e) => e.includes("Pre-flight check failed"))).toBe(true);
      // No agents should have been called
      expect(mockRunProductIntelAgent).not.toHaveBeenCalled();
      expect(mockRunArchitectureAgent).not.toHaveBeenCalled();
    });
  });
});
