import { describe, it, expect, vi, beforeEach } from "vitest";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";

const TMP_REPO = fs.mkdtempSync(path.join(os.tmpdir(), "react-gen-adapter-test-"));

// ─── Mock dependencies ───────────────────────────────────────────────────────

const mockWriteReactComponent = vi.fn().mockResolvedValue({
  pageName: "Login",
  filePath: path.join(TMP_REPO, "client/src/pages/login-page.tsx"),
  componentCode: 'export default function LoginPage() { return <div />; }',
  reviewScore: 0.9,
  reviewFeedback: [],
  passed: true,
  retried: false,
});

const mockBuildSharedComponents = vi.fn().mockResolvedValue({
  designTokens: path.join(TMP_REPO, "client/src/lib/design-tokens.ts"),
  UniversalLayout: path.join(TMP_REPO, "client/src/components/universal-layout.tsx"),
});

const mockEnsureLivePreviewServer = vi.fn().mockResolvedValue({
  url: "http://localhost:5173",
  isNew: false,
  shutdown: async () => {},
});

vi.mock("../../../lib/react-gen/component-writer.js", () => ({
  writeReactComponent: (...args: unknown[]) => mockWriteReactComponent(...args),
}));

vi.mock("../../../lib/react-gen/shared-component-builder.js", () => ({
  buildSharedComponents: (...args: unknown[]) => mockBuildSharedComponents(...args),
}));

vi.mock("../../../lib/react-gen/live-preview-server.js", () => ({
  ensureLivePreviewServer: (...args: unknown[]) => mockEnsureLivePreviewServer(...args),
}));

vi.mock("../../../lib/react-gen/build-status-overlay.js", () => ({
  injectBuildOverlay: vi.fn().mockResolvedValue(undefined),
  updateBuildStatus: vi.fn().mockResolvedValue(undefined),
  removeBuildOverlay: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("../../../lib/react-gen/screenshot-reviewer.js", () => ({
  screenshotAndReview: vi.fn().mockResolvedValue({
    score: 0.9,
    issues: [],
    screenshotPath: "",
  }),
}));

vi.mock("../../../lib/spec-parser/brand-voice-inferrer.js", () => ({
  loadBrandVoice: () => "# Brand Voice\nBe direct.",
}));

vi.mock("../../../lib/intake/intake-orchestrator.js", () => ({
  loadBriefFromConfig: () => null,
}));

// Mock DB
const mockDbSelect = vi.fn();
const mockDbFrom = vi.fn();
const mockDbWhere = vi.fn();
const mockDbOrderBy = vi.fn();
const mockDbLimit = vi.fn();

vi.mock("../../../lib/orchestrator/db.js", () => ({
  getOrchestratorDb: () => ({
    select: () => ({
      from: (table: unknown) => ({
        where: (cond: unknown) => ({
          orderBy: (ord: unknown) => ({
            limit: (n: number) => mockDbLimit(n),
          }),
          limit: (n: number) => mockDbLimit(n),
        }),
      }),
    }),
  }),
}));

import { reactGenPhaseImplementation } from "../../../lib/orchestrator/phases/react-gen-adapter.js";
import type { ProjectConfig } from "../../../shared/design-schema.js";

function makeConfig(): ProjectConfig {
  // Ensure design system file exists for the adapter
  const designDir = path.join(TMP_REPO, ".planning");
  fs.mkdirSync(designDir, { recursive: true });
  fs.writeFileSync(path.join(designDir, "design-system.md"), "# Design System", "utf-8");
  // Ensure public dir exists for overlay
  fs.mkdirSync(path.join(TMP_REPO, "public"), { recursive: true });
  fs.mkdirSync(path.join(TMP_REPO, "client", "src", "components"), { recursive: true });
  fs.mkdirSync(path.join(TMP_REPO, "client", "src", "pages"), { recursive: true });

  return {
    projectId: "test-project",
    repoPath: TMP_REPO,
    framework: "react-vite-tailwind-shadcn",
    designSystemPath: ".planning/design-system.md",
    outputPath: ".planning/output",
    clientSrcPath: "client/src",
    serverPath: "server",
    defaultBranch: "main",
    featureBranchPrefix: "feature/",
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  // Default: spec query returns a spec with one page
  mockDbLimit.mockResolvedValue([
    {
      output: JSON.stringify({
        pages: [
          {
            name: "Login",
            route: "/login",
            purpose: "User authentication",
            components: ["LoginForm"],
            authLevel: "public",
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
        ],
        sharedComponents: [],
        suggestedOrder: ["Login"],
      }),
      completedAt: new Date(),
    },
  ]);
});

describe("reactGenPhaseImplementation", () => {
  it("prepare() returns work units matching suggestedOrder", async () => {
    const config = makeConfig();
    const units = await reactGenPhaseImplementation.prepare(config);

    expect(units.length).toBe(1);
    expect(units[0].pageName).toBe("Login");
    expect(units[0].pageIndex).toBe(0);
  });

  it("prepare() calls buildSharedComponents before pages", async () => {
    const config = makeConfig();
    await reactGenPhaseImplementation.prepare(config);

    expect(mockBuildSharedComponents).toHaveBeenCalledTimes(1);
    expect(mockEnsureLivePreviewServer).toHaveBeenCalledTimes(1);
  });

  it("runPage() calls writeReactComponent for non-cached input", async () => {
    const config = makeConfig();
    const units = await reactGenPhaseImplementation.prepare(config);
    // Clear the precomputed output so runPage falls back to direct generation
    const input = units[0].input as Record<string, unknown>;
    delete input.precomputedOutput;
    delete input.precomputedError;

    await reactGenPhaseImplementation.runPage(units[0].input, config);
    expect(mockWriteReactComponent).toHaveBeenCalled();
  });

  it("runPage() throws when precomputedError is set", async () => {
    const config = makeConfig();
    const input = {
      page: { name: "Login" },
      precomputedError: "Generation failed: rate limited",
    };

    await expect(reactGenPhaseImplementation.runPage(input, config)).rejects.toThrow(
      "Generation failed: rate limited",
    );
  });

  it("runPage() returns cached output when precomputedOutput is set", async () => {
    const config = makeConfig();
    const cached = {
      pageName: "Login",
      filePath: "/tmp/login-page.tsx",
      componentCode: "export default function LoginPage() { return <div />; }",
      reviewScore: 0.92,
      reviewFeedback: [],
      passed: true,
      retried: false,
    };
    const input = {
      page: { name: "Login" },
      precomputedOutput: cached,
    };

    const result = await reactGenPhaseImplementation.runPage(input, config);
    expect(result).toMatchObject({
      filePath: cached.filePath,
      reviewScore: 0.92,
      passed: true,
    });
  });
});

describe("phase registration", () => {
  it("react-gen phase is importable and has prepare + runPage", () => {
    expect(typeof reactGenPhaseImplementation.prepare).toBe("function");
    expect(typeof reactGenPhaseImplementation.runPage).toBe("function");
  });
});
