import type { SchemaCodeBlock } from "./types.js";

// ─── HELPERS ──────────────────────────────────────────────────────────────────

/**
 * Convert camelCase or snake_case string to PascalCase.
 * "widgets" -> "Widget", "userProfiles" -> "UserProfile"
 */
function toPascalCase(str: string): string {
  // Handle snake_case
  const camel = str.replace(/_([a-z])/g, (_, c: string) => c.toUpperCase());
  // Capitalize first letter then singularize
  const upper = camel.charAt(0).toUpperCase() + camel.slice(1);
  return singularizePascal(upper);
}

/**
 * Singularize a PascalCase resource name.
 * "Widgets" -> "Widget", "UserProfiles" -> "UserProfile"
 */
function singularizePascal(name: string): string {
  if (name.endsWith("ies")) return name.slice(0, -3) + "y";
  if (name.endsWith("ses") || name.endsWith("xes") || name.endsWith("zes")) return name.slice(0, -2);
  if (name.endsWith("s") && !name.endsWith("ss")) return name.slice(0, -1);
  return name;
}

/**
 * Convert camelCase field name to snake_case column name.
 * "companyId" -> "company_id", "createdAt" -> "created_at"
 */
function toSnakeCase(str: string): string {
  return str.replace(/([A-Z])/g, (_, c: string) => `_${c.toLowerCase()}`);
}

/**
 * Standard columns always present in generated tables.
 */
const STANDARD_COLUMNS = ["id", "companyId", "createdAt", "updatedAt"];

// ─── SCHEMA CODE GENERATOR ────────────────────────────────────────────────────

/**
 * Generate Drizzle table definition, Zod insert schema, and type exports
 * from a table name and field list.
 * Per D-15 — matches the pattern in shared/schema.ts exactly.
 */
export function generateSchemaCode(tableName: string, fields: string[]): SchemaCodeBlock {
  const pascalName = toPascalCase(tableName);

  // Deduplicate fields — remove any that match standard columns
  const customFields = fields.filter(
    (f) => !STANDARD_COLUMNS.map((c) => c.toLowerCase()).includes(f.toLowerCase())
  );

  // ─── Drizzle table code ───────────────────────────────────────────────────
  const customColumnLines = customFields.map((field) => {
    const colName = toSnakeCase(field);
    return `  ${field}: text("${colName}"),`;
  });

  const drizzleLines = [
    `export const ${tableName} = pgTable("${tableName}", {`,
    `  id: text("id").primaryKey(),`,
    ...customColumnLines,
    `  companyId: text("company_id").notNull(),`,
    `  createdAt: timestamp("created_at").defaultNow(),`,
    `  updatedAt: timestamp("updated_at").defaultNow(),`,
    `});`,
  ];
  const drizzleCode = drizzleLines.join("\n");

  // ─── Zod insert schema code ───────────────────────────────────────────────
  const zodFieldLines = [
    ...customFields.map((f) => `  ${f}: z.string(),`),
    `  companyId: z.string().min(1),`,
  ];

  const zodLines = [
    `export const insert${pascalName}Schema = z.object({`,
    ...zodFieldLines,
    `});`,
  ];
  const zodInsertCode = zodLines.join("\n");

  // ─── Type export code ─────────────────────────────────────────────────────
  const typeExportCode = [
    `export type ${pascalName} = typeof ${tableName}.$inferSelect;`,
    `export type Insert${pascalName} = z.infer<typeof insert${pascalName}Schema>;`,
  ].join("\n");

  return {
    tableName,
    drizzleCode,
    zodInsertCode,
    typeExportCode,
  };
}

// ─── MIGRATION SQL GENERATOR ──────────────────────────────────────────────────

/**
 * Generate idempotent DDL SQL for creating tables from schema code blocks.
 * Per D-16, D-17 — uses CREATE TABLE IF NOT EXISTS.
 * Tables are ordered alphabetically (v1 — no FK dependencies generated).
 */
export function generateMigrationSQL(blocks: SchemaCodeBlock[]): string {
  // Sort alphabetically for deterministic ordering
  const sorted = [...blocks].sort((a, b) => a.tableName.localeCompare(b.tableName));

  const statements = sorted.map((block) => {
    // Parse fields from the drizzle code to generate SQL columns
    // We regenerate the columns from the block's drizzleCode by extracting field patterns
    const columnDefs = extractColumnDefs(block.drizzleCode);
    return [
      `CREATE TABLE IF NOT EXISTS "${block.tableName}" (`,
      columnDefs.map((col) => `  ${col}`).join(",\n"),
      `);`,
    ].join("\n");
  });

  return statements.join("\n\n");
}

/**
 * Extract SQL column definitions from generated drizzle code.
 * Parses the drizzle text to produce SQL-compatible column definitions.
 */
function extractColumnDefs(drizzleCode: string): string[] {
  const cols: string[] = [];

  // Always start with primary key
  cols.push('"id" text PRIMARY KEY');

  // Extract custom fields — lines like: `  fieldName: text("col_name"),`
  const fieldRegex = /^\s+(\w+):\s+text\("([^"]+)"\)(?:\.notNull\(\))?(?:\.defaultNow\(\))?,/gm;
  let match: RegExpExecArray | null;

  while ((match = fieldRegex.exec(drizzleCode)) !== null) {
    const [, fieldName, colName] = match;
    // Skip standard columns — handle separately
    if (["id", "company_id", "created_at", "updated_at"].includes(colName)) continue;
    cols.push(`"${colName}" text`);
  }

  // Standard trailing columns
  cols.push('"company_id" text NOT NULL');
  cols.push('"created_at" timestamp DEFAULT now()');
  cols.push('"updated_at" timestamp DEFAULT now()');

  return cols;
}
