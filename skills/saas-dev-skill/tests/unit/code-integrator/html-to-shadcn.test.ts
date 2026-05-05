import { describe, it, expect, vi, beforeEach } from "vitest";
import type Anthropic from "@anthropic-ai/sdk";
import type { TranslationInput } from "../../../lib/code-integrator/types.js";

// ─── Mock p-retry to execute immediately ─────────────────────────────────────

vi.mock("p-retry", () => ({
  default: vi.fn((fn: () => Promise<unknown>) => fn()),
}));

// Import AFTER mocks are in place
const { translateHtmlToShadcn } = await import(
  "../../../lib/code-integrator/html-to-shadcn.js"
);

// ─── Helpers ──────────────────────────────────────────────────────────────────

function makeInput(overrides: Partial<TranslationInput> = {}): TranslationInput {
  return {
    htmlContent: "<div><button>Click me</button></div>",
    pageName: "TestPage",
    pageRoute: "/test",
    installedComponents: ["button", "card", "tabs"],
    authLevel: "authenticated",
    ...overrides,
  };
}

function makeResponse(content: string) {
  return {
    content: [{ type: "text", text: content }],
  };
}

// ─── Factory: create a mock Anthropic client with a configurable create fn ───

function makeMockClient(
  mockCreate: ReturnType<typeof vi.fn>
): Anthropic {
  return {
    messages: { create: mockCreate },
  } as unknown as Anthropic;
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("translateHtmlToShadcn", () => {
  it("extracts shadcn imports from TSX output", async () => {
    const mockCreate = vi.fn();
    const tsxWithImports = `import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export default function TestPage() {
  return (
    <Layout title="Test">
      <Card><Button>Click</Button></Card>
    </Layout>
  );
}`;
    mockCreate.mockResolvedValueOnce(makeResponse(tsxWithImports));

    const result = await translateHtmlToShadcn(makeInput(), makeMockClient(mockCreate));

    expect(result.extractedImports).toContain("button");
    expect(result.extractedImports).toContain("card");
    expect(result.extractedImports).toHaveLength(2);
  });

  it("detects Layout wrapper", async () => {
    const mockCreate = vi.fn();
    const tsxWithLayout = `import { Layout } from "@/components/layout";

export default function TestPage() {
  return (
    <Layout title="Test">
      <div>content</div>
    </Layout>
  );
}`;
    mockCreate.mockResolvedValueOnce(makeResponse(tsxWithLayout));

    const result = await translateHtmlToShadcn(makeInput(), makeMockClient(mockCreate));

    expect(result.layoutWrapped).toBe(true);
  });

  it("strips markdown fences from output", async () => {
    const mockCreate = vi.fn();
    const tsxWithFences =
      "```tsx\nexport default function Page() {\n  return <div>content</div>;\n}\n```";
    mockCreate.mockResolvedValueOnce(makeResponse(tsxWithFences));

    const result = await translateHtmlToShadcn(makeInput(), makeMockClient(mockCreate));

    expect(result.tsxContent).not.toContain("```");
    expect(result.tsxContent).toContain("export default function Page()");
  });

  it("rejects data-fetching code — final output must not contain useQuery", async () => {
    const mockCreate = vi.fn();

    // First response contains forbidden data-fetching code
    const tsxWithDataFetch = `import { useQuery } from "@tanstack/react-query";
export default function TestPage() {
  const { data } = useQuery({ queryKey: ["/api/test"] });
  return <Layout title="Test"><div>{data}</div></Layout>;
}`;

    // Second response (after retry) is clean
    const cleanTsx = `export default function TestPage() {
  return <Layout title="Test"><div>static content</div></Layout>;
}`;

    mockCreate
      .mockResolvedValueOnce(makeResponse(tsxWithDataFetch))
      .mockResolvedValueOnce(makeResponse(cleanTsx));

    const result = await translateHtmlToShadcn(makeInput(), makeMockClient(mockCreate));

    expect(result.tsxContent).not.toMatch(/useQuery|useMutation|fetch\(|axios\./);
  });

  it("passes correct prompt structure to Claude", async () => {
    const mockCreate = vi.fn();
    const cleanTsx = `import { Layout } from "@/components/layout";
export default function ReportsPage() {
  return <Layout title="Reports"><div>content</div></Layout>;
}`;
    mockCreate.mockResolvedValueOnce(makeResponse(cleanTsx));

    const input = makeInput({
      pageName: "Reports",
      pageRoute: "/reports",
      installedComponents: ["button", "card", "tabs"],
      htmlContent: "<div><h1>Reports</h1></div>",
    });

    await translateHtmlToShadcn(input, makeMockClient(mockCreate));

    expect(mockCreate).toHaveBeenCalledOnce();
    const callArg = mockCreate.mock.calls[0][0];

    // Verify model and max_tokens
    expect(callArg.model).toBe("claude-sonnet-4-5");
    expect(callArg.max_tokens).toBe(8192);

    // Verify user message contains key info
    const userMessage = callArg.messages[0].content;
    expect(userMessage).toContain("Reports");
    expect(userMessage).toContain("/reports");
    expect(userMessage).toContain("button");
    expect(userMessage).toContain("<div><h1>Reports</h1></div>");
  });
});
