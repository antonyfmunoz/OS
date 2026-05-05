import { readFile, writeFile } from "fs/promises";
import { join } from "path";
import type { BackendWiringPlan, BackendBrownfieldInventory } from "./types.js";

// ─── Result Type ──────────────────────────────────────────────────────────────

export interface WiringApplyResult {
  filesModified: string[];
  routesAdded: number;
  schemaTablesAdded: number;
  storageFunctionsAdded: number;
  hooksInjected: number;
}

// ─── Main Entry Point ─────────────────────────────────────────────────────────

/**
 * Applies a BackendWiringPlan to the target project files.
 *
 * Execution order (per RESEARCH.md decisions):
 *   1. Validate — reject if collisions or gaps detected (D-03)
 *   2. Schema blocks — appended to shared/schema.ts (D-15; must precede routes/storage)
 *   3. Storage functions — inserted before closing brace of class in server/storage.ts (D-07)
 *   4. Route blocks — inserted before createServer(app) in server/routes.ts (D-06, D-08)
 *   5. Hook injections — import added and hook code inserted into page files (D-02)
 *
 * Each target file is read once, all insertions applied in-memory, then written once.
 * Insertions within a single file are applied highest-offset-first to preserve earlier offsets.
 */
export async function applyWiringPlan(
  projectRoot: string,
  plan: BackendWiringPlan,
  inventory: BackendBrownfieldInventory,
): Promise<WiringApplyResult> {
  // ── Step 1: Validate ───────────────────────────────────────────────────────
  if (!plan.validationResult.valid) {
    const details: string[] = [];
    if (plan.validationResult.collisions.length > 0) {
      details.push(`Collisions: ${plan.validationResult.collisions.join(", ")}`);
    }
    if (plan.validationResult.gaps.length > 0) {
      details.push(`Gaps: ${plan.validationResult.gaps.join(", ")}`);
    }
    throw new Error(
      `Wiring plan validation failed — cannot apply. ${details.join(". ")}`,
    );
  }

  // Early exit if nothing to do
  const hasRoutes = plan.newRoutes.length > 0;
  const hasSchema = plan.newSchemaBlocks.length > 0;
  const hasStorage = plan.newStorageFunctions.length > 0;
  const hasHooks = plan.hookInjections.length > 0;

  if (!hasRoutes && !hasSchema && !hasStorage && !hasHooks) {
    return {
      filesModified: [],
      routesAdded: 0,
      schemaTablesAdded: 0,
      storageFunctionsAdded: 0,
      hooksInjected: 0,
    };
  }

  const filesModified: string[] = [];
  // Normalize path separator to forward slashes for cross-platform consistency
  const toForwardSlash = (p: string) => p.replace(/\\/g, "/");

  // ── Step 2: Read all 3 core files up front (single read per file) ──────────
  const routesPath = join(projectRoot, "server", "routes.ts");
  const storagePath = join(projectRoot, "server", "storage.ts");
  const schemaPath = join(projectRoot, "shared", "schema.ts");

  let routesContent = await readFile(routesPath, "utf-8");
  let storageContent = await readFile(storagePath, "utf-8");
  let schemaContent = await readFile(schemaPath, "utf-8");

  // ── Step 3: Apply schema blocks (D-15 — append to end of schema.ts) ────────
  if (hasSchema) {
    for (const block of plan.newSchemaBlocks) {
      const codeToAppend =
        "\n\n" +
        block.drizzleCode +
        "\n\n" +
        block.zodInsertCode +
        "\n\n" +
        block.typeExportCode;
      schemaContent =
        schemaContent.slice(0, inventory.schemaInsertionOffset) +
        codeToAppend +
        schemaContent.slice(inventory.schemaInsertionOffset);
    }
    await writeFile(schemaPath, schemaContent, "utf-8");
    filesModified.push(toForwardSlash(schemaPath));
  }

  // ── Step 4: Apply storage functions (D-07 — before closing brace of class) ─
  if (hasStorage) {
    let offset = inventory.storageInsertionOffset;
    // Apply in reverse order (highest offset first) so prior offsets remain valid.
    // All storage functions share the same insertion point (before closing brace),
    // so we insert them in order but track the growing offset.
    for (const block of plan.newStorageFunctions) {
      const codeToInsert = "\n\n  " + block.code + "\n";
      storageContent =
        storageContent.slice(0, offset) +
        codeToInsert +
        storageContent.slice(offset);
      // Advance offset past newly inserted code so next function goes after this one
      offset += codeToInsert.length;
    }
    await writeFile(storagePath, storageContent, "utf-8");
    filesModified.push(toForwardSlash(storagePath));
  }

  // ── Step 5: Apply route blocks (D-06, D-08 — before createServer(app)) ─────
  if (hasRoutes) {
    if (inventory.routesInsertionOffset === -1) {
      throw new Error(
        "Cannot find createServer(app) anchor in routes.ts — routes insertion aborted",
      );
    }

    let offset = inventory.routesInsertionOffset;
    for (const block of plan.newRoutes) {
      // Prepend inline Zod schema code before the route handler if present
      const routeSection =
        (block.zodSchemaCode ? "\n\n" + block.zodSchemaCode + "\n" : "\n\n") +
        block.code +
        "\n";
      routesContent =
        routesContent.slice(0, offset) +
        routeSection +
        routesContent.slice(offset);
      // Advance offset so next route goes after this one (before anchor)
      offset += routeSection.length;
    }
    await writeFile(routesPath, routesContent, "utf-8");
    filesModified.push(toForwardSlash(routesPath));
  }

  // ── Step 6: Apply hook injections (D-02 — imports + hook code in page files)
  let hooksApplied = 0;
  if (hasHooks) {
    for (const injection of plan.hookInjections) {
      let pageContent = await readFile(injection.pageFilePath, "utf-8");

      // Add hookImport after the last import statement in the file
      const lastImportIndex = pageContent.lastIndexOf("\nimport ");
      if (lastImportIndex !== -1) {
        const endOfLastImport = pageContent.indexOf("\n", lastImportIndex + 1);
        const insertAfter = endOfLastImport !== -1 ? endOfLastImport + 1 : pageContent.length;
        pageContent =
          pageContent.slice(0, insertAfter) +
          injection.hookImport +
          "\n" +
          pageContent.slice(insertAfter);
      } else {
        // No imports found — prepend at top
        pageContent = injection.hookImport + "\n" + pageContent;
      }

      // Insert hookCode after the opening "{" of the component function body.
      // Pattern: find the first "{" that comes after "export default function" or "function"
      const fnBodyOpenIdx = findComponentBodyOpen(pageContent);
      if (fnBodyOpenIdx !== -1) {
        pageContent =
          pageContent.slice(0, fnBodyOpenIdx + 1) +
          "\n" +
          injection.hookCode +
          pageContent.slice(fnBodyOpenIdx + 1);
      }

      await writeFile(injection.pageFilePath, pageContent, "utf-8");
      filesModified.push(toForwardSlash(injection.pageFilePath));
      hooksApplied++;
    }
  }

  return {
    filesModified,
    routesAdded: plan.newRoutes.length,
    schemaTablesAdded: plan.newSchemaBlocks.length,
    storageFunctionsAdded: plan.newStorageFunctions.length,
    hooksInjected: hooksApplied,
  };
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

/**
 * Finds the index of the opening "{" of the first function/arrow component body
 * that appears after "export default function" or "function " declarations.
 * Returns -1 if no component function body is found.
 */
function findComponentBodyOpen(content: string): number {
  // Find the export default function or function declaration
  const exportDefaultIdx = content.indexOf("export default function");
  const functionIdx = content.indexOf("function ", exportDefaultIdx !== -1 ? exportDefaultIdx : 0);

  const startFrom = exportDefaultIdx !== -1 ? exportDefaultIdx : functionIdx;
  if (startFrom === -1) return -1;

  // Find the closing ")" of the parameter list first, then the "{"
  let depth = 0;
  let inParams = false;
  for (let i = startFrom; i < content.length; i++) {
    const ch = content[i];
    if (ch === "(" && !inParams) {
      inParams = true;
      depth = 1;
      continue;
    }
    if (inParams) {
      if (ch === "(") depth++;
      else if (ch === ")") {
        depth--;
        if (depth === 0) {
          inParams = false;
        }
      }
      continue;
    }
    // After params are closed, find the opening "{"
    if (!inParams && ch === "{") {
      return i;
    }
  }
  return -1;
}
