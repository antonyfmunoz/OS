import { describe, it, expect, vi, beforeEach } from "vitest";
import type {
  BackendWiringPlan,
  BackendBrownfieldInventory,
} from "../../../lib/backend-wirer/types.js";

// Mock fs/promises before importing the module
vi.mock("fs/promises", () => ({
  readFile: vi.fn(),
  writeFile: vi.fn(),
}));

import { readFile, writeFile } from "fs/promises";
import { applyWiringPlan } from "../../../lib/backend-wirer/wiring-applier.js";

const mockReadFile = vi.mocked(readFile);
const mockWriteFile = vi.mocked(writeFile);

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const validPlan: BackendWiringPlan = {
  newRoutes: [],
  newSchemaBlocks: [],
  newStorageFunctions: [],
  hookInjections: [],
  validationResult: { valid: true, gaps: [], collisions: [] },
};

const inventoryWithOffsets: BackendBrownfieldInventory = {
  existingRoutePaths: [],
  existingStorageFunctions: [],
  existingTableNames: [],
  routesInsertionOffset: 100,
  storageInsertionOffset: 80,
  schemaInsertionOffset: 120,
};

// routes.ts content sample — "const httpServer = createServer(app);" at offset 100
const ROUTES_BEFORE = "// routes header\n\nexport function registerRoutes(app: Express): Server {\n\n  app.get('/api/existing', () => {});\n\n";
const ROUTES_ANCHOR = "  const httpServer = createServer(app);\n  return httpServer;\n}";
const ROUTES_CONTENT = ROUTES_BEFORE + ROUTES_ANCHOR;

// storage.ts content sample — closing "}" at offset 80
const STORAGE_BEFORE = "export class DatabaseStorage {\n  async getExisting(): Promise<void> {\n    return;\n  }\n";
const STORAGE_TAIL = "}\n\nexport const storage = new DatabaseStorage();";
const STORAGE_CONTENT = STORAGE_BEFORE + STORAGE_TAIL;

// schema.ts content sample — end-of-file at offset 120
const SCHEMA_CONTENT = "import { pgTable } from 'drizzle-orm/pg-core';\n\nexport const users = pgTable('users', {});\n";

// page file content sample
const PAGE_CONTENT = `import React from 'react';
import { useQuery } from '@tanstack/react-query';

export default function WidgetsPage() {
  return <div>Widgets</div>;
}
`;

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("applyWiringPlan", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockWriteFile.mockResolvedValue(undefined);
  });

  it("throws when validationResult.valid is false", async () => {
    const invalidPlan: BackendWiringPlan = {
      ...validPlan,
      validationResult: {
        valid: false,
        gaps: ["missing /api/widgets endpoint"],
        collisions: ["/api/users already exists"],
      },
    };

    await expect(
      applyWiringPlan("/project", invalidPlan, inventoryWithOffsets)
    ).rejects.toThrow(/collision/i);
  });

  it("throws when validationResult.valid is false and includes gap details", async () => {
    const invalidPlan: BackendWiringPlan = {
      ...validPlan,
      validationResult: {
        valid: false,
        gaps: ["missing /api/items"],
        collisions: [],
      },
    };

    await expect(
      applyWiringPlan("/project", invalidPlan, inventoryWithOffsets)
    ).rejects.toThrow(/missing \/api\/items/);
  });

  it("inserts route code before createServer anchor at correct offset", async () => {
    const routesInsertionOffset = ROUTES_BEFORE.length;
    const inventory: BackendBrownfieldInventory = {
      ...inventoryWithOffsets,
      routesInsertionOffset,
      storageInsertionOffset: STORAGE_BEFORE.length,
      schemaInsertionOffset: SCHEMA_CONTENT.length,
    };

    const routeCode = `  app.get('/api/widgets', async (req, res) => { res.json([]); });`;
    const planWithRoute: BackendWiringPlan = {
      ...validPlan,
      newRoutes: [
        { method: "get", path: "/api/widgets", code: routeCode },
      ],
    };

    mockReadFile
      .mockResolvedValueOnce(ROUTES_BEFORE + ROUTES_ANCHOR) // routes.ts
      .mockResolvedValueOnce(STORAGE_CONTENT)               // storage.ts
      .mockResolvedValueOnce(SCHEMA_CONTENT);               // schema.ts

    await applyWiringPlan("/project", planWithRoute, inventory);

    const routesWriteCall = mockWriteFile.mock.calls.find(
      (call) => String(call[0]).includes("routes.ts")
    );
    expect(routesWriteCall).toBeDefined();
    const writtenContent = routesWriteCall![1] as string;
    expect(writtenContent).toContain("/api/widgets");
    // Route should appear before createServer anchor
    const routeIdx = writtenContent.indexOf("/api/widgets");
    const serverIdx = writtenContent.indexOf("createServer(app)");
    expect(routeIdx).toBeLessThan(serverIdx);
  });

  it("appends schema code at end of schema content", async () => {
    const schemaInsertionOffset = SCHEMA_CONTENT.length;
    const inventory: BackendBrownfieldInventory = {
      ...inventoryWithOffsets,
      schemaInsertionOffset,
      routesInsertionOffset: ROUTES_BEFORE.length,
      storageInsertionOffset: STORAGE_BEFORE.length,
    };

    const planWithSchema: BackendWiringPlan = {
      ...validPlan,
      newSchemaBlocks: [
        {
          tableName: "widgets",
          drizzleCode: "export const widgets = pgTable('widgets', { id: text('id').primaryKey() });",
          zodInsertCode: "export const insertWidgetSchema = z.object({ id: z.string() });",
          typeExportCode: "export type InsertWidget = z.infer<typeof insertWidgetSchema>;",
        },
      ],
    };

    mockReadFile
      .mockResolvedValueOnce(ROUTES_BEFORE + ROUTES_ANCHOR) // routes.ts
      .mockResolvedValueOnce(STORAGE_CONTENT)               // storage.ts
      .mockResolvedValueOnce(SCHEMA_CONTENT);               // schema.ts

    await applyWiringPlan("/project", planWithSchema, inventory);

    const schemaWriteCall = mockWriteFile.mock.calls.find(
      (call) => String(call[0]).includes("schema.ts")
    );
    expect(schemaWriteCall).toBeDefined();
    const writtenContent = schemaWriteCall![1] as string;
    // Appended schema code should come after original content
    expect(writtenContent).toContain(SCHEMA_CONTENT.trimEnd());
    expect(writtenContent).toContain("widgets");
    expect(writtenContent).toContain("insertWidgetSchema");
    expect(writtenContent).toContain("InsertWidget");
  });

  it("inserts storage function before closing brace at correct offset", async () => {
    const storageInsertionOffset = STORAGE_BEFORE.length;
    const inventory: BackendBrownfieldInventory = {
      ...inventoryWithOffsets,
      storageInsertionOffset,
      routesInsertionOffset: ROUTES_BEFORE.length,
      schemaInsertionOffset: SCHEMA_CONTENT.length,
    };

    const storageFunc = `async getWidgets(userId: string): Promise<any[]> {\n    return db.select().from(widgetsTable).where(eq(widgetsTable.userId, userId));\n  }`;
    const planWithStorage: BackendWiringPlan = {
      ...validPlan,
      newStorageFunctions: [
        { functionName: "getWidgets", code: storageFunc, tableName: "widgets" },
      ],
    };

    mockReadFile
      .mockResolvedValueOnce(ROUTES_BEFORE + ROUTES_ANCHOR) // routes.ts
      .mockResolvedValueOnce(STORAGE_CONTENT)               // storage.ts
      .mockResolvedValueOnce(SCHEMA_CONTENT);               // schema.ts

    await applyWiringPlan("/project", planWithStorage, inventory);

    const storageWriteCall = mockWriteFile.mock.calls.find(
      (call) => String(call[0]).includes("storage.ts")
    );
    expect(storageWriteCall).toBeDefined();
    const writtenContent = storageWriteCall![1] as string;
    expect(writtenContent).toContain("getWidgets");
    // Storage function should appear before "export const storage"
    const fnIdx = writtenContent.indexOf("getWidgets");
    const exportIdx = writtenContent.indexOf("export const storage");
    expect(fnIdx).toBeLessThan(exportIdx);
  });

  it("adds hook import and hook code to page file content", async () => {
    const inventory: BackendBrownfieldInventory = {
      ...inventoryWithOffsets,
      routesInsertionOffset: ROUTES_BEFORE.length,
      storageInsertionOffset: STORAGE_BEFORE.length,
      schemaInsertionOffset: SCHEMA_CONTENT.length,
    };

    const pageFilePath = "/project/client/src/pages/widgets-page.tsx";
    const planWithHook: BackendWiringPlan = {
      ...validPlan,
      hookInjections: [
        {
          pageFilePath,
          hookImport: "import { useWidgets } from '@/hooks/use-widgets';",
          hookCode: "  const { data: widgets } = useWidgets();",
          replacePattern: "export default function WidgetsPage()",
        },
      ],
    };

    mockReadFile
      .mockResolvedValueOnce(ROUTES_BEFORE + ROUTES_ANCHOR) // routes.ts
      .mockResolvedValueOnce(STORAGE_CONTENT)               // storage.ts
      .mockResolvedValueOnce(SCHEMA_CONTENT)                // schema.ts
      .mockResolvedValueOnce(PAGE_CONTENT);                 // page file

    await applyWiringPlan("/project", planWithHook, inventory);

    const pageWriteCall = mockWriteFile.mock.calls.find(
      (call) => String(call[0]) === pageFilePath
    );
    expect(pageWriteCall).toBeDefined();
    const writtenContent = pageWriteCall![1] as string;
    expect(writtenContent).toContain("useWidgets");
    expect(writtenContent).toContain("import { useWidgets }");
    expect(writtenContent).toContain("const { data: widgets } = useWidgets()");
    // Hook import should appear before the component
    const importIdx = writtenContent.indexOf("import { useWidgets }");
    const componentIdx = writtenContent.indexOf("export default function");
    expect(importIdx).toBeLessThan(componentIdx);
  });

  it("throws when routesInsertionOffset is -1", async () => {
    const inventoryNegative: BackendBrownfieldInventory = {
      ...inventoryWithOffsets,
      routesInsertionOffset: -1,
    };

    const planWithRoute: BackendWiringPlan = {
      ...validPlan,
      newRoutes: [
        { method: "get", path: "/api/test", code: `app.get('/api/test', (req, res) => res.json({}));` },
      ],
    };

    mockReadFile
      .mockResolvedValueOnce(ROUTES_BEFORE + ROUTES_ANCHOR) // routes.ts
      .mockResolvedValueOnce(STORAGE_CONTENT)               // storage.ts
      .mockResolvedValueOnce(SCHEMA_CONTENT);               // schema.ts

    await expect(
      applyWiringPlan("/project", planWithRoute, inventoryNegative)
    ).rejects.toThrow(/createServer.*anchor/i);
  });

  it("returns correct WiringApplyResult with file counts", async () => {
    const inventory: BackendBrownfieldInventory = {
      ...inventoryWithOffsets,
      routesInsertionOffset: ROUTES_BEFORE.length,
      storageInsertionOffset: STORAGE_BEFORE.length,
      schemaInsertionOffset: SCHEMA_CONTENT.length,
    };

    const pageFilePath = "/project/client/src/pages/items-page.tsx";
    const plan: BackendWiringPlan = {
      validationResult: { valid: true, gaps: [], collisions: [] },
      newRoutes: [
        { method: "get", path: "/api/items", code: `app.get('/api/items', (req, res) => res.json([]));` },
      ],
      newSchemaBlocks: [
        {
          tableName: "items",
          drizzleCode: "export const items = pgTable('items', {});",
          zodInsertCode: "export const insertItemSchema = z.object({});",
          typeExportCode: "export type InsertItem = z.infer<typeof insertItemSchema>;",
        },
      ],
      newStorageFunctions: [
        {
          functionName: "getItems",
          code: `async getItems(): Promise<any[]> { return []; }`,
          tableName: "items",
        },
      ],
      hookInjections: [
        {
          pageFilePath,
          hookImport: "import { useItems } from '@/hooks/use-items';",
          hookCode: "  const { data: items } = useItems();",
          replacePattern: "export default function ItemsPage()",
        },
      ],
    };

    mockReadFile
      .mockResolvedValueOnce(ROUTES_BEFORE + ROUTES_ANCHOR) // routes.ts
      .mockResolvedValueOnce(STORAGE_CONTENT)               // storage.ts
      .mockResolvedValueOnce(SCHEMA_CONTENT)                // schema.ts
      .mockResolvedValueOnce(PAGE_CONTENT);                 // page file

    const result = await applyWiringPlan("/project", plan, inventory);

    expect(result.routesAdded).toBe(1);
    expect(result.schemaTablesAdded).toBe(1);
    expect(result.storageFunctionsAdded).toBe(1);
    expect(result.hooksInjected).toBe(1);
    expect(result.filesModified).toContain("/project/server/routes.ts");
    expect(result.filesModified).toContain("/project/server/storage.ts");
    expect(result.filesModified).toContain("/project/shared/schema.ts");
    expect(result.filesModified).toContain(pageFilePath);
  });

  it("empty plan returns empty result without writing files", async () => {
    const emptyPlan: BackendWiringPlan = {
      ...validPlan,
      newRoutes: [],
      newSchemaBlocks: [],
      newStorageFunctions: [],
      hookInjections: [],
    };

    const result = await applyWiringPlan("/project", emptyPlan, inventoryWithOffsets);

    expect(result.routesAdded).toBe(0);
    expect(result.schemaTablesAdded).toBe(0);
    expect(result.storageFunctionsAdded).toBe(0);
    expect(result.hooksInjected).toBe(0);
    expect(result.filesModified).toHaveLength(0);
    expect(mockWriteFile).not.toHaveBeenCalled();
  });
});
