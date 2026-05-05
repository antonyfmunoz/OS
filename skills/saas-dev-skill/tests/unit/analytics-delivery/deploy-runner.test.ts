import { describe, it, expect, vi } from "vitest";
import type { ExecSyncOptionsWithStringEncoding } from "child_process";
import { checkCLIAvailable, preflightDeploy, runDeploy } from "../../../lib/analytics-delivery/deploy-runner.js";

// ─── Helpers ───────────────────────────────────────────────────────────────────

function makeExecFn(throws: boolean = false, output: string = ""): typeof import("child_process").execSync {
  return vi.fn((cmd: string, opts?: ExecSyncOptionsWithStringEncoding) => {
    if (throws) throw new Error("command not found");
    return output as any;
  }) as any;
}

// ─── checkCLIAvailable ────────────────────────────────────────────────────────

describe("checkCLIAvailable", () => {
  it("Test 1: returns true when execSync succeeds for railway", () => {
    const execFn = makeExecFn(false);
    const result = checkCLIAvailable("railway", execFn);
    expect(result).toBe(true);
  });

  it("Test 2: returns false when execSync throws for railway", () => {
    const execFn = makeExecFn(true);
    const result = checkCLIAvailable("railway", execFn);
    expect(result).toBe(false);
  });

  it("Test 3: always returns true for custom target (no CLI needed)", () => {
    const execFn = makeExecFn(true); // even if it would throw, custom returns true
    const result = checkCLIAvailable("custom", execFn);
    expect(result).toBe(true);
  });
});

// ─── preflightDeploy ──────────────────────────────────────────────────────────

describe("preflightDeploy", () => {
  it("Test 4: returns ready=true when RAILWAY_TOKEN present and CLI available", () => {
    const execFn = makeExecFn(false);
    const env = { RAILWAY_TOKEN: "token-abc" };
    const result = preflightDeploy("railway", env, execFn);
    expect(result.ready).toBe(true);
    expect(result.missingSecrets).toEqual([]);
    expect(result.missingCLI).toEqual([]);
    expect(result.warnings).toEqual([]);
  });

  it("Test 5: returns ready=false with missingSecrets when RAILWAY_TOKEN absent", () => {
    const execFn = makeExecFn(false);
    const env: Record<string, string | undefined> = {};
    const result = preflightDeploy("railway", env, execFn);
    expect(result.ready).toBe(false);
    expect(result.missingSecrets).toContain("RAILWAY_TOKEN");
  });

  it("Test 6: returns ready=false with missingCLI when flyctl unavailable", () => {
    const execFn = makeExecFn(true); // CLI not found
    const env = { FLY_API_TOKEN: "fly-token" };
    const result = preflightDeploy("fly", env, execFn);
    expect(result.ready).toBe(false);
    expect(result.missingCLI).toContain("flyctl");
  });

  it("Test 7: returns ready=false with missingSecrets when RENDER_DEPLOY_HOOK_URL absent", () => {
    const execFn = makeExecFn(false); // curl available
    const env: Record<string, string | undefined> = {};
    const result = preflightDeploy("render", env, execFn);
    expect(result.ready).toBe(false);
    expect(result.missingSecrets).toContain("RENDER_DEPLOY_HOOK_URL");
  });
});

// ─── runDeploy ────────────────────────────────────────────────────────────────

describe("runDeploy", () => {
  it("Test 8: returns skipped outcome when confirmed=false", () => {
    const execFn = makeExecFn(false);
    const result = runDeploy("railway", false, {}, execFn);
    expect(result.outcome).toBe("skipped");
    expect(result.confirmed).toBe(false);
    expect(result.executed).toBe(false);
  });

  it("Test 9: calls execSync with 'railway up' when railway confirmed and preflight passes", () => {
    const execFn = makeExecFn(false);
    const env = { RAILWAY_TOKEN: "token-abc" };
    runDeploy("railway", true, { env }, execFn);
    expect(execFn).toHaveBeenCalled();
    const calledCmd = (execFn as any).mock.calls[0][0] as string;
    // First call is the which/where CLI check, second is the actual deploy
    const deployCmdCall = (execFn as any).mock.calls.find((c: any[]) => (c[0] as string).includes("railway up"));
    expect(deployCmdCall).toBeDefined();
  });

  it("Test 10: returns failed-preflight when RAILWAY_TOKEN missing", () => {
    const execFn = makeExecFn(false); // CLI check succeeds, but secret missing
    const env: Record<string, string | undefined> = {};
    const result = runDeploy("railway", true, { env }, execFn);
    expect(result.outcome).toBe("failed-preflight");
    expect(result.error).toContain("RAILWAY_TOKEN");
  });

  it("Test 11: calls execSync with 'flyctl deploy --remote-only' for fly target", () => {
    const execFn = makeExecFn(false);
    const env = { FLY_API_TOKEN: "fly-token" };
    runDeploy("fly", true, { env }, execFn);
    const deployCmdCall = (execFn as any).mock.calls.find((c: any[]) => (c[0] as string).includes("flyctl deploy --remote-only"));
    expect(deployCmdCall).toBeDefined();
  });

  it("Test 12: calls execSync with curl to RENDER_DEPLOY_HOOK_URL for render target", () => {
    const execFn = makeExecFn(false);
    const env = { RENDER_DEPLOY_HOOK_URL: "https://api.render.com/deploy/srv-xxx?key=yyy" };
    runDeploy("render", true, { env }, execFn);
    const deployCmdCall = (execFn as any).mock.calls.find((c: any[]) => (c[0] as string).includes("https://api.render.com/deploy/srv-xxx"));
    expect(deployCmdCall).toBeDefined();
  });

  it("Test 13: calls execSync with custom script when target is custom", () => {
    const execFn = makeExecFn(false);
    const result = runDeploy("custom", true, { customScript: "./deploy.sh" }, execFn);
    const deployCmdCall = (execFn as any).mock.calls.find((c: any[]) => (c[0] as string).includes("./deploy.sh"));
    expect(deployCmdCall).toBeDefined();
    expect(result.outcome).toBe("deployed");
  });

  it("Test 14: returns failed-preflight with install instructions when CLI not available", () => {
    // CLI check (which) throws, meaning binary not found
    const execFn = makeExecFn(true);
    const env = { RAILWAY_TOKEN: "token-abc" };
    const result = runDeploy("railway", true, { env }, execFn);
    expect(result.outcome).toBe("failed-preflight");
    expect(result.error).toContain("railway");
  });

  it("Test 15: returns failed-runtime when execSync throws during deploy execution", () => {
    let callCount = 0;
    const execFn = vi.fn((cmd: string) => {
      callCount++;
      // First call is the CLI check (which railway) — let it succeed
      if (typeof cmd === "string" && (cmd.includes("which") || cmd.includes("where"))) {
        return "" as any;
      }
      // Second call is the deploy command — throw runtime error
      throw new Error("Deploy failed: connection refused");
    }) as any;

    const env = { RAILWAY_TOKEN: "token-abc" };
    const result = runDeploy("railway", true, { env }, execFn);
    expect(result.outcome).toBe("failed-runtime");
    expect(result.error).toContain("Deploy failed");
  });
});
