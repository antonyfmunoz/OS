import { describe, it, expect, vi, beforeEach } from "vitest";

const mockMessagesCreate = vi.fn();

vi.mock("@anthropic-ai/sdk", () => ({
  default: vi.fn().mockImplementation(() => ({
    messages: { create: mockMessagesCreate },
  })),
}));

import {
  adversarialReview,
  parseAdversarialReview,
} from "../../../lib/backend-wirer/codex-adversarial.js";

function textResponse(text: string): object {
  return { content: [{ type: "text", text }] };
}

beforeEach(() => {
  mockMessagesCreate.mockReset();
});

describe("parseAdversarialReview", () => {
  it("parses findings across severity buckets", () => {
    const text = `CRITICAL:
sql-injection | raw query in /users endpoint | use parameterized query

HIGH:
auth-bypass | missing isAuthenticated check on /admin | add middleware

MEDIUM:
input-validation | optional body field not validated | extend Zod schema

LOW:
none`;
    const result = parseAdversarialReview(text);
    expect(result.passed).toBe(false);
    expect(result.findings).toHaveLength(3);
    expect(result.findings[0]).toMatchObject({
      severity: "critical",
      category: "sql-injection",
    });
    expect(result.findings[1]).toMatchObject({
      severity: "high",
      category: "auth-bypass",
    });
    expect(result.findings[2].severity).toBe("medium");
  });

  it("passes when only medium/low findings exist", () => {
    const text = `CRITICAL:
none
HIGH:
none
MEDIUM:
input-validation | foo | bar
LOW:
other | trivial nit | ignore`;
    const result = parseAdversarialReview(text);
    expect(result.passed).toBe(true);
    expect(result.findings).toHaveLength(2);
  });

  it("normalises unknown categories to 'other'", () => {
    const text = `CRITICAL:
weird-category | something | mitigate it`;
    const result = parseAdversarialReview(text);
    expect(result.findings[0].category).toBe("other");
  });

  it("returns empty result for empty text", () => {
    const result = parseAdversarialReview("");
    expect(result.passed).toBe(true);
    expect(result.findings).toEqual([]);
  });
});

describe("adversarialReview", () => {
  const baseInput = {
    routes: [{ method: "GET", path: "/api/x", code: "app.get(...)" }],
    schema: [
      {
        tableName: "x",
        drizzleCode: "pgTable('x', ...)",
        zodInsertCode: "",
        typeExportCode: "",
      },
    ],
    storage: [{ code: "async getX() {}" }],
  };

  it("returns parsed findings on success", async () => {
    mockMessagesCreate.mockResolvedValue(
      textResponse(
        `CRITICAL:\nsql-injection | raw query | parameterize\nHIGH:\nnone\nMEDIUM:\nnone\nLOW:\nnone`
      )
    );
    const result = await adversarialReview(baseInput);
    expect(result.passed).toBe(false);
    expect(result.findings).toHaveLength(1);
  });

  it("fails open on API error", async () => {
    mockMessagesCreate.mockRejectedValue(new Error("rate limit"));
    const result = await adversarialReview(baseInput);
    expect(result.passed).toBe(true);
    expect(result.findings).toEqual([]);
  });
});
