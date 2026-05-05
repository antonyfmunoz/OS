import { writeFile, mkdir } from "fs/promises";
import { execSync } from "child_process";
import path from "path";

// ─── MIGRATION SCRIPT WRITER ──────────────────────────────────────────────────

/**
 * Write an idempotent DDL migration script to scripts/ matching the existing
 * scripts/setup-tables.ts pattern.
 * Per D-16, D-17 — uses tsx for execution, wraps SQL in db.execute(sql`...`).
 *
 * Returns the written file path.
 */
export async function writeMigrationScript(
  projectRoot: string,
  sql: string,
  slug: string
): Promise<string> {
  const date = new Date().toISOString().slice(0, 10); // YYYY-MM-DD
  const fileName = `phase5-migration-${date}-${slug}.ts`;
  const scriptsDir = path.join(projectRoot, "scripts");
  const filePath = path.join(scriptsDir, fileName);

  const content = generateMigrationScriptContent(sql);

  await mkdir(scriptsDir, { recursive: true });
  await writeFile(filePath, content, "utf-8");

  return filePath;
}

/**
 * Generate the TypeScript content for a migration script.
 * Matches the pattern in scripts/setup-tables.ts.
 */
function generateMigrationScriptContent(sql: string): string {
  return `import { db, client } from "../server/db.js";
import { sql } from "drizzle-orm";

async function runMigration() {
  try {
    await db.execute(sql\`
${sql}
    \`);
    console.log("Migration complete");
  } finally {
    await client.end();
  }
}

runMigration().catch((err) => {
  console.error(err);
  process.exit(1);
});
`;
}

// ─── MIGRATION RUNNER ─────────────────────────────────────────────────────────

/**
 * Execute a migration script via npx tsx.
 * Returns success/failure with combined stdout+stderr output.
 * Per D-17 — uses tsx for type-safe execution without pre-compilation.
 */
export async function runMigration(
  scriptPath: string,
  projectRoot: string
): Promise<{ success: boolean; output: string }> {
  try {
    const output = execSync(`npx tsx ${scriptPath}`, {
      cwd: projectRoot,
      encoding: "utf-8",
      stdio: ["pipe", "pipe", "pipe"],
    });
    return { success: true, output: output?.toString() ?? "Migration complete" };
  } catch (err: unknown) {
    const e = err as { message?: unknown; stdout?: { toString(): string }; stderr?: { toString(): string } };
    const output = [
      typeof e.message === "string" ? e.message : err instanceof Error ? err.message : String(err),
      e.stdout?.toString() ?? "",
      e.stderr?.toString() ?? "",
    ]
      .filter(Boolean)
      .join("\n");
    return { success: false, output };
  }
}
