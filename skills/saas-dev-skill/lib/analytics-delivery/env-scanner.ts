import { readFile, readdir } from "fs/promises";
import { join } from "path";
import type { EnvVarEntry } from "./types.js";

// ─── Regex Patterns ───────────────────────────────────────────────────────────

// Four patterns for env var access
const PROCESS_ENV_DOT = /process\.env\.(\w+)/g;
const PROCESS_ENV_BRACKET_DOUBLE = /process\.env\["(\w+)"\]/g;
const PROCESS_ENV_BRACKET_SINGLE = /process\.env\['(\w+)'\]/g;
const IMPORT_META_ENV = /import\.meta\.env\.(\w+)/g;

// Fallback detection — if same line has ?? or ||, the var has a default value
const FALLBACK_REGEX = /\?\?|\|\|/;

// Directories to skip during scanning
const SKIP_DIRS = new Set(["node_modules", "dist", ".git", ".planning", ".claude", ".cursor", ".features", ".memory"]);

// File extensions to scan
const SCAN_EXTENSIONS = new Set([".ts", ".tsx", ".js", ".jsx"]);

// ─── Internal Helpers ─────────────────────────────────────────────────────────

function getExtension(filename: string): string {
  const dot = filename.lastIndexOf(".");
  return dot >= 0 ? filename.substring(dot) : "";
}

type EnvVarMatch = {
  name: string;
  source: "server" | "client";
  required: boolean;
};

function extractEnvVars(content: string, filePath: string): EnvVarMatch[] {
  const results: EnvVarMatch[] = [];

  // Determine if this is a client file based on path or import.meta.env usage
  const isClientFile = filePath.includes("/client/") || filePath.includes("\\client\\");

  const lines = content.split("\n");

  for (const line of lines) {
    const hasFallback = FALLBACK_REGEX.test(line);

    // process.env dot notation
    const dotMatches = [...line.matchAll(PROCESS_ENV_DOT)];
    for (const m of dotMatches) {
      results.push({ name: m[1], source: "server", required: !hasFallback });
    }

    // process.env bracket double-quote notation
    const bracketDoubleMatches = [...line.matchAll(PROCESS_ENV_BRACKET_DOUBLE)];
    for (const m of bracketDoubleMatches) {
      results.push({ name: m[1], source: "server", required: !hasFallback });
    }

    // process.env bracket single-quote notation
    const bracketSingleMatches = [...line.matchAll(PROCESS_ENV_BRACKET_SINGLE)];
    for (const m of bracketSingleMatches) {
      results.push({ name: m[1], source: "server", required: !hasFallback });
    }

    // import.meta.env (Vite client env)
    const importMetaMatches = [...line.matchAll(IMPORT_META_ENV)];
    for (const m of importMetaMatches) {
      // Skip VITE_ prefix isn't required but source is always "client"
      results.push({ name: m[1], source: "client", required: !hasFallback });
    }
  }

  return results;
}

async function walkDir(dirPath: string, rootPath: string): Promise<string[]> {
  const files: string[] = [];
  let entries;

  try {
    entries = await readdir(dirPath, { withFileTypes: true });
  } catch {
    return files;
  }

  for (const entry of entries) {
    if (SKIP_DIRS.has(entry.name)) continue;

    const fullPath = join(dirPath, entry.name);

    if (entry.isDirectory()) {
      const subFiles = await walkDir(fullPath, rootPath);
      files.push(...subFiles);
    } else if (entry.isFile() && SCAN_EXTENSIONS.has(getExtension(entry.name))) {
      files.push(fullPath);
    }
  }

  return files;
}

// ─── scanEnvVars ─────────────────────────────────────────────────────────────

/**
 * Recursively scans client/, server/, and shared/ directories for env var references.
 * Finds process.env (dot + bracket notation) and import.meta.env patterns.
 * Deduplicates by var name, tracks source files, and detects fallback patterns.
 */
export async function scanEnvVars(projectRoot: string): Promise<EnvVarEntry[]> {
  const dirsToScan = ["client", "server", "shared"];
  const allFiles: string[] = [];

  for (const dir of dirsToScan) {
    const dirPath = join(projectRoot, dir);
    const files = await walkDir(dirPath, projectRoot);
    allFiles.push(...files);
  }

  // Map<varName, EnvVarEntry>
  const entryMap = new Map<string, EnvVarEntry>();

  for (const filePath of allFiles) {
    let content: string;
    try {
      content = await readFile(filePath, "utf8");
    } catch {
      continue;
    }

    const matches = extractEnvVars(content, filePath);

    for (const match of matches) {
      const existing = entryMap.get(match.name);
      if (existing) {
        // Merge: add file if not already tracked, keep required=true if any occurrence lacks fallback
        if (!existing.files.includes(filePath)) {
          existing.files.push(filePath);
        }
        if (match.required) {
          existing.required = true;
        }
      } else {
        entryMap.set(match.name, {
          name: match.name,
          source: match.source,
          files: [filePath],
          required: match.required,
        });
      }
    }
  }

  return Array.from(entryMap.values());
}

// ─── generateEnvExample ───────────────────────────────────────────────────────

/**
 * Generates .env.example content from scanned env vars.
 * Groups by source (server/client), sorts alphabetically within groups.
 * Always includes POSTHOG_PERSONAL_API_KEY (server) and VITE_POSTHOG_API_KEY (client) per D-03.
 * Marks required vars with # REQUIRED comment.
 */
export function generateEnvExample(
  entries: EnvVarEntry[],
  extraVars?: Array<{ name: string; source: "server" | "client"; description: string }>
): string {
  // Build combined map of entries (deduplicated by name)
  const allEntries = new Map<string, EnvVarEntry>();

  for (const entry of entries) {
    allEntries.set(entry.name, entry);
  }

  // Always add PostHog requirements per D-03 if not already found
  const posthogPersonal: EnvVarEntry = {
    name: "POSTHOG_PERSONAL_API_KEY",
    source: "server",
    files: [],
    required: false,
  };
  const posthogClient: EnvVarEntry = {
    name: "VITE_POSTHOG_API_KEY",
    source: "client",
    files: [],
    required: false,
  };

  if (!allEntries.has("POSTHOG_PERSONAL_API_KEY")) {
    allEntries.set("POSTHOG_PERSONAL_API_KEY", posthogPersonal);
  }
  if (!allEntries.has("VITE_POSTHOG_API_KEY")) {
    allEntries.set("VITE_POSTHOG_API_KEY", posthogClient);
  }

  // Add any extra vars provided by caller
  if (extraVars) {
    for (const extra of extraVars) {
      if (!allEntries.has(extra.name)) {
        allEntries.set(extra.name, {
          name: extra.name,
          source: extra.source,
          files: [],
          required: false,
        });
      }
    }
  }

  // Split by source
  const serverVars = Array.from(allEntries.values())
    .filter((e) => e.source === "server")
    .sort((a, b) => a.name.localeCompare(b.name));

  const clientVars = Array.from(allEntries.values())
    .filter((e) => e.source === "client")
    .sort((a, b) => a.name.localeCompare(b.name));

  const lines: string[] = [];

  // Server section
  lines.push("# Server-side");
  for (const entry of serverVars) {
    const suffix = entry.required ? "  # REQUIRED" : "";
    lines.push(`${entry.name}=${suffix}`);
  }

  // Blank line separator if both sections exist
  if (clientVars.length > 0) {
    lines.push("");
    lines.push("# Client-side");
    for (const entry of clientVars) {
      const suffix = entry.required ? "  # REQUIRED" : "";
      lines.push(`${entry.name}=${suffix}`);
    }
  }

  return lines.join("\n");
}
