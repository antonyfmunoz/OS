// lib/project-config.ts
// Loads and validates project config from .planning/project.config.json
// Throws if missing — every project using this skill must provide one.

import fs from "fs";
import path from "path";
import { ProjectConfigSchema } from "../shared/design-schema.js";
import type { ProjectConfig } from "../shared/design-schema.js";

export function loadProjectConfig(projectRoot: string): ProjectConfig {
  const configPath = path.join(projectRoot, ".planning", "project.config.json");
  if (!fs.existsSync(configPath)) {
    throw new Error(
      `No project.config.json found at ${configPath}. ` +
        `Copy from .claude/skills/saas-dev/templates/project.config.example.json and fill in your values.`
    );
  }
  const raw = JSON.parse(fs.readFileSync(configPath, "utf-8"));
  return ProjectConfigSchema.parse(raw);
}
