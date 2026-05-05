import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtemp, mkdir, writeFile, rm } from "fs/promises";
import { tmpdir } from "os";
import { join } from "path";
import { auditBackendBrownfield, detectCollisions } from "../../../lib/backend-wirer/brownfield-backend-audit.js";
import type { BackendBrownfieldInventory } from "../../../lib/backend-wirer/types.js";
import type { BackendSpec } from "../../../lib/backend-wirer/types.js";

// ─── Test Fixtures ────────────────────────────────────────────────────────────

const MOCK_ROUTES_TS = `
import { Express } from "express";
import { createServer, type Server } from "http";

export function registerRoutes(app: Express): Server {
  app.get("/api/users", async (req, res) => {
    res.json([]);
  });

  app.post("/api/agents", async (req, res) => {
    res.json({});
  });

  app.put("/api/agents/:id", async (req, res) => {
    res.json({});
  });

  app.delete("/api/tasks/:id", async (req, res) => {
    res.json({ success: true });
  });

  app.patch("/api/users/:id", async (req, res) => {
    res.json({});
  });

  const httpServer = createServer(app);
  return httpServer;
}
`.trim();

const MOCK_STORAGE_TS = `
import { db } from "./db";

class DatabaseStorage {
  async getUser(id: string) {
    return null;
  }

  async createAgent(data: any) {
    return {};
  }

  async updateTask(id: string, data: any) {
    return {};
  }

  async deleteDocument(id: string) {
    return true;
  }
}

export const storage = new DatabaseStorage();
`.trim();

const MOCK_SCHEMA_TS = `
import { pgTable, text, timestamp } from "drizzle-orm/pg-core";

export const users = pgTable("users", {
  id: text("id").primaryKey(),
});

export const agents = pgTable("agents", {
  id: text("id").primaryKey(),
  userId: text("user_id"),
});

export const tasks = pgTable("tasks", {
  id: text("id").primaryKey(),
});
`.trim();

const MOCK_ROUTES_NO_SERVER = `
import { Express } from "express";

export function registerRoutes(app: Express) {
  app.get("/api/items", async (req, res) => {
    res.json([]);
  });
}
`.trim();

// ─── Test Setup ───────────────────────────────────────────────────────────────

let tmpDir: string;

async function createMockProject(overrides: {
  routesContent?: string;
  storageContent?: string;
  schemaContent?: string;
} = {}): Promise<string> {
  const projectDir = await mkdtemp(join(tmpdir(), "backend-audit-test-"));
  await mkdir(join(projectDir, "server"), { recursive: true });
  await mkdir(join(projectDir, "shared"), { recursive: true });

  await writeFile(
    join(projectDir, "server", "routes.ts"),
    overrides.routesContent ?? MOCK_ROUTES_TS
  );
  await writeFile(
    join(projectDir, "server", "storage.ts"),
    overrides.storageContent ?? MOCK_STORAGE_TS
  );
  await writeFile(
    join(projectDir, "shared", "schema.ts"),
    overrides.schemaContent ?? MOCK_SCHEMA_TS
  );

  return projectDir;
}

beforeEach(async () => {
  tmpDir = "";
});

afterEach(async () => {
  if (tmpDir) {
    await rm(tmpDir, { recursive: true, force: true });
  }
});

// ─── Route Extraction Tests ───────────────────────────────────────────────────

describe("auditBackendBrownfield - route extraction", () => {
  it("extracts GET routes from routes.ts", async () => {
    tmpDir = await createMockProject();
    const inventory = await auditBackendBrownfield(tmpDir);
    expect(inventory.existingRoutePaths).toContain("/api/users");
  });

  it("extracts POST routes from routes.ts", async () => {
    tmpDir = await createMockProject();
    const inventory = await auditBackendBrownfield(tmpDir);
    expect(inventory.existingRoutePaths).toContain("/api/agents");
  });

  it("extracts all HTTP methods (GET, POST, PUT, PATCH, DELETE)", async () => {
    tmpDir = await createMockProject();
    const inventory = await auditBackendBrownfield(tmpDir);
    // All 5 routes should be extracted
    expect(inventory.existingRoutePaths).toContain("/api/users");
    expect(inventory.existingRoutePaths).toContain("/api/agents");
    expect(inventory.existingRoutePaths).toContain("/api/agents/:id");
    expect(inventory.existingRoutePaths).toContain("/api/tasks/:id");
    expect(inventory.existingRoutePaths).toContain("/api/users/:id");
  });
});

// ─── Storage Function Extraction Tests ───────────────────────────────────────

describe("auditBackendBrownfield - storage function extraction", () => {
  it("extracts async function names from storage.ts", async () => {
    tmpDir = await createMockProject();
    const inventory = await auditBackendBrownfield(tmpDir);
    expect(inventory.existingStorageFunctions).toContain("getUser");
    expect(inventory.existingStorageFunctions).toContain("createAgent");
  });

  it("extracts all storage functions", async () => {
    tmpDir = await createMockProject();
    const inventory = await auditBackendBrownfield(tmpDir);
    expect(inventory.existingStorageFunctions).toContain("updateTask");
    expect(inventory.existingStorageFunctions).toContain("deleteDocument");
  });
});

// ─── Table Name Extraction Tests ──────────────────────────────────────────────

describe("auditBackendBrownfield - table name extraction", () => {
  it("extracts pgTable names from schema.ts", async () => {
    tmpDir = await createMockProject();
    const inventory = await auditBackendBrownfield(tmpDir);
    expect(inventory.existingTableNames).toContain("users");
    expect(inventory.existingTableNames).toContain("agents");
    expect(inventory.existingTableNames).toContain("tasks");
  });
});

// ─── Insertion Offset Tests ───────────────────────────────────────────────────

describe("auditBackendBrownfield - insertion offset detection", () => {
  it("finds routesInsertionOffset at createServer call position", async () => {
    tmpDir = await createMockProject();
    const inventory = await auditBackendBrownfield(tmpDir);
    // Should be positive — createServer exists in mock routes
    expect(inventory.routesInsertionOffset).toBeGreaterThan(0);
  });

  it("returns -1 for routesInsertionOffset when no createServer call exists", async () => {
    tmpDir = await createMockProject({ routesContent: MOCK_ROUTES_NO_SERVER });
    const inventory = await auditBackendBrownfield(tmpDir);
    expect(inventory.routesInsertionOffset).toBe(-1);
  });

  it("finds storageInsertionOffset at the last closing brace", async () => {
    tmpDir = await createMockProject();
    const inventory = await auditBackendBrownfield(tmpDir);
    expect(inventory.storageInsertionOffset).toBeGreaterThan(0);
  });

  it("sets schemaInsertionOffset to the length of schema.ts content", async () => {
    tmpDir = await createMockProject();
    const inventory = await auditBackendBrownfield(tmpDir);
    expect(inventory.schemaInsertionOffset).toBe(MOCK_SCHEMA_TS.length);
  });
});

// ─── Collision Detection Tests ────────────────────────────────────────────────

describe("detectCollisions", () => {
  it("detects collision when spec endpoint path matches existing route", () => {
    const inventory: BackendBrownfieldInventory = {
      existingRoutePaths: ["/api/users", "/api/agents"],
      existingStorageFunctions: ["getUser"],
      existingTableNames: ["users"],
      routesInsertionOffset: 100,
      storageInsertionOffset: 50,
      schemaInsertionOffset: 200,
    };

    const spec: BackendSpec = {
      endpoints: [
        {
          method: "GET",
          path: "/api/users",
          description: "Get all users",
          requestBody: [],
          responseFields: [],
          authRequired: true,
          source: "inferred",
        },
      ],
      drizzleTableHints: [],
      backgroundJobs: [],
      mismatches: [],
    };

    const result = detectCollisions(inventory, spec);
    expect(result.valid).toBe(false);
    expect(result.collisions).toHaveLength(1);
    expect(result.collisions[0]).toContain("/api/users");
  });

  it("returns no collisions when all spec endpoint paths are new", () => {
    const inventory: BackendBrownfieldInventory = {
      existingRoutePaths: ["/api/users", "/api/agents"],
      existingStorageFunctions: ["getUser"],
      existingTableNames: ["users"],
      routesInsertionOffset: 100,
      storageInsertionOffset: 50,
      schemaInsertionOffset: 200,
    };

    const spec: BackendSpec = {
      endpoints: [
        {
          method: "GET",
          path: "/api/items",
          description: "Get all items",
          requestBody: [],
          responseFields: [],
          authRequired: true,
          source: "inferred",
        },
        {
          method: "POST",
          path: "/api/items",
          description: "Create item",
          requestBody: [],
          responseFields: [],
          authRequired: true,
          source: "inferred",
        },
      ],
      drizzleTableHints: [],
      backgroundJobs: [],
      mismatches: [],
    };

    const result = detectCollisions(inventory, spec);
    expect(result.valid).toBe(true);
    expect(result.collisions).toHaveLength(0);
    expect(result.gaps).toHaveLength(0);
  });

  it("returns valid: true for empty spec endpoints", () => {
    const inventory: BackendBrownfieldInventory = {
      existingRoutePaths: ["/api/users"],
      existingStorageFunctions: [],
      existingTableNames: [],
      routesInsertionOffset: 0,
      storageInsertionOffset: 0,
      schemaInsertionOffset: 0,
    };

    const spec: BackendSpec = {
      endpoints: [],
      drizzleTableHints: [],
      backgroundJobs: [],
      mismatches: [],
    };

    const result = detectCollisions(inventory, spec);
    expect(result.valid).toBe(true);
    expect(result.collisions).toHaveLength(0);
  });
});
