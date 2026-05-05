import { describe, it, expect, beforeEach, afterEach } from "vitest";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { ArtifactStore } from "../../../lib/agents/artifact-store.js";
import type {
  ProductInsights,
  SystemArchitecture,
  DesignSystem,
  ComponentInterface,
  PageOutput,
  BackendRoute,
  QAReport,
  BuildState,
  BuildStatus,
} from "../../../lib/agents/types.js";
import type { ProjectBrief } from "../../../lib/intake/types.js";
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
    brandVoice: "",
    designSystem: "",
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

function makeProductInsights(): ProductInsights {
  return {
    productCategory: "saas",
    targetUserProfile: "developers",
    competitiveIntel: null,
    designRecommendations: ["Use dark mode"],
    copyRecommendations: ["Be concise"],
    architectureRecommendations: ["Use REST"],
    marketPositioning: "Developer tools",
  };
}

function makeArchitecture(): SystemArchitecture {
  return {
    dataModel: {
      entities: [{ tableName: "users", fields: [{ name: "id", type: "serial", nullable: false }], indexes: [], timestamps: true }],
      relationships: [],
      enums: [],
    },
    apiContracts: [{ method: "GET", path: "/api/users", description: "List users", authRequired: true, responseShape: { users: "User[]" }, validationRules: [], relatedEntity: "users" }],
    pages: [{ name: "Dashboard", route: "/dashboard", authLevel: "authenticated", purpose: "Main view", components: [], dataNeeds: [], mutations: [] }],
    componentHierarchy: [{ name: "Sidebar", purpose: "Navigation", props: [], usedByPages: ["Dashboard"], dependsOn: [] }],
    userFlows: [{ name: "Login", steps: ["Enter credentials", "Submit", "Redirect"] }],
  };
}

function makeDesignSystem(): DesignSystem {
  return {
    tokens: {
      colors: { primary: "#3b82f6", background: "#ffffff" },
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

function makePageOutput(name = "Dashboard"): PageOutput {
  return {
    pageName: name,
    filePath: `client/src/pages/${name.toLowerCase()}-page.tsx`,
    route: `/${name.toLowerCase()}`,
    componentCode: `export default function ${name}Page() { return <div>${name}</div>; }`,
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

function makeBackendRoute(method = "GET", routePath = "/api/users"): BackendRoute {
  return {
    method,
    path: routePath,
    filePath: "server/generated/routes/users.ts",
    entity: "users",
    schemaGenerated: true,
    storageGenerated: true,
  };
}

function makeQAReport(): QAReport {
  return {
    allPassed: true,
    totalIssues: 0,
    issuesFixed: 0,
    remainingIssues: [],
    iterations: 0,
    tscClean: true,
    pageResults: [],
  };
}

function makeBuildState(): BuildState {
  return {
    projectRoot: tmpDir,
    brief: makeBrief(),
    status: makeBuildStatus(),
    agentResults: {},
    checkpoints: [],
  };
}

function makeBuildStatus(): BuildStatus {
  return {
    phase: "intake",
    totalAgents: 8,
    completedAgents: [],
    currentAgents: [],
    failedAgents: [],
    startedAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
}

// ─── Setup / Teardown ───────────────────────────────────────────────────────

beforeEach(() => {
  tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "artifact-store-test-"));
  store = new ArtifactStore(tmpDir);
});

afterEach(() => {
  fs.rmSync(tmpDir, { recursive: true, force: true });
});

// ─── Tests ──────────────────────────────────────────────────────────────────

describe("ArtifactStore", () => {
  describe("construction", () => {
    it("creates .planning/artifacts directory on construction", () => {
      const artifactsDir = path.join(tmpDir, ".planning", "artifacts");
      expect(fs.existsSync(artifactsDir)).toBe(true);
    });

    it("does not throw if artifacts directory already exists", () => {
      expect(() => new ArtifactStore(tmpDir)).not.toThrow();
    });
  });

  describe("set/get/exists for each artifact type", () => {
    it("brief: set, get, exists", () => {
      expect(store.exists("brief")).toBe(false);
      expect(store.getBrief()).toBeNull();

      const brief = makeBrief();
      store.setBrief(brief);

      expect(store.exists("brief")).toBe(true);
      const retrieved = store.getBrief();
      expect(retrieved).not.toBeNull();
      expect(retrieved!.productName).toBe("TestApp");
    });

    it("product-insights: set, get, exists", () => {
      expect(store.exists("product-insights")).toBe(false);
      expect(store.getProductInsights()).toBeNull();

      const insights = makeProductInsights();
      store.setProductInsights(insights);

      expect(store.exists("product-insights")).toBe(true);
      expect(store.getProductInsights()!.productCategory).toBe("saas");
    });

    it("architecture: set, get, exists", () => {
      expect(store.exists("architecture")).toBe(false);
      expect(store.getArchitecture()).toBeNull();

      const arch = makeArchitecture();
      store.setArchitecture(arch);

      expect(store.exists("architecture")).toBe(true);
      expect(store.getArchitecture()!.dataModel.entities).toHaveLength(1);
    });

    it("design-system: set, get, exists", () => {
      expect(store.exists("design-system")).toBe(false);
      expect(store.getDesignSystem()).toBeNull();

      const ds = makeDesignSystem();
      store.setDesignSystem(ds);

      expect(store.exists("design-system")).toBe(true);
      expect(store.getDesignSystem()!.aesthetic).toBe("Clean and minimal");
    });

    it("project-copy: set, get, exists", () => {
      expect(store.exists("project-copy")).toBe(false);
      expect(store.getProjectCopy()).toBeNull();

      const copy = makeProjectCopy();
      store.setProjectCopy(copy);

      expect(store.exists("project-copy")).toBe(true);
      expect(store.getProjectCopy()!.pages).toHaveLength(1);
    });

    it("component-interfaces: set, get, exists", () => {
      expect(store.exists("component-interfaces")).toBe(false);
      expect(store.getComponentInterfaces()).toBeNull();

      const interfaces: ComponentInterface[] = [
        { name: "Button", filePath: "client/src/components/ui/button.tsx", exportName: "Button", props: [{ name: "variant", type: "string", optional: true }], dependsOn: [] },
      ];
      store.setComponentInterfaces(interfaces);

      expect(store.exists("component-interfaces")).toBe(true);
      expect(store.getComponentInterfaces()!).toHaveLength(1);
      expect(store.getComponentInterfaces()![0].name).toBe("Button");
    });

    it("component-paths: set, get, exists", () => {
      expect(store.exists("component-paths")).toBe(false);
      expect(store.getComponentPaths()).toBeNull();

      const paths = { Button: "@/components/ui/button", Card: "@/components/ui/card" };
      store.setComponentPaths(paths);

      expect(store.exists("component-paths")).toBe(true);
      expect(store.getComponentPaths()!.Button).toBe("@/components/ui/button");
    });

    it("page-outputs: set, get, exists", () => {
      expect(store.exists("page-outputs")).toBe(false);
      expect(store.getPageOutputs()).toBeNull();

      const pages = [makePageOutput()];
      store.setPageOutputs(pages);

      expect(store.exists("page-outputs")).toBe(true);
      expect(store.getPageOutputs()!).toHaveLength(1);
    });

    it("backend-routes: set, get, exists", () => {
      expect(store.exists("backend-routes")).toBe(false);
      expect(store.getBackendRoutes()).toBeNull();

      const routes = [makeBackendRoute()];
      store.setBackendRoutes(routes);

      expect(store.exists("backend-routes")).toBe(true);
      expect(store.getBackendRoutes()!).toHaveLength(1);
    });

    it("qa-report: set, get, exists", () => {
      expect(store.exists("qa-report")).toBe(false);
      expect(store.getQAReport()).toBeNull();

      const report = makeQAReport();
      store.setQAReport(report);

      expect(store.exists("qa-report")).toBe(true);
      expect(store.getQAReport()!.allPassed).toBe(true);
    });

    it("build-state: set, get, exists", () => {
      expect(store.exists("build-state")).toBe(false);
      expect(store.getBuildState()).toBeNull();

      const state = makeBuildState();
      store.setBuildState(state);

      expect(store.exists("build-state")).toBe(true);
      expect(store.getBuildState()!.projectRoot).toBe(tmpDir);
    });

    it("build-status: set, get, exists", () => {
      expect(store.exists("build-status")).toBe(false);
      expect(store.getBuildStatus()).toBeNull();

      const status = makeBuildStatus();
      store.setBuildStatus(status);

      expect(store.exists("build-status")).toBe(true);
      expect(store.getBuildStatus()!.phase).toBe("intake");
    });
  });

  describe("atomic writes", () => {
    it("writes file atomically (file exists after set)", () => {
      store.setBrief(makeBrief());
      const filePath = path.join(tmpDir, ".planning", "artifacts", "brief.json");
      expect(fs.existsSync(filePath)).toBe(true);

      const content = JSON.parse(fs.readFileSync(filePath, "utf-8"));
      expect(content.productName).toBe("TestApp");
    });
  });

  describe("addPageOutput", () => {
    it("adds a new page output when none exist", () => {
      const page = makePageOutput("Dashboard");
      store.addPageOutput(page);

      const outputs = store.getPageOutputs();
      expect(outputs).toHaveLength(1);
      expect(outputs![0].pageName).toBe("Dashboard");
    });

    it("adds a new page output alongside existing ones", () => {
      store.addPageOutput(makePageOutput("Dashboard"));
      store.addPageOutput(makePageOutput("Settings"));

      const outputs = store.getPageOutputs();
      expect(outputs).toHaveLength(2);
      expect(outputs![0].pageName).toBe("Dashboard");
      expect(outputs![1].pageName).toBe("Settings");
    });

    it("updates existing page output by pageName", () => {
      store.addPageOutput(makePageOutput("Dashboard"));

      const updated = makePageOutput("Dashboard");
      updated.reviewScore = 0.5;
      updated.passed = false;
      store.addPageOutput(updated);

      const outputs = store.getPageOutputs();
      expect(outputs).toHaveLength(1);
      expect(outputs![0].reviewScore).toBe(0.5);
      expect(outputs![0].passed).toBe(false);
    });
  });

  describe("addBackendRoute", () => {
    it("adds a new backend route when none exist", () => {
      const route = makeBackendRoute();
      store.addBackendRoute(route);

      const routes = store.getBackendRoutes();
      expect(routes).toHaveLength(1);
      expect(routes![0].path).toBe("/api/users");
    });

    it("adds a new route alongside existing ones", () => {
      store.addBackendRoute(makeBackendRoute("GET", "/api/users"));
      store.addBackendRoute(makeBackendRoute("POST", "/api/users"));

      const routes = store.getBackendRoutes();
      expect(routes).toHaveLength(2);
    });

    it("updates existing route by method + path", () => {
      store.addBackendRoute(makeBackendRoute("GET", "/api/users"));

      const updated = makeBackendRoute("GET", "/api/users");
      updated.entity = "accounts";
      store.addBackendRoute(updated);

      const routes = store.getBackendRoutes();
      expect(routes).toHaveLength(1);
      expect(routes![0].entity).toBe("accounts");
    });
  });

  describe("appendBuildLog", () => {
    it("appends JSONL lines to build-log.jsonl", () => {
      store.appendBuildLog({ agent: "arch", event: "started", timestamp: 1000 });
      store.appendBuildLog({ agent: "arch", event: "completed", timestamp: 2000, detail: "ok" });

      const logPath = path.join(tmpDir, ".planning", "artifacts", "build-log.jsonl");
      expect(fs.existsSync(logPath)).toBe(true);

      const lines = fs.readFileSync(logPath, "utf-8").trim().split("\n");
      expect(lines).toHaveLength(2);

      const first = JSON.parse(lines[0]);
      expect(first.agent).toBe("arch");
      expect(first.event).toBe("started");

      const second = JSON.parse(lines[1]);
      expect(second.detail).toBe("ok");
    });
  });

  describe("writeProjectFile / readProjectFile", () => {
    it("writes and reads a project file", () => {
      store.writeProjectFile("src/index.ts", "console.log('hello');");
      const content = store.readProjectFile("src/index.ts");
      expect(content).toBe("console.log('hello');");
    });

    it("creates intermediate directories", () => {
      store.writeProjectFile("deep/nested/dir/file.ts", "export {};");
      const fullPath = path.join(tmpDir, "deep", "nested", "dir", "file.ts");
      expect(fs.existsSync(fullPath)).toBe(true);
    });

    it("returns null for non-existent project file", () => {
      expect(store.readProjectFile("does-not-exist.ts")).toBeNull();
    });
  });

  describe("existing-codebase-audit: set, get, exists", () => {
    it("stores and retrieves codebase audit", () => {
      expect(store.getExistingCodebaseAudit()).toBeNull();

      const audit = {
        existingRoutes: ["GET /api/users", "POST /api/auth/login"],
        existingTables: ["users", "sessions"],
        existingPages: ["dashboard-page.tsx", "settings-page.tsx"],
        existingStorageMethods: ["getUser", "createUser"],
        scannedAt: new Date().toISOString(),
      };
      store.setExistingCodebaseAudit(audit);

      expect(store.getExistingCodebaseAudit()).not.toBeNull();
      expect(store.getExistingCodebaseAudit()!.existingRoutes).toHaveLength(2);
      expect(store.getExistingCodebaseAudit()!.existingTables).toContain("users");
    });
  });

  describe("user-defined-constraints: set, get", () => {
    it("stores and retrieves user constraints", () => {
      expect(store.getUserDefinedConstraints()).toBeNull();

      store.setUserDefinedConstraints({
        explicit: { primaryColor: "#6a37d4", font: "Inter" },
        implicit: { tone: "professional" },
        open: ["animation style", "icon choices"],
      });

      const result = store.getUserDefinedConstraints();
      expect(result).not.toBeNull();
      expect(result!.explicit.primaryColor).toBe("#6a37d4");
      expect(result!.implicit.tone).toBe("professional");
      expect(result!.open).toHaveLength(2);
    });
  });

  describe("creative-decisions: append, get", () => {
    it("appends and retrieves creative decisions", () => {
      expect(store.getCreativeDecisions()).toEqual([]);

      store.appendCreativeDecision({
        agent: "design-system",
        decision: "Used dark mode",
        rationale: "Product targets developers who prefer dark interfaces",
        coherenceCheck: "Consistent with professional tone",
      });

      store.appendCreativeDecision({
        agent: "page-agent",
        decision: "Used card grid layout",
        rationale: "Dashboard needs at-a-glance metrics",
        coherenceCheck: "Fits information-dense operator product",
      });

      const decisions = store.getCreativeDecisions();
      expect(decisions).toHaveLength(2);
      expect(decisions[0].agent).toBe("design-system");
      expect(decisions[1].agent).toBe("page-agent");
    });
  });

  describe("returns null for non-existent artifacts", () => {
    it("returns null for every getter when no artifacts exist", () => {
      expect(store.getBrief()).toBeNull();
      expect(store.getProductInsights()).toBeNull();
      expect(store.getUserDefinedConstraints()).toBeNull();
      expect(store.getExistingCodebaseAudit()).toBeNull();
      expect(store.getArchitecture()).toBeNull();
      expect(store.getDesignSystem()).toBeNull();
      expect(store.getProjectCopy()).toBeNull();
      expect(store.getComponentInterfaces()).toBeNull();
      expect(store.getComponentPaths()).toBeNull();
      expect(store.getPageOutputs()).toBeNull();
      expect(store.getBackendRoutes()).toBeNull();
      expect(store.getQAReport()).toBeNull();
      expect(store.getBuildState()).toBeNull();
      expect(store.getBuildStatus()).toBeNull();
    });
  });

  describe("build status writes to public/build-status.json", () => {
    it("writes build status to both artifacts and public directory", () => {
      const status = makeBuildStatus();
      store.setBuildStatus(status);

      // Artifacts location
      const artifactPath = path.join(tmpDir, ".planning", "artifacts", "build-status.json");
      expect(fs.existsSync(artifactPath)).toBe(true);

      // Public location
      const publicPath = path.join(tmpDir, "public", "build-status.json");
      expect(fs.existsSync(publicPath)).toBe(true);

      const publicContent = JSON.parse(fs.readFileSync(publicPath, "utf-8"));
      expect(publicContent.phase).toBe("intake");
    });
  });

  describe("agent results", () => {
    it("sets and gets agent results", () => {
      store.setAgentResult("architecture", {
        agentName: "architecture",
        status: "completed",
        data: makeArchitecture(),
        error: null,
        durationMs: 5000,
        retries: 0,
      });

      const result = store.getAgentResult("architecture");
      expect(result).not.toBeNull();
      expect(result!.agentName).toBe("architecture");
      expect(result!.status).toBe("completed");
    });

    it("returns null for non-existent agent result", () => {
      expect(store.getAgentResult("nonexistent")).toBeNull();
    });
  });

  describe("getProjectRoot", () => {
    it("returns the project root path", () => {
      expect(store.getProjectRoot()).toBe(tmpDir);
    });
  });
});
