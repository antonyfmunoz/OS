import { describe, it, expect, beforeEach, afterAll } from "vitest";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { loadDesignSkills, resetSkillCache } from "../../../lib/react-gen/skill-loader.js";

const TMP = fs.mkdtempSync(path.join(os.tmpdir(), "skill-loader-test-"));

beforeEach(() => {
  resetSkillCache();
});

afterAll(() => {
  fs.rmSync(TMP, { recursive: true, force: true });
});

describe("loadDesignSkills", () => {
  it("returns empty string when no skill files exist", async () => {
    const result = await loadDesignSkills(TMP);
    expect(result).toBe("");
  });

  it("loads react-gen skill from project .claude/skills/", async () => {
    const skillDir = path.join(TMP, ".claude", "skills", "saas-dev", "skills", "react-gen");
    fs.mkdirSync(skillDir, { recursive: true });
    fs.writeFileSync(
      path.join(skillDir, "SKILL.md"),
      `---
name: saas-dev:react-gen
description: Test skill
---

# react-gen

### Design Token Enforcement
All components must follow tokens.

### Self-Review
Every component gets reviewed.

### Other Section
Not extracted.
`,
      "utf-8",
    );

    const result = await loadDesignSkills(TMP);
    expect(result).toContain("SKILL-INJECTED DESIGN PRINCIPLES");
    expect(result).toContain("Design Token Enforcement");
    expect(result).toContain("Self-Review");
    expect(result).not.toContain("Other Section");
  });

  it("caches result on second call", async () => {
    const first = await loadDesignSkills(TMP);
    const second = await loadDesignSkills(TMP);
    // After reset in beforeEach, both should be equal (cache populated on first call)
    expect(first).toBe(second);
  });

  it("resetSkillCache clears the cache", async () => {
    await loadDesignSkills(TMP);
    resetSkillCache();

    // Create a skill file after cache was populated
    const skillDir = path.join(TMP, ".claude", "skills", "saas-dev", "skills", "react-gen");
    fs.mkdirSync(skillDir, { recursive: true });
    fs.writeFileSync(
      path.join(skillDir, "SKILL.md"),
      `---
name: test
description: test
---

### Design Token Enforcement
New content after cache reset.
`,
      "utf-8",
    );

    const result = await loadDesignSkills(TMP);
    expect(result).toContain("New content after cache reset");
  });

  it("includes override notice in output", async () => {
    const skillDir = path.join(TMP, ".claude", "skills", "saas-dev", "skills", "react-gen");
    fs.mkdirSync(skillDir, { recursive: true });
    fs.writeFileSync(
      path.join(skillDir, "SKILL.md"),
      `---
name: test
description: test
---

### Design Token Enforcement
Tokens here.
`,
      "utf-8",
    );

    resetSkillCache();
    const result = await loadDesignSkills(TMP);
    expect(result).toContain("mandatory design rules");
    expect(result).toContain("OVERRIDE");
  });
});
