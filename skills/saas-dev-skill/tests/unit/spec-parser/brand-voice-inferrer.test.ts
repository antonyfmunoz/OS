import { describe, it, expect, vi, beforeEach } from "vitest";
import fs from "node:fs";
import path from "node:path";

// ─── Mock Anthropic SDK ───────────────────────────────────────────────────────

const mockMessagesCreate = vi.fn();

vi.mock("@anthropic-ai/sdk", () => {
  return {
    default: vi.fn().mockImplementation(() => ({
      messages: {
        create: mockMessagesCreate,
      },
    })),
  };
});

// ─── Import under test ────────────────────────────────────────────────────────

import { inferBrandVoice, loadBrandVoice } from "../../../lib/spec-parser/brand-voice-inferrer.js";

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("inferBrandVoice", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns brand voice content when Claude responds successfully", async () => {
    mockMessagesCreate.mockResolvedValueOnce({
      content: [{ type: "text", text: "## Tone\nProfessional and authoritative." }],
    });

    const tmpDir = path.join(process.cwd(), "tests", "tmp-brand-voice-" + Date.now());
    try {
      const result = await inferBrandVoice("# My PRD\nA SaaS product.", tmpDir);

      expect(result).not.toBeNull();
      expect(result!.content).toContain("Professional and authoritative");
      expect(result!.sourcePath).toBe(path.join(tmpDir, "BRAND-VOICE.md"));
      expect(fs.existsSync(result!.sourcePath)).toBe(true);
      expect(fs.readFileSync(result!.sourcePath, "utf-8")).toContain("Professional");
    } finally {
      if (fs.existsSync(tmpDir)) {
        fs.rmSync(tmpDir, { recursive: true, force: true });
      }
    }
  });

  it("returns null and logs warning when Claude API fails", async () => {
    mockMessagesCreate.mockRejectedValueOnce(new Error("API rate limited"));

    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    const result = await inferBrandVoice("# PRD", "/tmp/nonexistent-brand-voice");

    expect(result).toBeNull();
    expect(warnSpy).toHaveBeenCalledWith(
      expect.stringContaining("Failed to infer brand voice"),
    );
    warnSpy.mockRestore();
  });

  it("returns null when Claude returns empty text", async () => {
    mockMessagesCreate.mockResolvedValueOnce({
      content: [{ type: "text", text: "" }],
    });

    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    const result = await inferBrandVoice("# PRD", "/tmp/nonexistent-brand-voice");

    expect(result).toBeNull();
    expect(warnSpy).toHaveBeenCalledWith(
      expect.stringContaining("empty response"),
    );
    warnSpy.mockRestore();
  });

  it("uses claude-haiku-4-5 model for cost efficiency", async () => {
    mockMessagesCreate.mockResolvedValueOnce({
      content: [{ type: "text", text: "## Tone\nMinimal." }],
    });

    const tmpDir = path.join(process.cwd(), "tests", "tmp-brand-voice-model-" + Date.now());
    try {
      await inferBrandVoice("# PRD", tmpDir);

      expect(mockMessagesCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          model: "claude-haiku-4-5-20251001",
        }),
      );
    } finally {
      if (fs.existsSync(tmpDir)) {
        fs.rmSync(tmpDir, { recursive: true, force: true });
      }
    }
  });
});

describe("loadBrandVoice", () => {
  it("returns null when BRAND-VOICE.md does not exist", () => {
    const result = loadBrandVoice("/tmp/nonexistent-dir-" + Date.now());
    expect(result).toBeNull();
  });

  it("returns content when BRAND-VOICE.md exists", () => {
    const tmpDir = path.join(process.cwd(), "tests", "tmp-load-bv-" + Date.now());
    try {
      fs.mkdirSync(tmpDir, { recursive: true });
      fs.writeFileSync(path.join(tmpDir, "BRAND-VOICE.md"), "## Tone\nBold.", "utf-8");

      const result = loadBrandVoice(tmpDir);
      expect(result).toBe("## Tone\nBold.");
    } finally {
      if (fs.existsSync(tmpDir)) {
        fs.rmSync(tmpDir, { recursive: true, force: true });
      }
    }
  });

  it("returns null when BRAND-VOICE.md is empty", () => {
    const tmpDir = path.join(process.cwd(), "tests", "tmp-load-bv-empty-" + Date.now());
    try {
      fs.mkdirSync(tmpDir, { recursive: true });
      fs.writeFileSync(path.join(tmpDir, "BRAND-VOICE.md"), "", "utf-8");

      const result = loadBrandVoice(tmpDir);
      expect(result).toBeNull();
    } finally {
      if (fs.existsSync(tmpDir)) {
        fs.rmSync(tmpDir, { recursive: true, force: true });
      }
    }
  });
});
