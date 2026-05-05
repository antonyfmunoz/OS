import { describe, it, expect, vi, beforeEach } from "vitest";

// ─── Mock orchestrator DB ────────────────────────────────────────────────────

const mockGetPagesForPhase = vi.fn();
const mockCreatePage = vi.fn();
const mockUpdatePage = vi.fn();

vi.mock("../../../lib/orchestrator/db.js", () => ({
  getPagesForPhase: (...args: unknown[]) => mockGetPagesForPhase(...args),
  createPage: (...args: unknown[]) => mockCreatePage(...args),
  updatePage: (...args: unknown[]) => mockUpdatePage(...args),
}));

// ─── Import under test ────────────────────────────────────────────────────────

import { runPhase } from "../../../lib/orchestrator/phase-runner.js";
import type { PhaseImplementation, PageWorkUnit, PageCompleteContext, PageDecision } from "../../../lib/orchestrator/phase-runner.js";
import type { ProjectConfig } from "../../../shared/design-schema.js";

// ─── Helpers ──────────────────────────────────────────────────────────────────

const stubConfig: ProjectConfig = {
  projectId: "test-proj",
  repoPath: "/tmp/test",
  framework: "react-vite-tailwind-shadcn",
  designSystemPath: ".planning/design-system.md",
  outputPath: ".planning/output",
  clientSrcPath: "client/src",
  serverPath: "server",
  defaultBranch: "main",
  featureBranchPrefix: "feature/",
};

function makePage(overrides: Partial<{ id: number; pageIndex: number; status: string }> = {}) {
  return {
    id: overrides.id ?? 1,
    runId: 1,
    projectId: "test-proj",
    pageName: "TestPage",
    pageIndex: overrides.pageIndex ?? 0,
    phase: "react-gen",
    status: overrides.status ?? "pending",
    error: null,
    output: null,
    startedAt: null,
    completedAt: null,
  };
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("phase-runner onPageComplete hook", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUpdatePage.mockResolvedValue(undefined);
  });

  it("calls onPageComplete after successful runPage and continues on 'continue'", async () => {
    const onPageComplete = vi.fn().mockResolvedValue({ action: "continue" } as PageDecision);
    const impl: PhaseImplementation = {
      prepare: vi.fn().mockResolvedValue([
        { pageName: "Page1", pageIndex: 0, input: {} },
      ] as PageWorkUnit[]),
      runPage: vi.fn().mockResolvedValue({ htmlUrl: "http://test.com" }),
      onPageComplete,
    };

    mockGetPagesForPhase.mockResolvedValue([]);
    mockCreatePage.mockResolvedValue(makePage());

    const result = await runPhase(1, "react-gen", impl, stubConfig);

    expect(onPageComplete).toHaveBeenCalledTimes(1);
    expect(onPageComplete).toHaveBeenCalledWith(
      { pageName: "Page1", pageIndex: 0, output: { htmlUrl: "http://test.com" } },
      stubConfig,
    );
    expect(result.completedPages).toBe(1);
  });

  it("retries runPage once when onPageComplete returns 'retry'", async () => {
    const onPageComplete = vi.fn().mockResolvedValue({ action: "retry", feedback: "fix colors" } as PageDecision);
    const runPage = vi.fn()
      .mockResolvedValueOnce({ version: 1 })
      .mockResolvedValueOnce({ version: 2 });
    const impl: PhaseImplementation = {
      prepare: vi.fn().mockResolvedValue([
        { pageName: "Page1", pageIndex: 0, input: {} },
      ] as PageWorkUnit[]),
      runPage,
      onPageComplete,
    };

    mockGetPagesForPhase.mockResolvedValue([]);
    mockCreatePage.mockResolvedValue(makePage());

    const result = await runPhase(1, "react-gen", impl, stubConfig);

    expect(runPage).toHaveBeenCalledTimes(2);
    expect(result.completedPages).toBe(1);
    // The output should be from the retry (version 2)
    expect(mockUpdatePage).toHaveBeenCalledWith(1, expect.objectContaining({
      status: "complete",
      output: JSON.stringify({ version: 2 }),
    }));
  });

  it("marks page as skipped when onPageComplete returns 'skip'", async () => {
    const onPageComplete = vi.fn().mockResolvedValue({ action: "skip" } as PageDecision);
    const impl: PhaseImplementation = {
      prepare: vi.fn().mockResolvedValue([
        { pageName: "Page1", pageIndex: 0, input: {} },
      ] as PageWorkUnit[]),
      runPage: vi.fn().mockResolvedValue({ htmlUrl: "http://test.com" }),
      onPageComplete,
    };

    mockGetPagesForPhase.mockResolvedValue([]);
    mockCreatePage.mockResolvedValue(makePage());

    const result = await runPhase(1, "react-gen", impl, stubConfig);

    expect(result.completedPages).toBe(1);
    expect(mockUpdatePage).toHaveBeenCalledWith(1, expect.objectContaining({
      status: "complete",
      output: JSON.stringify({ skipped: true }),
    }));
  });

  it("does not call onPageComplete when hook is absent", async () => {
    const impl: PhaseImplementation = {
      prepare: vi.fn().mockResolvedValue([
        { pageName: "Page1", pageIndex: 0, input: {} },
      ] as PageWorkUnit[]),
      runPage: vi.fn().mockResolvedValue({ data: "ok" }),
    };

    mockGetPagesForPhase.mockResolvedValue([]);
    mockCreatePage.mockResolvedValue(makePage());

    const result = await runPhase(1, "react-gen", impl, stubConfig);

    expect(result.completedPages).toBe(1);
    expect(mockUpdatePage).toHaveBeenCalledWith(1, expect.objectContaining({
      status: "complete",
      output: JSON.stringify({ data: "ok" }),
    }));
  });

  it("works with multiple pages — hook called per page", async () => {
    const decisions: PageDecision[] = [
      { action: "continue" },
      { action: "skip" },
      { action: "continue" },
    ];
    let callIdx = 0;
    const onPageComplete = vi.fn().mockImplementation(() => {
      return Promise.resolve(decisions[callIdx++]);
    });

    const impl: PhaseImplementation = {
      prepare: vi.fn().mockResolvedValue([
        { pageName: "P1", pageIndex: 0, input: {} },
        { pageName: "P2", pageIndex: 1, input: {} },
        { pageName: "P3", pageIndex: 2, input: {} },
      ] as PageWorkUnit[]),
      runPage: vi.fn().mockResolvedValue({ ok: true }),
      onPageComplete,
    };

    mockGetPagesForPhase.mockResolvedValue([]);
    let pageId = 1;
    mockCreatePage.mockImplementation(() => Promise.resolve(makePage({ id: pageId++, pageIndex: pageId - 2 })));

    const result = await runPhase(1, "react-gen", impl, stubConfig);

    expect(onPageComplete).toHaveBeenCalledTimes(3);
    expect(result.completedPages).toBe(3);
    expect(result.totalPages).toBe(3);
  });
});
