import { describe, it, expect, vi, beforeEach } from "vitest";

const mockMessagesCreate = vi.fn();

vi.mock("@anthropic-ai/sdk", () => ({
  default: vi.fn().mockImplementation(() => ({
    messages: { create: mockMessagesCreate },
  })),
}));

import {
  reviewWithCodex,
  parseCodexReview,
} from "../../../lib/code-integrator/codex-review.js";

function textResponse(text: string): object {
  return { content: [{ type: "text", text }] };
}

beforeEach(() => {
  mockMessagesCreate.mockReset();
});

describe("parseCodexReview", () => {
  it("extracts issues from each severity section", () => {
    const text = `CRITICAL: missing key prop on list
WARNING: hook dependency missing
useEffect deps incomplete
INFO: consider extracting helper`;
    const result = parseCodexReview(text);
    expect(result.passed).toBe(false);
    expect(result.issues.filter((i) => i.severity === "critical")).toHaveLength(1);
    expect(result.issues.filter((i) => i.severity === "warning")).toHaveLength(2);
    expect(result.issues.filter((i) => i.severity === "info")).toHaveLength(1);
  });

  it("passes when no critical issues are present", () => {
    const text = `CRITICAL: none\nWARNING: minor nit\nINFO: tidy`;
    const result = parseCodexReview(text);
    expect(result.passed).toBe(true);
    expect(result.issues).toHaveLength(2);
  });

  it("strips bullet markers", () => {
    const text = `CRITICAL: \n- bad import\n* missing prop\nWARNING:`;
    const result = parseCodexReview(text);
    expect(result.issues.map((i) => i.description)).toEqual([
      "bad import",
      "missing prop",
    ]);
  });

  it("returns empty result for empty text", () => {
    const result = parseCodexReview("");
    expect(result.passed).toBe(true);
    expect(result.issues).toEqual([]);
  });
});

describe("reviewWithCodex", () => {
  it("returns parsed result on success", async () => {
    mockMessagesCreate.mockResolvedValue(
      textResponse("CRITICAL: uses fetch directly\nWARNING:\nINFO:")
    );
    const result = await reviewWithCodex("const x = fetch('/api')", "Dashboard");
    expect(result.passed).toBe(false);
    expect(result.issues[0].description).toContain("fetch");
  });

  it("fails open on API error", async () => {
    mockMessagesCreate.mockRejectedValue(new Error("nope"));
    const result = await reviewWithCodex("// code", "Page");
    expect(result.passed).toBe(true);
    expect(result.issues).toEqual([]);
  });

  it("fails open when content block is not text", async () => {
    mockMessagesCreate.mockResolvedValue({ content: [{ type: "tool_use" }] });
    const result = await reviewWithCodex("// code", "Page");
    expect(result.passed).toBe(true);
  });
});
