import { describe, it, expect } from "vitest";
import {
  generateCIWorkflow,
  generateCDWorkflow,
} from "../../../lib/analytics-delivery/github-actions-generator.js";

describe("generateCIWorkflow", () => {
  it("Test 1: output contains name: CI and pull_request trigger", () => {
    const output = generateCIWorkflow();
    expect(output).toContain("name: CI");
    expect(output).toContain("pull_request");
  });

  it("Test 2: output contains npm ci, npm run check, npm test, npm run build in order", () => {
    const output = generateCIWorkflow();
    const ciIdx = output.indexOf("npm ci");
    const checkIdx = output.indexOf("npm run check");
    const testIdx = output.indexOf("npm test");
    const buildIdx = output.indexOf("npm run build");
    expect(ciIdx).toBeGreaterThan(-1);
    expect(checkIdx).toBeGreaterThan(ciIdx);
    expect(testIdx).toBeGreaterThan(checkIdx);
    expect(buildIdx).toBeGreaterThan(testIdx);
  });

  it("Test 3: output contains node-version: '20' and cache: 'npm'", () => {
    const output = generateCIWorkflow();
    expect(output).toContain('node-version: "20"');
    expect(output).toContain('cache: "npm"');
  });
});

describe("generateCDWorkflow", () => {
  it("Test 4: railway CD output contains name: CD and push to main trigger", () => {
    const output = generateCDWorkflow("railway");
    expect(output).toContain("name: CD");
    expect(output).toContain("branches: [main]");
  });

  it("Test 5: railway CD output contains environment: staging and environment: production", () => {
    const output = generateCDWorkflow("railway");
    expect(output).toContain("environment: staging");
    expect(output).toContain("environment: production");
  });

  it("Test 6: railway CD output contains deploy-production job with needs: deploy-staging", () => {
    const output = generateCDWorkflow("railway");
    expect(output).toContain("deploy-production:");
    expect(output).toContain("needs: deploy-staging");
  });

  it("Test 7: railway CD output contains @railway/cli install and railway up", () => {
    const output = generateCDWorkflow("railway");
    expect(output).toContain("@railway/cli");
    expect(output).toContain("railway up");
  });

  it("Test 8: render CD output contains RENDER_DEPLOY_HOOK_URL", () => {
    const output = generateCDWorkflow("render");
    expect(output).toContain("RENDER_DEPLOY_HOOK_URL");
  });

  it("Test 9: fly CD output contains flyctl deploy", () => {
    const output = generateCDWorkflow("fly");
    expect(output).toContain("flyctl deploy");
  });

  it("Test 10: custom CD output contains staging+production structure and placeholder comment", () => {
    const output = generateCDWorkflow("custom");
    expect(output).toContain("environment: staging");
    expect(output).toContain("environment: production");
    expect(output).toContain("# Add your custom deploy command here");
  });

  it("all CD variants have deploy-staging job", () => {
    for (const target of ["railway", "render", "fly", "custom"] as const) {
      expect(generateCDWorkflow(target)).toContain("deploy-staging:");
    }
  });

  it("CI output contains on: with push branches-ignore and pull_request", () => {
    const output = generateCIWorkflow();
    expect(output).toContain("branches-ignore");
    expect(output).toContain("pull_request");
  });
});
