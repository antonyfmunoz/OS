import { describe, it, expect, afterEach } from "vitest";
import { mkdtemp, mkdir, writeFile, rm } from "fs/promises";
import { join } from "path";
import { tmpdir } from "os";
import { scanEnvVars, generateEnvExample } from "../../../lib/analytics-delivery/env-scanner.js";
import type { EnvVarEntry } from "../../../lib/analytics-delivery/types.js";

// ─── Helpers ──────────────────────────────────────────────────────────────────

async function createTempProject(files: Record<string, string>): Promise<string> {
  const root = await mkdtemp(join(tmpdir(), "env-scanner-test-"));
  for (const [relPath, content] of Object.entries(files)) {
    const fullPath = join(root, relPath);
    const dir = fullPath.substring(0, fullPath.lastIndexOf("/") !== -1 ? fullPath.lastIndexOf("/") : fullPath.lastIndexOf("\\"));
    await mkdir(dir, { recursive: true });
    await writeFile(fullPath, content, "utf8");
  }
  return root;
}

const tempDirs: string[] = [];

afterEach(async () => {
  for (const dir of tempDirs) {
    await rm(dir, { recursive: true, force: true });
  }
  tempDirs.length = 0;
});

// ─── Tests: scanEnvVars ───────────────────────────────────────────────────────

describe("scanEnvVars", () => {
  it("Test 1: finds process.env.DATABASE_URL (dot notation) in server file", async () => {
    const root = await createTempProject({
      "server/index.ts": `const db = process.env.DATABASE_URL;\n`,
    });
    tempDirs.push(root);

    const entries = await scanEnvVars(root);
    const entry = entries.find((e) => e.name === "DATABASE_URL");
    expect(entry).toBeDefined();
    expect(entry!.source).toBe("server");
  });

  it("Test 2: finds import.meta.env.VITE_POSTHOG_API_KEY in .tsx file", async () => {
    const root = await createTempProject({
      "client/src/posthog.tsx": `const key = import.meta.env.VITE_POSTHOG_API_KEY;\n`,
    });
    tempDirs.push(root);

    const entries = await scanEnvVars(root);
    const entry = entries.find((e) => e.name === "VITE_POSTHOG_API_KEY");
    expect(entry).toBeDefined();
    expect(entry!.source).toBe("client");
  });

  it("Test 3: finds process.env[\"FIREBASE_SERVICE_ACCOUNT_KEY\"] bracket notation", async () => {
    const root = await createTempProject({
      "server/auth.ts": `const key = process.env["FIREBASE_SERVICE_ACCOUNT_KEY"];\n`,
    });
    tempDirs.push(root);

    const entries = await scanEnvVars(root);
    const entry = entries.find((e) => e.name === "FIREBASE_SERVICE_ACCOUNT_KEY");
    expect(entry).toBeDefined();
    expect(entry!.source).toBe("server");
  });

  it("Test 4: deduplicates — same var in 3 files appears once with files array length 3", async () => {
    const root = await createTempProject({
      "server/a.ts": `const a = process.env.DATABASE_URL;\n`,
      "server/b.ts": `const b = process.env.DATABASE_URL;\n`,
      "server/c.ts": `const c = process.env.DATABASE_URL;\n`,
    });
    tempDirs.push(root);

    const entries = await scanEnvVars(root);
    const dbEntries = entries.filter((e) => e.name === "DATABASE_URL");
    expect(dbEntries).toHaveLength(1);
    expect(dbEntries[0].files).toHaveLength(3);
  });

  it("Test 5: skips node_modules and dist directories", async () => {
    const root = await createTempProject({
      "node_modules/some-lib/index.js": `process.env.SHOULD_NOT_FIND_THIS;\n`,
      "dist/index.js": `process.env.ALSO_SHOULD_NOT_FIND;\n`,
      "server/real.ts": `const x = process.env.REAL_VAR;\n`,
    });
    tempDirs.push(root);

    const entries = await scanEnvVars(root);
    expect(entries.find((e) => e.name === "SHOULD_NOT_FIND_THIS")).toBeUndefined();
    expect(entries.find((e) => e.name === "ALSO_SHOULD_NOT_FIND")).toBeUndefined();
    expect(entries.find((e) => e.name === "REAL_VAR")).toBeDefined();
  });

  it("Test 6: marks required=true without fallback, required=false with ?? fallback", async () => {
    const root = await createTempProject({
      "server/config.ts": [
        `const port = process.env.PORT ?? 5000;`,
        `const secret = process.env.SESSION_SECRET;`,
      ].join("\n"),
    });
    tempDirs.push(root);

    const entries = await scanEnvVars(root);
    const portEntry = entries.find((e) => e.name === "PORT");
    const secretEntry = entries.find((e) => e.name === "SESSION_SECRET");

    expect(portEntry).toBeDefined();
    expect(portEntry!.required).toBe(false);

    expect(secretEntry).toBeDefined();
    expect(secretEntry!.required).toBe(true);
  });
});

// ─── Tests: generateEnvExample ────────────────────────────────────────────────

describe("generateEnvExample", () => {
  it("Test 7: produces grouped, sorted .env.example content with section headers", () => {
    const entries: EnvVarEntry[] = [
      { name: "DATABASE_URL", source: "server", files: ["server/db.ts"], required: true },
      { name: "VITE_API_URL", source: "client", files: ["client/src/api.ts"], required: false },
      { name: "API_SECRET", source: "server", files: ["server/routes.ts"], required: false },
    ];

    const result = generateEnvExample(entries);

    expect(result).toContain("# Server-side");
    expect(result).toContain("# Client-side");
    // Alphabetical order within server section
    const serverSection = result.split("# Client-side")[0];
    const apiSecretPos = serverSection.indexOf("API_SECRET");
    const databaseUrlPos = serverSection.indexOf("DATABASE_URL");
    expect(apiSecretPos).toBeLessThan(databaseUrlPos);
  });

  it("Test 8: generateEnvExample always includes VITE_POSTHOG_API_KEY and POSTHOG_PERSONAL_API_KEY", () => {
    const entries: EnvVarEntry[] = [
      { name: "DATABASE_URL", source: "server", files: [], required: true },
    ];

    const result = generateEnvExample(entries);

    expect(result).toContain("VITE_POSTHOG_API_KEY");
    expect(result).toContain("POSTHOG_PERSONAL_API_KEY");
  });

  it("Test 9: marks required vars with # REQUIRED comment suffix", () => {
    const entries: EnvVarEntry[] = [
      { name: "DATABASE_URL", source: "server", files: [], required: true },
      { name: "OPTIONAL_VAR", source: "server", files: [], required: false },
    ];

    const result = generateEnvExample(entries);

    expect(result).toContain("DATABASE_URL=  # REQUIRED");
    expect(result).not.toMatch(/OPTIONAL_VAR=.*# REQUIRED/);
  });
});
