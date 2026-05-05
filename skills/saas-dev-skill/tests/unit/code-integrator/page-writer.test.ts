import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mkdtemp, mkdir, writeFile, rm, readFile } from "fs/promises";
import { tmpdir } from "os";
import { join } from "path";

// Mock child_process.exec before importing page-writer to prevent real npx calls
vi.mock("child_process", () => ({
  exec: vi.fn((_cmd: string, _opts: unknown, callback: (err: null, stdout: string, stderr: string) => void) => {
    callback(null, "", "");
  }),
}));

import {
  writePage,
  checkFileConflict,
  ensureShadcnComponents,
  toKebabCase,
} from "../../../lib/code-integrator/page-writer.js";

// ─── Setup: temp project root ─────────────────────────────────────────────────

let tempRoot: string;

beforeEach(async () => {
  tempRoot = await mkdtemp(join(tmpdir(), "page-writer-test-"));
  // Create the pages directory structure
  await mkdir(join(tempRoot, "client", "src", "pages"), { recursive: true });
});

afterEach(async () => {
  await rm(tempRoot, { recursive: true, force: true });
});

// ─── toKebabCase tests ────────────────────────────────────────────────────────

describe("toKebabCase", () => {
  it("converts PascalCase to kebab-case", () => {
    expect(toKebabCase("ReportsPage")).toBe("reports-page");
    expect(toKebabCase("UserSettings")).toBe("user-settings");
    expect(toKebabCase("Dashboard")).toBe("dashboard");
  });

  it("handles all-caps abbreviations", () => {
    expect(toKebabCase("CRM")).toBe("crm");
    expect(toKebabCase("CRMPage")).toBe("crm-page");
    expect(toKebabCase("APIKeys")).toBe("api-keys");
    expect(toKebabCase("URLShortener")).toBe("url-shortener");
  });

  it("does not double-kebab already kebab-like input", () => {
    expect(toKebabCase("MyPage")).toBe("my-page");
  });

  it("handles lowercase single word", () => {
    expect(toKebabCase("simple")).toBe("simple");
  });
});

// ─── writePage tests ──────────────────────────────────────────────────────────

describe("writePage", () => {
  const tsxContent = `import { Layout } from "@/components/layout";

export default function ReportsPage() {
  return <Layout title="Reports"><div>Reports</div></Layout>;
}`;

  it("writes page file to correct path", async () => {
    const filePath = await writePage({
      projectRoot: tempRoot,
      pageName: "Reports",
      tsxContent,
    });

    // File should exist at computed path
    const expectedPath = join(tempRoot, "client", "src", "pages", "reports-page.tsx");
    expect(filePath).toBe(expectedPath);

    const written = await readFile(filePath, "utf-8");
    expect(written).toBe(tsxContent);
  });

  it("converts PascalCase to kebab-case filename", async () => {
    await writePage({
      projectRoot: tempRoot,
      pageName: "UserSettings",
      tsxContent,
    });
    const { existingPath } = await checkFileConflict({ projectRoot: tempRoot, pageName: "UserSettings" });
    expect(existingPath).toContain("user-settings-page.tsx");
  });

  it("converts CRM to crm-page.tsx", async () => {
    await writePage({
      projectRoot: tempRoot,
      pageName: "CRM",
      tsxContent,
    });
    const { exists } = await checkFileConflict({ projectRoot: tempRoot, pageName: "CRM" });
    expect(exists).toBe(true);
  });

  it("refuses to overwrite existing file without overwrite flag", async () => {
    // Create a file at the target path first
    const targetPath = join(tempRoot, "client", "src", "pages", "reports-page.tsx");
    await writeFile(targetPath, "existing content", "utf-8");

    // Should throw when trying to write without overwrite flag
    await expect(
      writePage({ projectRoot: tempRoot, pageName: "Reports", tsxContent })
    ).rejects.toThrow(/already exists/);
  });

  it("overwrites existing file when overwrite=true", async () => {
    // Create a file with old content
    const targetPath = join(tempRoot, "client", "src", "pages", "reports-page.tsx");
    await writeFile(targetPath, "old content", "utf-8");

    // Should succeed and replace content when overwrite=true
    await writePage({
      projectRoot: tempRoot,
      pageName: "Reports",
      tsxContent,
      overwrite: true,
    });

    const written = await readFile(targetPath, "utf-8");
    expect(written).toBe(tsxContent);
  });
});

// ─── checkFileConflict tests ──────────────────────────────────────────────────

describe("checkFileConflict", () => {
  it("detects existing file", async () => {
    // Create the file first
    const targetPath = join(tempRoot, "client", "src", "pages", "reports-page.tsx");
    await writeFile(targetPath, "existing content", "utf-8");

    const result = await checkFileConflict({ projectRoot: tempRoot, pageName: "Reports" });

    expect(result.exists).toBe(true);
    expect(result.existingPath).toBe(targetPath);
  });

  it("returns exists=false for new file", async () => {
    const result = await checkFileConflict({ projectRoot: tempRoot, pageName: "Reports" });

    expect(result.exists).toBe(false);
    expect(result.existingPath).toBeNull();
  });
});

// ─── ensureShadcnComponents tests ────────────────────────────────────────────

describe("ensureShadcnComponents", () => {
  it("identifies missing components and installs them", async () => {
    const installedComponents = ["button", "card"];
    const extractedImports = ["button", "card", "tabs"];

    // child_process.exec is mocked above — no real npx runs
    const installed = await ensureShadcnComponents({
      projectRoot: tempRoot,
      extractedImports,
      installedComponents,
    });

    // "tabs" is the only missing component — should be installed
    expect(installed).toEqual(["tabs"]);
  });

  it("returns empty when all components present", async () => {
    const installedComponents = ["button", "card", "tabs"];
    const extractedImports = ["button", "card", "tabs"];

    const result = await ensureShadcnComponents({
      projectRoot: tempRoot,
      extractedImports,
      installedComponents,
    });

    // When all components are present, no npx calls, empty array returned
    expect(result).toEqual([]);
  });
});
