import { readFile } from "fs/promises";
import { join } from "path";
import {
  BackendBrownfieldInventorySchema,
  type BackendBrownfieldInventory,
  type WiringValidationResult,
} from "./types.js";
import type { BackendSpec } from "./types.js";

// ─── Route Path Extraction ────────────────────────────────────────────────────

function extractRoutePaths(routesContent: string): string[] {
  const paths: string[] = [];
  // Matches: app.get("/api/...", or app.post("/api/...", etc.
  const routeRegex = /app\.(get|post|put|patch|delete)\("(\/api\/[^"]+)"/g;
  let match: RegExpExecArray | null;
  while ((match = routeRegex.exec(routesContent)) !== null) {
    paths.push(match[2]);
  }
  return paths;
}

// ─── Storage Function Extraction ─────────────────────────────────────────────

function extractStorageFunctions(storageContent: string): string[] {
  const functions: string[] = [];
  // Matches: async functionName( patterns within the class
  const funcRegex = /async (\w+)\s*\(/g;
  let match: RegExpExecArray | null;
  while ((match = funcRegex.exec(storageContent)) !== null) {
    functions.push(match[1]);
  }
  return functions;
}

// ─── Table Name Extraction ────────────────────────────────────────────────────

function extractTableNames(schemaContent: string): string[] {
  const tables: string[] = [];
  // Matches: pgTable("tableName", pattern
  const tableRegex = /pgTable\("([^"]+)"/g;
  let match: RegExpExecArray | null;
  while ((match = tableRegex.exec(schemaContent)) !== null) {
    tables.push(match[1]);
  }
  return tables;
}

// ─── Main Audit Function ──────────────────────────────────────────────────────

export async function auditBackendBrownfield(projectRoot: string): Promise<BackendBrownfieldInventory> {
  // Read the three backend source files
  const routesPath = join(projectRoot, "server", "routes.ts");
  const storagePath = join(projectRoot, "server", "storage.ts");
  const schemaPath = join(projectRoot, "shared", "schema.ts");

  let routesContent = "";
  let storageContent = "";
  let schemaContent = "";

  try {
    routesContent = await readFile(routesPath, "utf8");
  } catch {
    // routes.ts not found — empty inventory
  }

  try {
    storageContent = await readFile(storagePath, "utf8");
  } catch {
    // storage.ts not found
  }

  try {
    schemaContent = await readFile(schemaPath, "utf8");
  } catch {
    // schema.ts not found
  }

  // Extract existing route paths
  const existingRoutePaths = extractRoutePaths(routesContent);

  // Extract existing storage function names
  const existingStorageFunctions = extractStorageFunctions(storageContent);

  // Extract existing table names
  const existingTableNames = extractTableNames(schemaContent);

  // Find routes insertion offset — before createServer call
  const routesInsertionOffset = routesContent.indexOf("const httpServer = createServer(app)");

  // Find storage insertion offset — last closing brace of class
  const storageInsertionOffset = storageContent.lastIndexOf("}");

  // Schema insertion offset — append at end of file
  const schemaInsertionOffset = schemaContent.length;

  // Validate and return
  return BackendBrownfieldInventorySchema.parse({
    existingRoutePaths,
    existingStorageFunctions,
    existingTableNames,
    routesInsertionOffset,
    storageInsertionOffset,
    schemaInsertionOffset,
  });
}

// ─── Collision Detection ──────────────────────────────────────────────────────

export function detectCollisions(
  inventory: BackendBrownfieldInventory,
  spec: BackendSpec
): WiringValidationResult {
  const collisions: string[] = [];

  for (const endpoint of spec.endpoints) {
    const specPath = endpoint.path;

    // Exact match check
    if (inventory.existingRoutePaths.includes(specPath)) {
      collisions.push(`${endpoint.method} ${specPath} already exists in routes.ts`);
      continue;
    }

    // Check if the spec path matches an existing parameterized route pattern
    // e.g., /api/items matches /api/items/:id base path check
    // Strip trailing parameterized segment (/:id, /:name, etc.) for base comparison
    const specBase = specPath.replace(/\/:[^/]+$/, "");
    if (specBase !== specPath && inventory.existingRoutePaths.includes(specBase)) {
      // specPath is a parameterized variant of an existing route — not a collision
      // (different endpoints like GET /api/users and GET /api/users/:id are distinct)
    }
  }

  return {
    valid: collisions.length === 0,
    gaps: [], // gaps are checked at wiring plan generation time, not audit time (per plan spec)
    collisions,
  };
}
