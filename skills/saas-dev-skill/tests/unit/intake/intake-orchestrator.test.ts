import { describe, it, expect, vi, beforeEach, afterAll } from "vitest";
import fs from "node:fs";
import path from "node:path";

// ─── Mock Anthropic SDK ───────────────────────────────────────────────────────

const mockMessagesCreate = vi.fn();
const mockMessagesStream = vi.fn();

vi.mock("@anthropic-ai/sdk", () => {
  return {
    default: vi.fn().mockImplementation(() => ({
      messages: {
        create: mockMessagesCreate,
        stream: mockMessagesStream,
      },
    })),
  };
});

// ─── Import under test ────────────────────────────────────────────────────────

import { runIntake, loadBriefFromConfig } from "../../../lib/intake/intake-orchestrator.js";
import { ProjectBriefSchema } from "../../../lib/intake/types.js";
import type { ProjectConfig } from "../../../shared/design-schema.js";

// ─── Helpers ──────────────────────────────────────────────────────────────────

const BASE = path.join(process.cwd(), "tests", "tmp-intake-" + Date.now());
let testIdx = 0;

function makeRoot(files: Record<string, string> = {}): string {
  const root = path.join(BASE, String(testIdx++));
  for (const [filePath, content] of Object.entries(files)) {
    const full = path.join(root, filePath);
    fs.mkdirSync(path.dirname(full), { recursive: true });
    fs.writeFileSync(full, content, "utf-8");
  }
  return root;
}

function makeConfig(root: string): ProjectConfig {
  return {
    projectId: "test-proj",
    repoPath: root,
    framework: "react-vite-tailwind-shadcn",
    designSystemPath: ".planning/design-system.md",
    outputPath: ".planning/output",
    clientSrcPath: "client/src",
    serverPath: "server",
    defaultBranch: "main",
    featureBranchPrefix: "feature/",
  };
}

const VALID_SPEC = JSON.stringify({
  pages: [{
    name: "Dashboard",
    route: "/dashboard",
    purpose: "Main view",
    components: ["sidebar", "chart"],
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
  }],
  sharedComponents: [],
  suggestedOrder: ["/dashboard"],
  backendSpec: {
    endpoints: [{ method: "GET", path: "/api/dashboard", description: "Get dashboard data", requestBody: [], responseFields: ["data"], authRequired: true, source: "inferred" }],
    drizzleTableHints: [],
    backgroundJobs: [],
    mismatches: [],
  },
});

beforeEach(() => {
  vi.clearAllMocks();
  process.env.SKIP_GAP_ANALYSIS = "true";
});

afterAll(() => {
  delete process.env.SKIP_GAP_ANALYSIS;
  if (fs.existsSync(BASE)) {
    fs.rmSync(BASE, { recursive: true, force: true });
  }
});

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("runIntake", () => {
  it("greenfield mode returns skeleton brief with isGreenfield=true", async () => {
    const root = makeRoot();
    const result = await runIntake(makeConfig(root));

    expect(result.mode).toBe("greenfield");
    expect(result.brief.isGreenfield).toBe(true);
    expect(result.brief.existingCodeScanned).toBe(false);
    expect(result.brief.spec.pages.length).toBe(1);
  });

  it("docs-only mode with pre-validated JSON spec produces brief without LLM call", async () => {
    const root = makeRoot({
      ".planning/PRD.md": "# TestProduct\n\n## 1. Executive Summary\nA testing product.\n\n---\n\n## 2. Product Vision\nBest product ever.\n\n---",
      ".planning/specs/mvp.json": VALID_SPEC,
    });

    // Brand voice inference will be called since no BRAND-VOICE.md
    mockMessagesCreate.mockResolvedValueOnce({
      content: [{ type: "text", text: "## Tone\nProfessional." }],
    });

    const result = await runIntake(makeConfig(root));

    expect(result.mode).toBe("docs-only");
    expect(result.brief.isGreenfield).toBe(false);
    expect(result.brief.spec.pages[0].name).toBe("Dashboard");
    expect(result.brief.productName).toBe("TestProduct");
    expect(result.brief.sourceDocs).toContain("PRD.md");
  });

  it("docs-only mode loads existing BRAND-VOICE.md without re-inferring", async () => {
    const root = makeRoot({
      ".planning/PRD.md": "# Product\n\n## 1. Executive Summary\nBuilding something.\n\n---",
      ".planning/BRAND-VOICE.md": "## Tone\nBold and authoritative.",
      ".planning/specs/mvp.json": VALID_SPEC,
    });

    const result = await runIntake(makeConfig(root));

    expect(result.brief.brandVoice).toBe("## Tone\nBold and authoritative.");
    // Should NOT have called Claude for brand voice
    expect(mockMessagesCreate).not.toHaveBeenCalled();
  });

  it("existing-codebase mode sets existingCodeScanned=true", async () => {
    const root = makeRoot({
      "client/src/App.tsx": "export default function App() {}",
      "package.json": JSON.stringify({
        dependencies: { react: "^18", "@clerk/clerk-react": "^5" },
        devDependencies: { vite: "^5", tailwindcss: "^3" },
      }),
      ".planning/PRD.md": "# Product\n\n## 1. Executive Summary\nFull stack app.\n\n---",
      ".planning/specs/mvp.json": VALID_SPEC,
    });

    mockMessagesCreate.mockResolvedValueOnce({
      content: [{ type: "text", text: "## Tone\nMinimal." }],
    });

    const result = await runIntake(makeConfig(root));

    expect(result.mode).toBe("existing-codebase");
    expect(result.brief.existingCodeScanned).toBe(true);
    expect(result.brief.techStack.frontend).toBe("react");
    expect(result.brief.authProvider).toBe("clerk");
  });
});

describe("ProjectBriefSchema", () => {
  it("validates a complete brief", () => {
    const brief = {
      productName: "TestApp",
      productDescription: "A test app",
      productVision: "Best app",
      targetUsers: ["developers"],
      jobsToBeDone: ["build fast"],
      brandVoice: "Professional",
      designSystem: "# Colors\nprimary: blue",
      techStack: { frontend: "react", buildTool: "vite", styling: "tailwind", componentLib: "shadcn/ui", language: "typescript" },
      authProvider: "clerk",
      dbProvider: "neon",
      deployTarget: "vps",
      spec: JSON.parse(VALID_SPEC),
      isGreenfield: false,
      existingCodeScanned: true,
      sourceDocs: ["PRD.md"],
    };

    const result = ProjectBriefSchema.safeParse(brief);
    expect(result.success).toBe(true);
  });

  it("rejects brief missing required fields", () => {
    const result = ProjectBriefSchema.safeParse({});
    expect(result.success).toBe(false);
  });

  it("applies defaults for optional fields", () => {
    const brief = {
      productName: "X",
      productDescription: "Y",
      techStack: {},
      spec: JSON.parse(VALID_SPEC),
      isGreenfield: true,
    };
    const result = ProjectBriefSchema.safeParse(brief);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.authProvider).toBe("clerk");
      expect(result.data.dbProvider).toBe("neon");
      expect(result.data.techStack.frontend).toBe("react");
    }
  });
});

describe("loadBriefFromConfig", () => {
  it("returns null for config without brief", () => {
    expect(loadBriefFromConfig(JSON.stringify({ projectId: "x" }))).toBeNull();
  });

  it("returns null for invalid JSON", () => {
    expect(loadBriefFromConfig("not json")).toBeNull();
  });

  it("returns brief when valid", () => {
    const brief = {
      productName: "X",
      productDescription: "Y",
      techStack: { frontend: "react", buildTool: "vite", styling: "tailwind", componentLib: "shadcn/ui", language: "typescript" },
      authProvider: "clerk",
      dbProvider: "neon",
      deployTarget: "vps",
      spec: JSON.parse(VALID_SPEC),
      isGreenfield: true,
      existingCodeScanned: false,
      sourceDocs: [],
    };
    const result = loadBriefFromConfig(JSON.stringify({ brief }));
    expect(result).not.toBeNull();
    expect(result!.productName).toBe("X");
  });
});

