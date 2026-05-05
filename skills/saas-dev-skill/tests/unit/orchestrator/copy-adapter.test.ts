import { describe, it, expect, vi, beforeEach, beforeAll, afterAll } from "vitest";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";

// ─── Isolated temp workspace ─────────────────────────────────────────────────
// copy-adapter.runPage() writes PROJECT-COPY.json to
// `<config.repoPath>/.planning/output/copy/` using real filesystem APIs.
// Use a per-run tmpdir as repoPath so tests never touch the real workspace.
const TMP_REPO = fs.mkdtempSync(path.join(os.tmpdir(), "copy-adapter-test-"));

// ─── Mock dependencies ───────────────────────────────────────────────────────

const mockGenerateProjectCopy = vi.fn();
const mockReviewProjectCopy = vi.fn();

vi.mock("../../../lib/copy-planner/copy-writer.js", () => ({
  generateProjectCopy: (...args: unknown[]) => mockGenerateProjectCopy(...args),
}));

vi.mock("../../../lib/copy-planner/copy-reviewer.js", () => ({
  reviewProjectCopy: (...args: unknown[]) => mockReviewProjectCopy(...args),
}));

vi.mock("../../../lib/spec-parser/brand-voice-inferrer.js", () => ({
  loadBrandVoice: () => "# Brand Voice\nBe direct and commanding.",
}));

vi.mock("../../../lib/intake/intake-orchestrator.js", () => ({
  loadBriefFromConfig: (json: string) => {
    const parsed = JSON.parse(json);
    return parsed.brief ?? null;
  },
}));

const mockDbSelect = vi.fn();
vi.mock("../../../lib/orchestrator/db.js", () => ({
  getOrchestratorDb: () => ({
    select: () => ({
      from: () => ({
        where: () => ({
          orderBy: () => ({
            limit: () => mockDbSelect(),
          }),
        }),
      }),
    }),
  }),
}));

// ─── Import under test ────────────────────────────────────────────────────────

import { copyPhaseImplementation } from "../../../lib/orchestrator/phases/copy-adapter.js";
import type { ProjectConfig } from "../../../shared/design-schema.js";
import type { ProjectCopy } from "../../../lib/copy-planner/types.js";

// ─── Helpers ──────────────────────────────────────────────────────────────────

const SPEC = {
  pages: [
    { name: "Dashboard", route: "/dashboard", purpose: "Main view", components: [], authLevel: "authenticated", priority: 1, dependsOn: [], specVersion: 1, source: "explicit", dataRequirements: [], apiEndpoints: [], validationRules: [], events: [], featureFlagCandidates: [] },
  ],
  sharedComponents: [],
  suggestedOrder: ["/dashboard"],
  backendSpec: { endpoints: [], drizzleTableHints: [], backgroundJobs: [], mismatches: [] },
};

const BRIEF = {
  productName: "TestApp",
  productDescription: "Test",
  productVision: "",
  targetUsers: [],
  jobsToBeDone: [],
  brandVoice: "# Brand",
  designSystem: "",
  techStack: { frontend: "react", buildTool: "vite", styling: "tailwind", componentLib: "shadcn/ui", language: "typescript" },
  authProvider: "clerk",
  dbProvider: "neon",
  deployTarget: "vps",
  spec: SPEC,
  isGreenfield: false,
  existingCodeScanned: false,
  sourceDocs: [],
};

const CONFIG: ProjectConfig = {
  projectId: "test-proj",
  repoPath: TMP_REPO,
  framework: "react-vite-tailwind-shadcn",
  designSystemPath: ".planning/design-system.md",
  outputPath: ".planning/output",
  clientSrcPath: "client/src",
  serverPath: "server",
  defaultBranch: "main",
  featureBranchPrefix: "feature/",
};

const MOCK_COPY: ProjectCopy = {
  pages: [{
    pageName: "Dashboard",
    pageHeading: "Command Center",
    sections: [],
    ctas: [{ id: "add", label: "Add Task", context: "main" }],
    emptyState: "No data yet.",
    errorMessages: {},
    placeholders: {},
    helperText: {},
    successMessages: {},
    navLabel: "Home",
  }],
  generatedAt: new Date().toISOString(),
  brandVoiceHash: "abc123",
};

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("copyPhaseImplementation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // DB returns pipeline_runs with brief
    mockDbSelect.mockResolvedValue([{
      config: JSON.stringify({ ...CONFIG, brief: BRIEF }),
      startedAt: new Date(),
    }]);
  });

  afterAll(() => {
    // Clean up the isolated temp workspace created at module load.
    try {
      fs.rmSync(TMP_REPO, { recursive: true, force: true });
    } catch {
      // Best-effort cleanup; ignore failures.
    }
  });

  it("prepare() returns single work unit named 'project-copy'", async () => {
    const units = await copyPhaseImplementation.prepare(CONFIG);
    expect(units).toHaveLength(1);
    expect(units[0].pageName).toBe("project-copy");
    expect(units[0].pageIndex).toBe(0);
  });

  it("runPage() calls generateProjectCopy then reviewProjectCopy", async () => {
    mockGenerateProjectCopy.mockResolvedValueOnce(MOCK_COPY);
    mockReviewProjectCopy.mockResolvedValueOnce({
      overallScore: 0.9,
      passed: true,
      pageResults: [{ pageName: "Dashboard", score: 0.9, issues: [] }],
      revisedCopy: MOCK_COPY,
    });

    const input = { spec: SPEC, brandVoice: "# Brand", projectBrief: BRIEF };
    const result = await copyPhaseImplementation.runPage(input, CONFIG);
    const copy = result as ProjectCopy;

    expect(mockGenerateProjectCopy).toHaveBeenCalledTimes(1);
    expect(mockReviewProjectCopy).toHaveBeenCalledTimes(1);
    expect(copy.pages).toHaveLength(1);
    expect(copy.pages[0].pageName).toBe("Dashboard");
  });

  it("runPage() uses revisedCopy from review even when passed", async () => {
    const revisedCopy = { ...MOCK_COPY, pages: [{ ...MOCK_COPY.pages[0], pageHeading: "Your Command Center" }] };
    mockGenerateProjectCopy.mockResolvedValueOnce(MOCK_COPY);
    mockReviewProjectCopy.mockResolvedValueOnce({
      overallScore: 0.92,
      passed: true,
      pageResults: [{ pageName: "Dashboard", score: 0.92, issues: [] }],
      revisedCopy,
    });

    const input = { spec: SPEC, brandVoice: "# Brand", projectBrief: BRIEF };
    const result = await copyPhaseImplementation.runPage(input, CONFIG) as ProjectCopy;

    expect(result.pages[0].pageHeading).toBe("Your Command Center");
  });
});

describe("copy phase registration", () => {
  it("'copy' is a valid phase in the type system", () => {
    // This test verifies that the Phase type includes 'copy'
    // by importing the type and using it
    const phase: import("../../../lib/orchestrator/db.js").Phase = "copy";
    expect(phase).toBe("copy");
  });
});
