import { describe, it, expect, vi, beforeEach } from "vitest";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const TMP = fs.mkdtempSync(path.join(os.tmpdir(), "screenshot-reviewer-test-"));

// ─── Mock Playwright ────────────────────────────────────────────────────────

const mockScreenshot = vi.fn().mockResolvedValue(undefined);
const mockGoto = vi.fn().mockResolvedValue(undefined);
const mockClose = vi.fn().mockResolvedValue(undefined);

vi.mock("playwright", () => ({
  chromium: {
    launch: vi.fn().mockResolvedValue({
      newContext: vi.fn().mockResolvedValue({
        newPage: vi.fn().mockResolvedValue({
          goto: mockGoto,
          screenshot: mockScreenshot,
        }),
      }),
      close: mockClose,
    }),
  },
}));

// ─── Mock Anthropic SDK ─────────────────────────────────────────────────────

const mockCreate = vi.fn();

vi.mock("@anthropic-ai/sdk", () => ({
  default: class {
    messages = { create: mockCreate };
  },
}));

vi.mock("../../../lib/env.js", () => ({
  getAnthropicApiKey: () => "sk-test",
  getAnthropicBaseUrl: () => "https://api.anthropic.com",
}));

import { screenshotAndReview } from "../../../lib/react-gen/screenshot-reviewer.js";

beforeEach(() => {
  vi.clearAllMocks();
  // Make screenshot write a dummy file so readFileSync works
  mockScreenshot.mockImplementation(async (opts: { path: string }) => {
    fs.mkdirSync(path.dirname(opts.path), { recursive: true });
    fs.writeFileSync(opts.path, Buffer.from("fake-png-data"));
  });
});

describe("screenshotAndReview", () => {
  it("returns passing score from Claude vision review", async () => {
    mockCreate.mockResolvedValueOnce({
      content: [{ type: "text", text: '{ "score": 0.85, "issues": [] }' }],
    });

    const result = await screenshotAndReview({
      url: "http://localhost:5173/dashboard",
      pageName: "Dashboard",
      designSystem: "# Design System",
      projectRoot: TMP,
    });

    expect(result.score).toBe(0.85);
    expect(result.issues).toEqual([]);
    expect(result.screenshotPath).toContain("dashboard.png");
  });

  it("returns issues from Claude vision review", async () => {
    mockCreate.mockResolvedValueOnce({
      content: [{ type: "text", text: '{ "score": 0.4, "issues": ["Uses gradient on header", "Pure black text detected"] }' }],
    });

    const result = await screenshotAndReview({
      url: "http://localhost:5173/login",
      pageName: "Login",
      designSystem: "",
      projectRoot: TMP,
    });

    expect(result.score).toBe(0.4);
    expect(result.issues).toHaveLength(2);
    expect(result.issues[0]).toContain("gradient");
  });

  it("handles Claude vision API failure gracefully", async () => {
    mockCreate.mockRejectedValueOnce(new Error("API rate limited"));

    const result = await screenshotAndReview({
      url: "http://localhost:5173/settings",
      pageName: "Settings",
      designSystem: "",
      projectRoot: TMP,
    });

    // Should not throw — returns a conservative score to trigger regeneration
    expect(result.score).toBe(0.5);
    expect(result.issues[0]).toContain("Vision review failed");
  });

  it("creates screenshot directory if missing", async () => {
    mockCreate.mockResolvedValueOnce({
      content: [{ type: "text", text: '{ "score": 0.9, "issues": [] }' }],
    });

    const freshTmp = fs.mkdtempSync(path.join(os.tmpdir(), "ss-dir-test-"));
    await screenshotAndReview({
      url: "http://localhost:5173/test",
      pageName: "Test",
      designSystem: "",
      projectRoot: freshTmp,
    });

    expect(fs.existsSync(path.join(freshTmp, ".planning", "output", "screenshots"))).toBe(true);
    fs.rmSync(freshTmp, { recursive: true, force: true });
  });

  it("closes browser even on navigation error", async () => {
    mockGoto.mockRejectedValueOnce(new Error("Navigation timeout"));

    const result = await screenshotAndReview({
      url: "http://localhost:5173/broken",
      pageName: "Broken",
      designSystem: "",
      projectRoot: TMP,
    });

    expect(mockClose).toHaveBeenCalledTimes(1);
    expect(result.score).toBe(0.5); // Conservative fallback triggers regeneration
  });

  it("clamps score to 0-1 range", async () => {
    mockCreate.mockResolvedValueOnce({
      content: [{ type: "text", text: '{ "score": 1.5, "issues": [] }' }],
    });

    const result = await screenshotAndReview({
      url: "http://localhost:5173/test",
      pageName: "TestClamp",
      designSystem: "",
      projectRoot: TMP,
    });

    expect(result.score).toBe(1);
  });
});
