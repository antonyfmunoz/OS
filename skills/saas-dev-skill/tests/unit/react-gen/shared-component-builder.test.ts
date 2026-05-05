import { describe, it, expect, vi } from "vitest";

// ─── Mock Claude ─────────────────────────────────────────────────────────────

const mockStream = {
  finalMessage: vi.fn().mockResolvedValue({
    content: [{ type: "text", text: 'export default function Stub() { return <div />; }\nexport { Stub };' }],
  }),
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

import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { buildSharedComponents, SHARED_COMPONENTS } from "../../../lib/react-gen/shared-component-builder.js";
import type { ProjectBrief } from "../../../lib/intake/types.js";

const TMP_REPO = fs.mkdtempSync(path.join(os.tmpdir(), "shared-builder-test-"));

const mockBrief: ProjectBrief = {
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
};

describe("SHARED_COMPONENTS definition", () => {
  it("defines exactly 7 components", () => {
    expect(SHARED_COMPONENTS).toHaveLength(7);
  });

  it("has correct build order", () => {
    const names = SHARED_COMPONENTS.map((c) => c.name);
    expect(names).toEqual([
      "designTokens",
      "AgentChatStub",
      "FloatingAiPanel",
      "LeftRail",
      "RightRail",
      "Header",
      "UniversalLayout",
    ]);
  });

  it("each component has required fields", () => {
    for (const comp of SHARED_COMPONENTS) {
      expect(comp.name).toBeTruthy();
      expect(comp.fileName).toBeTruthy();
      expect(comp.relativePath).toBeTruthy();
      expect(comp.description).toBeTruthy();
      expect(Array.isArray(comp.dependsOn)).toBe(true);
    }
  });

  it("dependencies reference valid component names", () => {
    const names = new Set(SHARED_COMPONENTS.map((c) => c.name));
    for (const comp of SHARED_COMPONENTS) {
      for (const dep of comp.dependsOn) {
        expect(names.has(dep)).toBe(true);
      }
    }
  });

  it("no circular dependencies (each depends only on earlier components)", () => {
    const built = new Set<string>();
    for (const comp of SHARED_COMPONENTS) {
      for (const dep of comp.dependsOn) {
        expect(built.has(dep)).toBe(true);
      }
      built.add(comp.name);
    }
  });
});

describe("buildSharedComponents", () => {
  it("returns a map of component name → file path for all 7 components", async () => {
    const result = await buildSharedComponents(mockBrief, TMP_REPO);

    expect(Object.keys(result)).toHaveLength(7);
    for (const [name, filePath] of Object.entries(result)) {
      expect(name).toBeTruthy();
      expect(filePath).toBeTruthy();
      expect(fs.existsSync(filePath)).toBe(true);
    }
  });

  it("writes files under client/src/", async () => {
    const result = await buildSharedComponents(mockBrief, TMP_REPO);
    const clientSrc = path.join(TMP_REPO, "client", "src");

    for (const filePath of Object.values(result)) {
      expect(filePath.startsWith(clientSrc)).toBe(true);
    }
  });
});
