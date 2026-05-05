import { describe, it, expect } from "vitest";
import {
  generateDockerConfig,
  generateHostingMenu,
} from "../../../lib/analytics-delivery/docker-config-generator.js";

describe("generateDockerConfig", () => {
  it("Test 1: railway returns Dockerfile with multi-stage structure and PORT env var", () => {
    const result = generateDockerConfig("railway");
    expect(result.dockerfile).toContain("FROM node:20-slim AS builder");
    expect(result.dockerfile).toContain("FROM node:20-slim AS runner");
    expect(result.dockerfile).toContain("ENV PORT=5000");
    expect(result.dockerfile).toContain("EXPOSE 5000");
    expect(result.dockerfile).toContain('CMD ["node", "dist/index.js"]');
  });

  it("Test 2: railway returns railway.toml platform config with builder=DOCKERFILE and /health", () => {
    const result = generateDockerConfig("railway");
    expect(result.platformConfigFilename).toBe("railway.toml");
    expect(result.platformConfig).toContain('builder = "DOCKERFILE"');
    expect(result.platformConfig).toContain('healthcheckPath = "/health"');
  });

  it("Test 3: render returns render.yaml with runtime=docker and /health", () => {
    const result = generateDockerConfig("render");
    expect(result.platformConfigFilename).toBe("render.yaml");
    expect(result.platformConfig).toContain("runtime: docker");
    expect(result.platformConfig).toContain("healthCheckPath: /health");
  });

  it("Test 4: fly returns fly.toml with internal_port=5000 and force_https", () => {
    const result = generateDockerConfig("fly");
    expect(result.platformConfigFilename).toBe("fly.toml");
    expect(result.platformConfig).toContain("internal_port = 5000");
    expect(result.platformConfig).toContain("force_https = true");
  });

  it("Test 5: custom returns dockerCompose defined with build:. and ports", () => {
    const result = generateDockerConfig("custom");
    expect(result.dockerCompose).toBeDefined();
    expect(result.dockerCompose).toContain("build: .");
    expect(result.dockerCompose).toContain("ports:");
    expect(result.dockerCompose).toContain('"5000:5000"');
  });

  it("Test 6: custom returns empty platformConfig and platformConfigFilename", () => {
    const result = generateDockerConfig("custom");
    expect(result.platformConfig).toBe("");
    expect(result.platformConfigFilename).toBe("");
  });

  it("Test 7: all targets produce identical Dockerfile content", () => {
    const railway = generateDockerConfig("railway");
    const render = generateDockerConfig("render");
    const fly = generateDockerConfig("fly");
    const custom = generateDockerConfig("custom");
    expect(railway.dockerfile).toBe(render.dockerfile);
    expect(render.dockerfile).toBe(fly.dockerfile);
    expect(fly.dockerfile).toBe(custom.dockerfile);
  });

  it("Test 8: generateHostingMenu returns 4 objects with required fields", () => {
    const menu = generateHostingMenu();
    expect(menu).toHaveLength(4);
    for (const item of menu) {
      expect(item).toHaveProperty("target");
      expect(item).toHaveProperty("name");
      expect(item).toHaveProperty("pros");
      expect(item).toHaveProperty("cons");
    }
    const targets = menu.map((m) => m.target);
    expect(targets).toContain("railway");
    expect(targets).toContain("render");
    expect(targets).toContain("fly");
    expect(targets).toContain("custom");
  });

  it("Test 9: all targets return non-empty dockerignore with required entries", () => {
    const targets = ["railway", "render", "fly", "custom"] as const;
    for (const target of targets) {
      const result = generateDockerConfig(target);
      expect(result.dockerignore).toBeTruthy();
      expect(result.dockerignore).toContain("node_modules");
      expect(result.dockerignore).toContain("dist");
      expect(result.dockerignore).toContain(".git");
      expect(result.dockerignore).toContain(".env");
    }
  });

  it("Test 10: Dockerfile contains PORT env var default 5000 and HEALTHCHECK uses PORT", () => {
    const result = generateDockerConfig("railway");
    expect(result.dockerfile).toContain("ENV PORT=5000");
    expect(result.dockerfile).toContain("HEALTHCHECK");
    expect(result.dockerfile).toContain("${PORT}");
  });

  it("returns correct target in result", () => {
    expect(generateDockerConfig("railway").target).toBe("railway");
    expect(generateDockerConfig("render").target).toBe("render");
    expect(generateDockerConfig("fly").target).toBe("fly");
    expect(generateDockerConfig("custom").target).toBe("custom");
  });

  it("Dockerfile contains curl install for HEALTHCHECK in runner stage", () => {
    const result = generateDockerConfig("railway");
    expect(result.dockerfile).toContain("apt-get install");
    expect(result.dockerfile).toContain("curl");
  });
});
