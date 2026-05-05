import type { BackendEndpointSpec } from "@shared/spec-schema.js";
import type { BackendBrownfieldInventory, RouteCodeBlock, StorageCodeBlock } from "./types.js";

// ─── HELPERS ──────────────────────────────────────────────────────────────────

/**
 * Derive a resource name from a path segment.
 * "/api/widgets" -> "widgets"
 * "/api/user-profiles" -> "userProfiles"
 */
function pathToResource(path: string): string {
  // Strip query params and split
  const segments = path.split("/").filter(Boolean);
  // Find the last non-param segment
  const lastSegment = [...segments].reverse().find((s) => !s.startsWith(":")) ?? "items";
  // Convert kebab-case to camelCase
  return lastSegment.replace(/-([a-z])/g, (_, c: string) => c.toUpperCase());
}

/**
 * Capitalize first letter of a string.
 */
function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/**
 * Singularize a resource name for function naming.
 * "widgets" -> "Widget", "userProfiles" -> "UserProfile"
 */
function singularize(resource: string): string {
  const cap = capitalize(resource);
  if (cap.endsWith("ies")) return cap.slice(0, -3) + "y";
  if (cap.endsWith("ses") || cap.endsWith("xes") || cap.endsWith("zes")) return cap.slice(0, -2);
  if (cap.endsWith("s") && !cap.endsWith("ss")) return cap.slice(0, -1);
  return cap;
}

/**
 * Derive storage function name from endpoint method + path.
 * GET /api/widgets -> getWidgets
 * POST /api/widgets -> createWidget
 * PUT/PATCH /api/widgets/:id -> updateWidget
 * DELETE /api/widgets/:id -> deleteWidget
 */
function deriveStorageFunctionName(endpoint: BackendEndpointSpec): string {
  const resource = pathToResource(endpoint.path);
  const single = singularize(resource);
  switch (endpoint.method) {
    case "GET":
      return `get${capitalize(resource)}`;
    case "POST":
      return `create${single}`;
    case "PUT":
    case "PATCH":
      return `update${single}`;
    case "DELETE":
      return `delete${single}`;
    default:
      return `handle${capitalize(resource)}`;
  }
}

// ─── ROUTE CODE GENERATOR ─────────────────────────────────────────────────────

/**
 * Generate an Express route handler code block matching the existing routes.ts pattern.
 * Per D-06, D-08, D-09 — appends to routes.ts without refactoring.
 */
export function generateRouteCode(
  endpoint: BackendEndpointSpec,
  inventory: BackendBrownfieldInventory
): RouteCodeBlock {
  const method = endpoint.method.toLowerCase();
  const functionName = deriveStorageFunctionName(endpoint);
  const resource = pathToResource(endpoint.path);
  const hasBody = ["POST", "PUT", "PATCH"].includes(endpoint.method) && endpoint.requestBody.length > 0;

  // Bug 2: if inventory lists real storage methods and this endpoint's derived
  // name is not among them, emit a 501 TODO placeholder instead of a broken
  // call to a method that does not exist on the real storage class.
  const realMethods = inventory.existingStorageFunctions;
  const methodIsReal =
    realMethods.length === 0 || realMethods.includes(functionName);
  if (!methodIsReal) {
    const todoLines = [
      `app.${method}("${endpoint.path}", async (_req: Request, res: Response) => {`,
      `  // TODO: implement storage.${functionName} — no matching method exists on the real storage interface`,
      `  res.status(501).json({ message: "Not implemented: storage.${functionName}" });`,
      `});`,
    ];
    return {
      method,
      path: endpoint.path,
      code: todoLines.join("\n"),
      zodSchemaCode: undefined,
    };
  }

  const lines: string[] = [];

  lines.push(`app.${method}("${endpoint.path}", async (req: Request, res: Response) => {`);

  // Auth check
  if (endpoint.authRequired) {
    lines.push(`  if (!req.isAuthenticated()) return res.status(401).json({ message: "Not authenticated" });`);
  }

  lines.push(`  try {`);

  if (endpoint.authRequired) {
    lines.push(`    const userId = (req.user as { id: string }).id;`);
  }

  // Method-specific logic
  if (endpoint.method === "GET") {
    const companyParam = endpoint.authRequired ? "userId" : "";
    lines.push(`    const data = await storage.${functionName}(${companyParam});`);
    lines.push(`    res.json(data);`);
  } else if (endpoint.method === "POST") {
    if (hasBody) {
      const schemaName = `insert${singularize(resource)}Schema`;
      lines.push(`    const parsed = ${schemaName}.safeParse(req.body);`);
      lines.push(`    if (!parsed.success) return res.status(400).json({ message: parsed.error.issues[0].message });`);
      lines.push(`    const created = await storage.${functionName}(parsed.data);`);
      lines.push(`    res.status(201).json(created);`);
    } else {
      lines.push(`    const created = await storage.${functionName}(req.body);`);
      lines.push(`    res.status(201).json(created);`);
    }
  } else if (endpoint.method === "PUT" || endpoint.method === "PATCH") {
    if (hasBody) {
      const schemaName = `insert${singularize(resource)}Schema`;
      lines.push(`    const parsed = ${schemaName}.safeParse(req.body);`);
      lines.push(`    if (!parsed.success) return res.status(400).json({ message: parsed.error.issues[0].message });`);
      const userArg = endpoint.authRequired ? ", userId" : "";
      lines.push(`    const updated = await storage.${functionName}(req.params.id, parsed.data${userArg});`);
      lines.push(`    res.json(updated);`);
    } else {
      const userArg = endpoint.authRequired ? ", userId" : "";
      lines.push(`    const updated = await storage.${functionName}(req.params.id, req.body${userArg});`);
      lines.push(`    res.json(updated);`);
    }
  } else if (endpoint.method === "DELETE") {
    const userArg = endpoint.authRequired ? ", userId" : "";
    lines.push(`    await storage.${functionName}(req.params.id${userArg});`);
    lines.push(`    res.status(204).end();`);
  }

  lines.push(`  } catch (error: any) {`);
  lines.push(`    res.status(500).json({ message: error.message });`);
  lines.push(`  }`);
  lines.push(`});`);

  const code = lines.join("\n");

  // Optional inline Zod schema for POST/PUT/PATCH with body
  let zodSchemaCode: string | undefined;
  if (hasBody) {
    const schemaName = `insert${singularize(resource)}Schema`;
    const fields = endpoint.requestBody.map((f) => `  ${f}: z.string()`).join(",\n");
    zodSchemaCode = `const ${schemaName} = z.object({\n${fields},\n});`;
  }

  return {
    method,
    path: endpoint.path,
    code,
    zodSchemaCode,
  };
}

// ─── STORAGE CODE GENERATOR ───────────────────────────────────────────────────

/**
 * Generate a storage class method code block matching the existing storage.ts pattern.
 * Per D-07 — appends method inside the storage class.
 */
export function generateStorageCode(endpoint: BackendEndpointSpec): StorageCodeBlock {
  const resource = pathToResource(endpoint.path);
  const functionName = deriveStorageFunctionName(endpoint);
  const single = singularize(resource);
  const tableName = resource;
  // Generated Drizzle tables in shared/schema.ts are exported with the
  // plain resource name (no "Table" suffix) — match that export exactly.
  const tableVar = resource;

  let code: string;

  switch (endpoint.method) {
    case "GET":
      code = [
        `  async ${functionName}(companyId: string): Promise<${single}[]> {`,
        `    return db.select().from(${tableVar}).where(eq(${tableVar}.companyId, companyId));`,
        `  }`,
      ].join("\n");
      break;

    case "POST":
      code = [
        `  async ${functionName}(data: Insert${single}): Promise<${single}> {`,
        `    const id = crypto.randomUUID();`,
        `    const [created] = await db.insert(${tableVar}).values({ id, ...data }).returning();`,
        `    return created;`,
        `  }`,
      ].join("\n");
      break;

    case "PUT":
    case "PATCH":
      code = [
        `  async ${functionName}(id: string, data: Partial<Insert${single}>, userId: string): Promise<${single}> {`,
        `    const [updated] = await db.update(${tableVar}).set({ ...data, updatedAt: new Date() }).where(eq(${tableVar}.id, id)).returning();`,
        `    return updated;`,
        `  }`,
      ].join("\n");
      break;

    case "DELETE":
      code = [
        `  async ${functionName}(id: string, userId: string): Promise<void> {`,
        `    await db.delete(${tableVar}).where(eq(${tableVar}.id, id));`,
        `  }`,
      ].join("\n");
      break;

    default:
      throw new Error(`Unknown HTTP method: ${endpoint.method}`);
  }

  return {
    functionName,
    code,
    tableName,
  };
}
