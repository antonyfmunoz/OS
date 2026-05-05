// lib/agents/backend-agent.ts
// Backend agent — generates Express route handlers, storage methods, and Drizzle
// table schemas from the SystemArchitecture's dataModel and apiContracts.
// Writes generated code to server/generated/ and migration SQL to
// .planning/output/migrations/.

import fs from "node:fs";
import path from "node:path";
import Anthropic from "@anthropic-ai/sdk";
import { getAnthropicApiKey, getAnthropicBaseUrl } from "../env.js";
import { extractJsonFromResponse } from "../spec-parser/restructure-spec.js";
import { generateSchemaCode, generateMigrationSQL } from "../backend-wirer/schema-generator.js";
import { generateRouteCode, generateStorageCode } from "../backend-wirer/route-generator.js";
import { runTscCheck } from "../react-gen/component-writer.js";
import { ArtifactStore } from "./artifact-store.js";
import type { SystemArchitecture, ApiContract, BackendRoute } from "./types.js";
import type { BackendBrownfieldInventory } from "../backend-wirer/types.js";
import type { BackendEndpointSpec } from "@shared/spec-schema.js";

// ─── Constants ───────────────────────────────────────────────────────────────

const SYSTEM_PROMPT = `You are a senior backend engineer with deep expertise in Express, TypeScript, Drizzle ORM, and PostgreSQL. You write production-quality, type-safe API code.`;

const emptyInventory: BackendBrownfieldInventory = {
  existingRoutePaths: [],
  existingStorageFunctions: [],
  existingTableNames: [],
  routesInsertionOffset: -1,
  storageInsertionOffset: -1,
  schemaInsertionOffset: -1,
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

function safeFileName(s: string): string {
  return s.replace(/[^a-zA-Z0-9_-]/g, "_").replace(/_+/g, "_");
}

function endpointBasename(endpoint: BackendEndpointSpec): string {
  const method = endpoint.method.toLowerCase();
  const tail = safeFileName(endpoint.path.replace(/^\/+/, "").replace(/\//g, "_"));
  return `${method}_${tail || "root"}`;
}

function toPascal(name: string): string {
  return name
    .split(/[^a-zA-Z0-9]+/)
    .filter(Boolean)
    .map((seg) => seg.charAt(0).toUpperCase() + seg.slice(1))
    .join("");
}

function deriveEntityName(endpointPath: string): string {
  const segments = endpointPath.split("/").filter((s) => s && !s.startsWith(":") && s !== "api");
  const last = segments[segments.length - 1] ?? "items";
  return last.replace(/-([a-z])/g, (_, c: string) => c.toUpperCase());
}

function toPascalEntity(entity: string): string {
  const cap = entity.charAt(0).toUpperCase() + entity.slice(1);
  if (cap.endsWith("ies")) return cap.slice(0, -3) + "y";
  if (cap.endsWith("ses") || cap.endsWith("xes") || cap.endsWith("zes")) return cap.slice(0, -2);
  if (cap.endsWith("s") && !cap.endsWith("ss")) return cap.slice(0, -1);
  return cap;
}

/**
 * Convert an ApiContract from the SystemArchitecture into the
 * BackendEndpointSpec shape expected by the existing route/storage generators.
 */
function apiContractToEndpointSpec(contract: ApiContract): BackendEndpointSpec {
  return {
    method: contract.method,
    path: contract.path,
    description: contract.description,
    requestBody: contract.requestBody ? Object.keys(contract.requestBody) : [],
    responseFields: contract.responseShape ? Object.keys(contract.responseShape) : [],
    authRequired: contract.authRequired,
    uiPageRef: contract.pageRef,
    source: "explicit" as const,
  };
}

// ─── Marker-bounded block helpers ────────────────────────────────────────────

const INDEX_IMPORTS_START = "// __GENERATED_ROUTE_IMPORTS__";
const INDEX_IMPORTS_END = "// __GENERATED_ROUTE_IMPORTS_END__";
const INDEX_REGS_START = "// __GENERATED_ROUTE_REGISTRATIONS__";
const INDEX_REGS_END = "// __GENERATED_ROUTE_REGISTRATIONS_END__";

function extractBlockBody(source: string, startMarker: string, endMarker: string): string {
  const startIdx = source.indexOf(startMarker);
  const endIdx = source.indexOf(endMarker);
  if (startIdx === -1 || endIdx === -1 || endIdx < startIdx) return "";
  return source.slice(startIdx + startMarker.length, endIdx).trim();
}

function replaceOrInsertBlock(
  source: string,
  startMarker: string,
  endMarker: string,
  newBody: string,
): string {
  const startIdx = source.indexOf(startMarker);
  const endIdx = source.indexOf(endMarker);
  if (startIdx === -1 || endIdx === -1 || endIdx < startIdx) {
    const prefix = source.endsWith("\n") ? source : source + "\n";
    return `${prefix}${startMarker}\n${newBody}\n${endMarker}\n`;
  }
  const before = source.slice(0, startIdx + startMarker.length);
  const after = source.slice(endIdx);
  return `${before}\n${newBody}\n${after}`;
}

function ensureLine(body: string, line: string): string {
  const lines = body.split("\n").map((l) => l.trimEnd()).filter((l) => l.length > 0);
  if (!lines.includes(line.trim())) lines.push(line.trim());
  return lines.join("\n");
}

// ─── server/generated/index.ts scaffolding ───────────────────────────────────

function ensureGeneratedIndex(generatedDir: string): string {
  const indexPath = path.join(generatedDir, "index.ts");
  if (!fs.existsSync(indexPath)) {
    const scaffold = [
      "// AUTO-GENERATED by saas-dev:backend-agent — do not edit manually",
      `import type { Express } from "express";`,
      "",
      INDEX_IMPORTS_START,
      INDEX_IMPORTS_END,
      "",
      `export function registerGeneratedRoutes(app: Express): void {`,
      `  ${INDEX_REGS_START}`,
      `  ${INDEX_REGS_END}`,
      `}`,
      "",
    ].join("\n");
    fs.writeFileSync(indexPath, scaffold, "utf-8");
  }
  return indexPath;
}

function addRouteToGeneratedIndex(
  indexPath: string,
  baseName: string,
  registerFnName: string,
): void {
  const src = fs.readFileSync(indexPath, "utf-8");
  const importLine = `import { ${registerFnName} } from "./routes/${baseName}.js";`;
  const regLine = `  ${registerFnName}(app);`;

  const currentImports = extractBlockBody(src, INDEX_IMPORTS_START, INDEX_IMPORTS_END);
  const newImports = ensureLine(currentImports, importLine);

  let next = replaceOrInsertBlock(src, INDEX_IMPORTS_START, INDEX_IMPORTS_END, newImports);

  const currentRegs = extractBlockBody(next, INDEX_REGS_START, INDEX_REGS_END);
  const newRegs = ensureLine(currentRegs, regLine);
  next = replaceOrInsertBlock(next, INDEX_REGS_START, INDEX_REGS_END, newRegs);

  fs.writeFileSync(indexPath, next, "utf-8");
}

// ─── Schema file assembly ────────────────────────────────────────────────────

function writeGeneratedSchemaFile(
  generatedDir: string,
  schemaBlockContent: string,
  tableName: string,
): void {
  const generatedSchemaFile = path.join(generatedDir, "schema.ts");
  const banner =
    "// AUTO-GENERATED by saas-dev:backend-agent — do not edit manually\n" +
    `import { pgTable, text, timestamp } from "drizzle-orm/pg-core";\n` +
    `import { z } from "zod";\n\n`;

  let existing = fs.existsSync(generatedSchemaFile)
    ? fs.readFileSync(generatedSchemaFile, "utf-8")
    : banner;
  if (!existing.startsWith("// AUTO-GENERATED")) {
    existing = banner + existing;
  }

  const tableDeclRegex = new RegExp(`export\\s+const\\s+${tableName}\\s*=\\s*pgTable`);
  if (!tableDeclRegex.test(existing)) {
    existing =
      (existing.endsWith("\n") ? existing : existing + "\n") +
      "\n" +
      schemaBlockContent;
    fs.writeFileSync(generatedSchemaFile, existing, "utf-8");
  }
}

// ─── Per-endpoint code generation ────────────────────────────────────────────

interface EndpointGenerationResult {
  backendRoute: BackendRoute;
  routeFilePath: string;
  storageFilePath: string;
  migrationFilePath: string;
}

function generateEndpointCode(
  endpoint: BackendEndpointSpec,
  projectRoot: string,
  generatedDir: string,
  migrationsDir: string,
): EndpointGenerationResult {
  const routeBlock = generateRouteCode(endpoint, emptyInventory);
  const storageBlock = generateStorageCode(endpoint);

  const entityName = deriveEntityName(endpoint.path);
  const tableName = entityName;
  const fields = endpoint.requestBody.length > 0 ? endpoint.requestBody : ["name"];
  const schemaBlock = generateSchemaCode(tableName, fields);
  const migrationSQL = generateMigrationSQL([schemaBlock]);

  const base = endpointBasename(endpoint);
  const registerFnName = `register${toPascal(base)}Routes`;
  const pascal = toPascalEntity(entityName);

  const routesDir = path.join(generatedDir, "routes");
  const storageDir = path.join(generatedDir, "storage");

  // ── Per-endpoint route file ──────────────────────────────────────────────
  const routeFilePath = path.join(routesDir, `${base}.ts`);
  const routeContent = [
    "// AUTO-GENERATED by saas-dev:backend-agent — do not edit manually",
    `import type { Request, Response, Express } from "express";`,
    `import { z } from "zod";`,
    `import { storage } from "../../storage.js";`,
    "",
    routeBlock.zodSchemaCode ?? "",
    "",
    `export function ${registerFnName}(app: Express): void {`,
    routeBlock.code
      .split("\n")
      .map((l) => (l.length > 0 ? `  ${l}` : l))
      .join("\n"),
    `}`,
    "",
  ]
    .filter((s) => s !== undefined)
    .join("\n");
  fs.writeFileSync(routeFilePath, routeContent, "utf-8");

  // ── Per-entity storage file ──────────────────────────────────────────────
  const storageFilePath = path.join(storageDir, `${entityName}.ts`);
  const storageContent = [
    "// AUTO-GENERATED by saas-dev:backend-agent — do not edit manually",
    `import { eq } from "drizzle-orm";`,
    `import { db } from "../../db";`,
    `import { ${tableName}, type ${pascal}, type Insert${pascal} } from "../../../shared/schema";`,
    "",
    `export const ${entityName}Storage = {`,
    storageBlock.code
      .split("\n")
      .map((l) => (l.length > 0 ? `  ${l}` : l))
      .join("\n"),
    `};`,
    "",
  ].join("\n");
  fs.writeFileSync(storageFilePath, storageContent, "utf-8");

  // ── Schema block into server/generated/schema.ts ─────────────────────────
  const schemaBlockContent = [
    schemaBlock.drizzleCode,
    "",
    schemaBlock.zodInsertCode,
    "",
    schemaBlock.typeExportCode,
    "",
  ].join("\n");
  writeGeneratedSchemaFile(generatedDir, schemaBlockContent, tableName);

  // ── Index registration ───────────────────────────────────────────────────
  const indexPath = ensureGeneratedIndex(generatedDir);
  addRouteToGeneratedIndex(indexPath, base, registerFnName);

  // ── Migration SQL ────────────────────────────────────────────────────────
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  const migrationFilePath = path.join(migrationsDir, `${timestamp}-${base}.sql`);
  fs.writeFileSync(migrationFilePath, migrationSQL, "utf-8");

  return {
    backendRoute: {
      method: endpoint.method,
      path: endpoint.path,
      filePath: routeFilePath,
      entity: entityName,
      schemaGenerated: true,
      storageGenerated: true,
      migrationPath: migrationFilePath,
    },
    routeFilePath,
    storageFilePath,
    migrationFilePath,
  };
}

// ─── Main agent function ─────────────────────────────────────────────────────

export async function runBackendAgent(
  brief: { spec: { backendSpec?: { endpoints: BackendEndpointSpec[] } } },
  store: ArtifactStore,
): Promise<BackendRoute[]> {
  const projectRoot = store.getProjectRoot();

  // ── 1. Read SystemArchitecture from ArtifactStore ────────────────────────
  const architecture = store.getArchitecture();

  // ── 2. Resolve endpoints: architecture apiContracts or brief fallback ────
  let endpoints: BackendEndpointSpec[];

  if (architecture && architecture.apiContracts.length > 0) {
    endpoints = architecture.apiContracts.map(apiContractToEndpointSpec);
  } else if (brief.spec.backendSpec && brief.spec.backendSpec.endpoints.length > 0) {
    endpoints = brief.spec.backendSpec.endpoints;
  } else {
    throw new Error(
      "Backend agent: no API contracts in architecture and no endpoints in brief.spec.backendSpec. " +
      "Cannot generate backend code without endpoint definitions.",
    );
  }

  // ── 3. Ensure output directories exist ───────────────────────────────────
  const generatedDir = path.join(projectRoot, "server", "generated");
  fs.mkdirSync(path.join(generatedDir, "routes"), { recursive: true });
  fs.mkdirSync(path.join(generatedDir, "storage"), { recursive: true });

  const migrationsDir = path.join(projectRoot, ".planning", "output", "migrations");
  fs.mkdirSync(migrationsDir, { recursive: true });

  // Scaffold the generated index file
  ensureGeneratedIndex(generatedDir);

  // ── 4. Generate Drizzle schemas for architecture entities ────────────────
  // If we have a full architecture with a dataModel, generate schemas for
  // every entity up front so the schema file is complete before route files
  // reference its types.
  if (architecture && architecture.dataModel.entities.length > 0) {
    const schemaBanner =
      "// AUTO-GENERATED by saas-dev:backend-agent — do not edit manually\n" +
      `import { pgTable, text, timestamp } from "drizzle-orm/pg-core";\n` +
      `import { z } from "zod";\n\n`;

    const generatedSchemaFile = path.join(generatedDir, "schema.ts");
    let schemaFileContent = fs.existsSync(generatedSchemaFile)
      ? fs.readFileSync(generatedSchemaFile, "utf-8")
      : schemaBanner;
    if (!schemaFileContent.startsWith("// AUTO-GENERATED")) {
      schemaFileContent = schemaBanner + schemaFileContent;
    }

    for (const entity of architecture.dataModel.entities) {
      const tableDeclRegex = new RegExp(
        `export\\s+const\\s+${entity.tableName}\\s*=\\s*pgTable`,
      );
      if (tableDeclRegex.test(schemaFileContent)) continue;

      const fieldNames = entity.fields.map((f) => f.name);
      const schemaBlock = generateSchemaCode(entity.tableName, fieldNames);
      const blockContent = [
        schemaBlock.drizzleCode,
        "",
        schemaBlock.zodInsertCode,
        "",
        schemaBlock.typeExportCode,
        "",
      ].join("\n");

      schemaFileContent =
        (schemaFileContent.endsWith("\n") ? schemaFileContent : schemaFileContent + "\n") +
        "\n" +
        blockContent;
    }

    fs.writeFileSync(generatedSchemaFile, schemaFileContent, "utf-8");

    // Write migration SQL for all entities
    const allSchemaBlocks = architecture.dataModel.entities.map((entity) =>
      generateSchemaCode(entity.tableName, entity.fields.map((f) => f.name)),
    );
    const fullMigrationSQL = generateMigrationSQL(allSchemaBlocks);
    const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
    const fullMigrationPath = path.join(migrationsDir, `${timestamp}-all-entities.sql`);
    fs.writeFileSync(fullMigrationPath, fullMigrationSQL, "utf-8");
  }

  // ── 5. Generate route + storage for each endpoint ────────────────────────
  //    Skip endpoints that already exist in the codebase. For new endpoints,
  //    verify referenced storage methods exist or mark them as generated.
  const backendRoutes: BackendRoute[] = [];

  // Load codebase audit from artifact store (written by architecture agent)
  const audit = store.getExistingCodebaseAudit();
  const existingRoutesSet = new Set(
    (audit?.existingRoutes ?? []).map((r) => r.toLowerCase()),
  );
  const existingStorageSet = new Set(audit?.existingStorageMethods ?? []);

  for (const endpoint of endpoints) {
    // Check if this route already exists in the codebase
    const routeKey = `${endpoint.method.toLowerCase()} ${endpoint.path}`;
    if (existingRoutesSet.has(routeKey)) {
      store.appendBuildLog({
        agent: "backend-agent",
        event: "skip",
        timestamp: Date.now(),
        detail: `Skipping existing route: ${endpoint.method} ${endpoint.path}`,
      });
      backendRoutes.push({
        method: endpoint.method,
        path: endpoint.path,
        filePath: "existing",
        entity: deriveEntityName(endpoint.path),
        schemaGenerated: false,
        storageGenerated: false,
      });
      continue;
    }

    const result = generateEndpointCode(
      endpoint,
      projectRoot,
      generatedDir,
      migrationsDir,
    );
    backendRoutes.push(result.backendRoute);
  }

  // ── 6. Write BackendRoute[] to ArtifactStore ─────────────────────────────
  store.setBackendRoutes(backendRoutes);

  store.appendBuildLog({
    agent: "backend-agent",
    event: "complete",
    timestamp: Date.now(),
    detail: `Generated ${backendRoutes.length} routes, schema, storage, and migrations in server/generated/`,
  });

  // ── 7. Return BackendRoute[] ─────────────────────────────────────────────
  return backendRoutes;
}
