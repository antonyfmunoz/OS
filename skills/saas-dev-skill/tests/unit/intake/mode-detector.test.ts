import { describe, it, expect, afterEach } from "vitest";
import fs from "node:fs";
import path from "node:path";
import { detectIntakeMode } from "../../../lib/intake/mode-detector.js";

// ─── Helpers ──────────────────────────────────────────────────────────────────

const BASE = path.join(process.cwd(), "tests", "tmp-mode-detector-" + Date.now());

function setup(dirs: string[], files: Record<string, string> = {}): string {
  const root = path.join(BASE, String(Math.random()).slice(2, 10));
  for (const dir of dirs) {
    fs.mkdirSync(path.join(root, dir), { recursive: true });
  }
  for (const [filePath, content] of Object.entries(files)) {
    const full = path.join(root, filePath);
    fs.mkdirSync(path.dirname(full), { recursive: true });
    fs.writeFileSync(full, content, "utf-8");
  }
  return root;
}

afterEach(() => {
  if (fs.existsSync(BASE)) {
    fs.rmSync(BASE, { recursive: true, force: true });
  }
});

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("detectIntakeMode", () => {
  it("returns 'greenfield' for empty directory", () => {
    const root = setup([]);
    expect(detectIntakeMode(root)).toBe("greenfield");
  });

  it("returns 'greenfield' when .planning/ exists but is empty", () => {
    const root = setup([".planning"]);
    expect(detectIntakeMode(root)).toBe("greenfield");
  });

  it("returns 'docs-only' when PRD.md exists", () => {
    const root = setup([], {
      ".planning/PRD.md": "# My Product\nA great SaaS.",
    });
    expect(detectIntakeMode(root)).toBe("docs-only");
  });

  it("returns 'docs-only' when REQUIREMENTS.md exists", () => {
    const root = setup([], {
      ".planning/REQUIREMENTS.md": "# Requirements\n- Feature A",
    });
    expect(detectIntakeMode(root)).toBe("docs-only");
  });

  it("returns 'docs-only' when spec files exist", () => {
    const root = setup([], {
      ".planning/specs/mvp.json": '{"pages":[]}',
    });
    expect(detectIntakeMode(root)).toBe("docs-only");
  });

  it("returns 'existing-codebase' when client/src has .tsx files", () => {
    const root = setup([], {
      "client/src/App.tsx": "export default function App() {}",
      ".planning/PRD.md": "# Product",
    });
    expect(detectIntakeMode(root)).toBe("existing-codebase");
  });

  it("returns 'existing-codebase' when server has .ts files", () => {
    const root = setup([], {
      "server/index.ts": "import express from 'express';",
    });
    expect(detectIntakeMode(root)).toBe("existing-codebase");
  });

  it("returns 'greenfield' when client/src exists but has no code files", () => {
    const root = setup(["client/src"], {
      "client/src/styles.css": "body { margin: 0; }",
    });
    expect(detectIntakeMode(root)).toBe("greenfield");
  });

  it("existing-codebase takes priority over docs-only", () => {
    const root = setup([], {
      ".planning/PRD.md": "# Product",
      "client/src/pages/dashboard.tsx": "export default function Dashboard() {}",
    });
    expect(detectIntakeMode(root)).toBe("existing-codebase");
  });
});
