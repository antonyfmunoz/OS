import { describe, it, expect } from "vitest";
import {
  BackendBrownfieldInventorySchema,
  RouteCodeBlockSchema,
  SchemaCodeBlockSchema,
  StorageCodeBlockSchema,
  HookInjectionSchema,
  WiringValidationResultSchema,
  BackendWiringPlanSchema,
} from "../../../lib/backend-wirer/types.js";

// ─── BackendBrownfieldInventorySchema ─────────────────────────────────────────

describe("BackendBrownfieldInventorySchema", () => {
  it("parses a valid inventory", () => {
    const valid = {
      existingRoutePaths: ["/api/users", "/api/agents"],
      existingStorageFunctions: ["getUser", "createAgent"],
      existingTableNames: ["users", "agents"],
      routesInsertionOffset: 1000,
      storageInsertionOffset: 500,
      schemaInsertionOffset: 200,
    };
    const result = BackendBrownfieldInventorySchema.safeParse(valid);
    expect(result.success).toBe(true);
  });

  it("rejects inventory missing required fields", () => {
    const invalid = {
      existingRoutePaths: ["/api/users"],
      // missing existingStorageFunctions, existingTableNames, etc.
    };
    const result = BackendBrownfieldInventorySchema.safeParse(invalid);
    expect(result.success).toBe(false);
  });

  it("rejects inventory with wrong types for offsets", () => {
    const invalid = {
      existingRoutePaths: [],
      existingStorageFunctions: [],
      existingTableNames: [],
      routesInsertionOffset: "not-a-number",
      storageInsertionOffset: 0,
      schemaInsertionOffset: 0,
    };
    const result = BackendBrownfieldInventorySchema.safeParse(invalid);
    expect(result.success).toBe(false);
  });
});

// ─── RouteCodeBlockSchema ─────────────────────────────────────────────────────

describe("RouteCodeBlockSchema", () => {
  it("parses a valid route code block", () => {
    const valid = {
      method: "GET",
      path: "/api/items",
      code: "app.get('/api/items', async (req, res) => { res.json([]); });",
    };
    const result = RouteCodeBlockSchema.safeParse(valid);
    expect(result.success).toBe(true);
  });

  it("parses a route block with optional zodSchemaCode", () => {
    const valid = {
      method: "POST",
      path: "/api/items",
      code: "app.post('/api/items', async (req, res) => { ... });",
      zodSchemaCode: "const createItemSchema = z.object({ name: z.string() });",
    };
    const result = RouteCodeBlockSchema.safeParse(valid);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.zodSchemaCode).toBeDefined();
    }
  });

  it("rejects route block missing required fields", () => {
    const invalid = {
      method: "GET",
      // missing path and code
    };
    const result = RouteCodeBlockSchema.safeParse(invalid);
    expect(result.success).toBe(false);
  });
});

// ─── SchemaCodeBlockSchema ────────────────────────────────────────────────────

describe("SchemaCodeBlockSchema", () => {
  it("parses a valid schema code block", () => {
    const valid = {
      tableName: "items",
      drizzleCode: "export const items = pgTable('items', { id: text('id').primaryKey() });",
      zodInsertCode: "export const insertItemSchema = createInsertSchema(items);",
      typeExportCode: "export type Item = typeof items.$inferSelect;",
    };
    const result = SchemaCodeBlockSchema.safeParse(valid);
    expect(result.success).toBe(true);
  });

  it("rejects schema block missing drizzleCode", () => {
    const invalid = {
      tableName: "items",
      // missing drizzleCode, zodInsertCode, typeExportCode
    };
    const result = SchemaCodeBlockSchema.safeParse(invalid);
    expect(result.success).toBe(false);
  });
});

// ─── StorageCodeBlockSchema ───────────────────────────────────────────────────

describe("StorageCodeBlockSchema", () => {
  it("parses a valid storage code block", () => {
    const valid = {
      functionName: "getItems",
      code: "async getItems(userId: string) { return db.select().from(itemsTable).where(eq(itemsTable.userId, userId)); }",
      tableName: "items",
    };
    const result = StorageCodeBlockSchema.safeParse(valid);
    expect(result.success).toBe(true);
  });

  it("rejects storage block with missing tableName", () => {
    const invalid = {
      functionName: "getItems",
      code: "async getItems() {}",
      // missing tableName
    };
    const result = StorageCodeBlockSchema.safeParse(invalid);
    expect(result.success).toBe(false);
  });
});

// ─── HookInjectionSchema ──────────────────────────────────────────────────────

describe("HookInjectionSchema", () => {
  it("parses a valid hook injection", () => {
    const valid = {
      pageFilePath: "client/src/pages/items-page.tsx",
      hookImport: "import { useQuery } from '@tanstack/react-query';",
      hookCode: "const { data: items } = useQuery({ queryKey: ['/api/items'] });",
      replacePattern: "const items = [];",
    };
    const result = HookInjectionSchema.safeParse(valid);
    expect(result.success).toBe(true);
  });

  it("rejects hook injection missing replacePattern", () => {
    const invalid = {
      pageFilePath: "client/src/pages/items-page.tsx",
      hookImport: "import { useQuery } from '@tanstack/react-query';",
      hookCode: "const { data } = useQuery(...);",
      // missing replacePattern
    };
    const result = HookInjectionSchema.safeParse(invalid);
    expect(result.success).toBe(false);
  });
});

// ─── WiringValidationResultSchema ────────────────────────────────────────────

describe("WiringValidationResultSchema", () => {
  it("parses a valid result with valid: true and empty arrays", () => {
    const valid = {
      valid: true,
      gaps: [],
      collisions: [],
    };
    const result = WiringValidationResultSchema.safeParse(valid);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.valid).toBe(true);
    }
  });

  it("parses a result with valid: false and populated collisions", () => {
    const invalid = {
      valid: false,
      gaps: ["items data requirement has no endpoint"],
      collisions: ["/api/users already exists"],
    };
    const result = WiringValidationResultSchema.safeParse(invalid);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.valid).toBe(false);
      expect(result.data.collisions).toHaveLength(1);
    }
  });

  it("rejects result missing valid boolean", () => {
    const invalid = {
      gaps: [],
      collisions: [],
      // missing valid
    };
    const result = WiringValidationResultSchema.safeParse(invalid);
    expect(result.success).toBe(false);
  });
});

// ─── BackendWiringPlanSchema ──────────────────────────────────────────────────

describe("BackendWiringPlanSchema", () => {
  it("parses a valid wiring plan with all arrays and validation result", () => {
    const valid = {
      newRoutes: [
        {
          method: "GET",
          path: "/api/items",
          code: "app.get('/api/items', ...)",
        },
      ],
      newSchemaBlocks: [
        {
          tableName: "items",
          drizzleCode: "export const items = pgTable(...);",
          zodInsertCode: "export const insertItemSchema = ...;",
          typeExportCode: "export type Item = ...;",
        },
      ],
      newStorageFunctions: [
        {
          functionName: "getItems",
          code: "async getItems() {}",
          tableName: "items",
        },
      ],
      hookInjections: [
        {
          pageFilePath: "client/src/pages/items-page.tsx",
          hookImport: "import { useQuery } from '@tanstack/react-query';",
          hookCode: "const { data } = useQuery(...);",
          replacePattern: "const items = [];",
        },
      ],
      validationResult: {
        valid: true,
        gaps: [],
        collisions: [],
      },
    };
    const result = BackendWiringPlanSchema.safeParse(valid);
    expect(result.success).toBe(true);
  });

  it("parses an empty wiring plan (valid with no new items)", () => {
    const empty = {
      newRoutes: [],
      newSchemaBlocks: [],
      newStorageFunctions: [],
      hookInjections: [],
      validationResult: {
        valid: true,
        gaps: [],
        collisions: [],
      },
    };
    const result = BackendWiringPlanSchema.safeParse(empty);
    expect(result.success).toBe(true);
  });

  it("rejects wiring plan missing validationResult", () => {
    const invalid = {
      newRoutes: [],
      newSchemaBlocks: [],
      newStorageFunctions: [],
      hookInjections: [],
      // missing validationResult
    };
    const result = BackendWiringPlanSchema.safeParse(invalid);
    expect(result.success).toBe(false);
  });
});
