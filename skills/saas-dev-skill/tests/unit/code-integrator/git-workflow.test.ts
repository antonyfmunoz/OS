import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mkdtemp, mkdir, writeFile, rm } from "fs/promises";
import { tmpdir } from "os";
import { join } from "path";
import {
  createBranch,
  commitPage,
  pushAndCreatePR,
  detectBaseBranch,
} from "../../../lib/code-integrator/git-workflow.js";
import type { ExecFn } from "../../../lib/code-integrator/git-workflow.js";

// Build a testable execFn from a command->response map
function makeExecFn(
  responses: Record<string, { stdout: string; stderr?: string }>,
): { execFn: ExecFn; calls: string[] } {
  const calls: string[] = [];
  const execFn: ExecFn = async (cmd: string) => {
    calls.push(cmd);
    // Find first matching key (substring match)
    const matchKey = Object.keys(responses).find((k) => cmd.includes(k));
    const response = matchKey ? responses[matchKey] : { stdout: "", stderr: "" };
    return { stdout: response.stdout, stderr: response.stderr ?? "" };
  };
  return { execFn, calls };
}

describe("createBranch", () => {
  it("runs git checkout <base> then git checkout -b <feature>", async () => {
    const { execFn, calls } = makeExecFn({});

    await createBranch("main", "feature/ui-integration", execFn);

    expect(calls[0]).toContain("git checkout main");
    expect(calls[1]).toContain("git checkout -b feature/ui-integration");
  });

  it("uses caller-supplied base and feature branch names", async () => {
    const { execFn, calls } = makeExecFn({});

    await createBranch("feature/company-system", "feature/ui-integration", execFn);

    expect(calls[0]).toContain("git checkout feature/company-system");
    expect(calls[1]).toContain("git checkout -b feature/ui-integration");
  });
});

describe("commitPage", () => {
  it("stages only the specified files with git add (quoted paths)", async () => {
    const { execFn, calls } = makeExecFn({
      "git log": { stdout: "abc1234" },
    });

    const files = [
      "client/src/pages/reports-page.tsx",
      "client/src/App.tsx",
      "client/src/components/sidebar.tsx",
    ];
    await commitPage("Reports", files, execFn);

    expect(calls.some((c) => c.includes('"client/src/pages/reports-page.tsx"'))).toBe(true);
    expect(calls.some((c) => c.includes('"client/src/App.tsx"'))).toBe(true);
    expect(calls.some((c) => c.includes('"client/src/components/sidebar.tsx"'))).toBe(true);
  });

  it("uses correct commit message format feat(ui): integrate {pageName} page", async () => {
    const { execFn, calls } = makeExecFn({
      "git log": { stdout: "abc1234" },
    });

    await commitPage("Reports", ["client/src/App.tsx"], execFn);

    const commitCall = calls.find((c) => c.includes("git commit"));
    expect(commitCall).toBeDefined();
    expect(commitCall).toContain("feat(ui): integrate Reports page");
  });

  it("returns commit hash from git log output", async () => {
    const { execFn } = makeExecFn({
      "git log": { stdout: "abc1234\n" },
    });

    const hash = await commitPage("Reports", ["client/src/App.tsx"], execFn);

    expect(hash).toBe("abc1234");
  });
});

describe("pushAndCreatePR", () => {
  it("runs git push -u origin <featureBranch> and gh pr create", async () => {
    const { execFn, calls } = makeExecFn({
      "gh pr create": { stdout: "https://github.com/user/repo/pull/42" },
    });

    await pushAndCreatePR("feature/ui-integration", ["Reports", "Analytics"], execFn);

    expect(calls.some((c) => c.includes("git push -u origin feature/ui-integration"))).toBe(true);
    expect(calls.some((c) => c.includes("gh pr create"))).toBe(true);
  });

  it("returns the PR URL from gh pr create output", async () => {
    const { execFn } = makeExecFn({
      "gh pr create": { stdout: "https://github.com/user/repo/pull/42\n" },
    });

    const url = await pushAndCreatePR("feature/ui-integration", ["Reports"], execFn);

    expect(url).toBe("https://github.com/user/repo/pull/42");
  });
});

describe("detectBaseBranch", () => {
  let tmpDir: string;

  beforeEach(async () => {
    tmpDir = await mkdtemp(join(tmpdir(), "detect-base-branch-test-"));
  });

  afterEach(async () => {
    await rm(tmpDir, { recursive: true, force: true });
  });

  const eosOptions = {
    markerFiles: [
      "client/src/lib/company-guard.tsx",
      "client/src/hooks/use-company.ts",
    ],
    fallbackBranch: "feature/company-system",
    defaultBranch: "main",
  };

  it("returns defaultBranch when all marker files exist", async () => {
    await mkdir(join(tmpDir, "client/src/lib"), { recursive: true });
    await mkdir(join(tmpDir, "client/src/hooks"), { recursive: true });
    await writeFile(join(tmpDir, "client/src/lib/company-guard.tsx"), "export {};", "utf-8");
    await writeFile(join(tmpDir, "client/src/hooks/use-company.ts"), "export {};", "utf-8");

    const { execFn } = makeExecFn({});
    const result = await detectBaseBranch(tmpDir, eosOptions, execFn);

    expect(result).toBe("main");
  });

  it("returns fallbackBranch when markers absent and the fallback branch exists", async () => {
    const { execFn } = makeExecFn({
      "git branch --list feature/company-system": { stdout: "  feature/company-system\n" },
    });

    const result = await detectBaseBranch(tmpDir, eosOptions, execFn);

    expect(result).toBe("feature/company-system");
  });

  it("returns defaultBranch when markers absent and fallback branch missing", async () => {
    const { execFn } = makeExecFn({
      "git branch --list feature/company-system": { stdout: "" },
    });

    const result = await detectBaseBranch(tmpDir, eosOptions, execFn);

    expect(result).toBe("main");
  });

  it("returns defaultBranch immediately when no markers and no fallback are configured", async () => {
    const { execFn, calls } = makeExecFn({});
    const result = await detectBaseBranch(
      tmpDir,
      { defaultBranch: "main" },
      execFn,
    );

    expect(result).toBe("main");
    expect(calls).toHaveLength(0);
  });
});
