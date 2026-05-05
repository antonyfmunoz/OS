import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock fs/promises before importing the module
vi.mock("fs/promises", () => ({
  writeFile: vi.fn().mockResolvedValue(undefined),
  mkdir: vi.fn().mockResolvedValue(undefined),
}));

// Mock child_process
vi.mock("child_process", () => ({
  execSync: vi.fn().mockReturnValue(Buffer.from("Migration complete\n")),
}));

import { writeMigrationScript, runMigration } from "../../../lib/backend-wirer/migration-runner.js";
import * as fsPromises from "fs/promises";
import * as childProcess from "child_process";

describe("writeMigrationScript", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("writes file to scripts/ directory with correct YYYY-MM-DD date pattern", async () => {
    const filePath = await writeMigrationScript("/project/root", "CREATE TABLE IF NOT EXISTS test;", "test-slug");
    // Path should contain date format YYYY-MM-DD
    expect(filePath).toMatch(/\d{4}-\d{2}-\d{2}/);
    expect(filePath).toContain("scripts");
    expect(filePath).toContain("test-slug");
  });

  it("written file content contains correct db import", async () => {
    await writeMigrationScript("/project/root", "CREATE TABLE IF NOT EXISTS test;", "test-slug");
    const writeFileMock = vi.mocked(fsPromises.writeFile);
    expect(writeFileMock).toHaveBeenCalledOnce();
    const content = writeFileMock.mock.calls[0][1] as string;
    expect(content).toContain('import { db, client } from "../server/db.js"');
  });

  it("written file content wraps SQL in db.execute(sql`...`)", async () => {
    const sql = "CREATE TABLE IF NOT EXISTS test (id text PRIMARY KEY);";
    await writeMigrationScript("/project/root", sql, "test-slug");
    const writeFileMock = vi.mocked(fsPromises.writeFile);
    const content = writeFileMock.mock.calls[0][1] as string;
    expect(content).toContain("db.execute(sql`");
    expect(content).toContain(sql);
  });

  it("written file contains runMigration function and error handling", async () => {
    await writeMigrationScript("/project/root", "SELECT 1;", "test-slug");
    const writeFileMock = vi.mocked(fsPromises.writeFile);
    const content = writeFileMock.mock.calls[0][1] as string;
    expect(content).toContain("async function runMigration");
    expect(content).toContain("await client.end()");
    expect(content).toContain("process.exit(1)");
  });
});

describe("runMigration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns success:true when execSync succeeds", async () => {
    vi.mocked(childProcess.execSync).mockReturnValue(Buffer.from("Migration complete\n"));
    const result = await runMigration("/project/root/scripts/migration.ts", "/project/root");
    expect(result.success).toBe(true);
    expect(result.output).toContain("Migration complete");
  });

  it("returns success:false when execSync throws", async () => {
    vi.mocked(childProcess.execSync).mockImplementation(() => {
      throw new Error("tsx failed: syntax error");
    });
    const result = await runMigration("/project/root/scripts/migration.ts", "/project/root");
    expect(result.success).toBe(false);
    expect(result.output).toContain("tsx failed");
  });
});
