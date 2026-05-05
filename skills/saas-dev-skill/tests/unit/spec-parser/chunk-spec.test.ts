import { describe, it, expect } from "vitest";
import type { PageSpecFull } from "@shared/spec-schema";

// ─── Fixture Helpers ──────────────────────────────────────────────────────────

/**
 * Creates a minimal valid PageSpecFull for testing.
 * Only route matters for domain classification tests.
 */
function makePage(route: string, priority = 2): PageSpecFull {
  return {
    name: route.replace(/\//g, "").replace(/-/g, "") || "Home",
    route,
    purpose: `Page at ${route}`,
    components: [],
    authLevel: "authenticated",
    priority,
    dependsOn: [],
    specVersion: 1,
    source: "inferred",
    dataRequirements: [],
    apiEndpoints: [],
    validationRules: [],
    events: [],
    featureFlagCandidates: [],
  };
}

/**
 * Creates N pages with sequential routes like /feature/1, /feature/2...
 */
function makePages(count: number, prefix = "/feature"): PageSpecFull[] {
  return Array.from({ length: count }, (_, i) => makePage(`${prefix}/${i + 1}`));
}

// ─── chunkSpecByDomain tests ──────────────────────────────────────────────────

describe("chunkSpecByDomain", () => {
  it("returns single chunk for 25 or fewer pages (D-24 threshold)", async () => {
    const { chunkSpecByDomain } = await import(
      "../../../lib/spec-parser/chunk-spec.js"
    );
    const pages = makePages(25);
    const chunks = chunkSpecByDomain(pages);
    expect(chunks.length).toBe(1);
    expect(chunks[0].length).toBe(25);
  });

  it("returns single chunk for exactly 25 pages", async () => {
    const { chunkSpecByDomain } = await import(
      "../../../lib/spec-parser/chunk-spec.js"
    );
    const pages = makePages(25);
    const chunks = chunkSpecByDomain(pages);
    expect(chunks).toHaveLength(1);
  });

  it("splits 30 pages into multiple chunks (D-25 threshold exceeded)", async () => {
    const { chunkSpecByDomain } = await import(
      "../../../lib/spec-parser/chunk-spec.js"
    );
    const pages = makePages(30);
    const chunks = chunkSpecByDomain(pages);
    expect(chunks.length).toBeGreaterThan(1);
    // Each chunk should have roughly equal distribution
    chunks.forEach((chunk) => {
      expect(chunk.length).toBeGreaterThan(0);
    });
  });

  it("groups auth-related pages together (routes containing /auth, /login, /signup)", async () => {
    const { chunkSpecByDomain } = await import(
      "../../../lib/spec-parser/chunk-spec.js"
    );
    const authPages = [
      makePage("/auth/callback"),
      makePage("/login"),
      makePage("/signup"),
      makePage("/forgot-password"),
      makePage("/verify-email"),
    ];
    // Mix with 26 other pages to trigger chunking
    const otherPages = makePages(26);
    const allPages = [...authPages, ...otherPages];
    const chunks = chunkSpecByDomain(allPages);
    // Find the chunk that contains auth pages
    const authChunk = chunks.find((chunk) =>
      chunk.some((p) => p.route === "/login")
    );
    expect(authChunk).toBeDefined();
    // Auth pages should be in the same chunk
    const authRoutes = authChunk?.map((p) => p.route);
    expect(authRoutes).toContain("/login");
    expect(authRoutes).toContain("/signup");
  });

  it("groups admin pages together (routes containing /admin or /settings)", async () => {
    const { chunkSpecByDomain } = await import(
      "../../../lib/spec-parser/chunk-spec.js"
    );
    const adminPages = [
      makePage("/admin/users"),
      makePage("/admin/billing"),
      makePage("/settings/profile"),
      makePage("/settings/security"),
    ];
    // Mix with 26 other pages to trigger chunking
    const otherPages = makePages(26);
    const allPages = [...adminPages, ...otherPages];
    const chunks = chunkSpecByDomain(allPages);
    // Find the chunk that contains admin pages
    const adminChunk = chunks.find((chunk) =>
      chunk.some((p) => p.route === "/admin/users")
    );
    expect(adminChunk).toBeDefined();
    const adminRoutes = adminChunk?.map((p) => p.route);
    expect(adminRoutes).toContain("/admin/users");
    expect(adminRoutes).toContain("/admin/billing");
  });

  it("never produces a chunk larger than 20 pages", async () => {
    const { chunkSpecByDomain } = await import(
      "../../../lib/spec-parser/chunk-spec.js"
    );
    // Test with many pages in a single domain
    const pages = makePages(60);
    const chunks = chunkSpecByDomain(pages);
    chunks.forEach((chunk) => {
      expect(chunk.length).toBeLessThanOrEqual(20);
    });
  });

  it("preserves all input pages across chunks (no page lost)", async () => {
    const { chunkSpecByDomain } = await import(
      "../../../lib/spec-parser/chunk-spec.js"
    );
    const pages = makePages(50);
    const chunks = chunkSpecByDomain(pages);
    const allRoutes = chunks.flatMap((chunk) => chunk.map((p) => p.route));
    const originalRoutes = pages.map((p) => p.route);
    // Every original page should appear in exactly one chunk
    expect(allRoutes.length).toBe(originalRoutes.length);
    originalRoutes.forEach((route) => {
      expect(allRoutes).toContain(route);
    });
  });
});

// ─── chunkRawText tests ───────────────────────────────────────────────────────

describe("chunkRawText", () => {
  it("returns single chunk for text under 15000 chars", async () => {
    const { chunkRawText } = await import(
      "../../../lib/spec-parser/chunk-spec.js"
    );
    const smallText = "# Section 1\n\nSome content here.\n\n# Section 2\n\nMore content.";
    const chunks = chunkRawText(smallText);
    expect(chunks).toHaveLength(1);
    expect(chunks[0]).toBe(smallText);
  });

  it("splits text with markdown headings into sections when over limit", async () => {
    const { chunkRawText } = await import(
      "../../../lib/spec-parser/chunk-spec.js"
    );
    // Build a text with clear heading sections that exceeds 15000 chars
    const section1 = "# Section One\n\n" + "Content line A.\n".repeat(500);
    const section2 = "# Section Two\n\n" + "Content line B.\n".repeat(500);
    const text = section1 + section2;
    expect(text.length).toBeGreaterThan(15000);
    const chunks = chunkRawText(text);
    expect(chunks.length).toBeGreaterThan(1);
  });

  it("splits at heading boundaries (# or ## lines), not mid-paragraph", async () => {
    const { chunkRawText } = await import(
      "../../../lib/spec-parser/chunk-spec.js"
    );
    const section1 = "# Auth Pages\n\n" + "x".repeat(8000);
    const section2 = "## Dashboard Section\n\n" + "y".repeat(8000);
    const text = section1 + "\n" + section2;
    const chunks = chunkRawText(text, 10000);
    // Each chunk should start at a heading boundary, not mid-content
    chunks.forEach((chunk) => {
      const trimmed = chunk.trim();
      if (trimmed.length > 0) {
        // The chunk should start with content from its section start
        // (no chunk should contain only partial heading text)
        expect(trimmed).not.toMatch(/^x+$/); // shouldn't be raw content without heading
      }
    });
    // Check that sections aren't cut mid-way through — each section content should be in one chunk
    const hasSection1Content = chunks.some((c) => c.includes("Auth Pages"));
    const hasSection2Content = chunks.some((c) => c.includes("Dashboard Section"));
    expect(hasSection1Content).toBe(true);
    expect(hasSection2Content).toBe(true);
  });

  it("preserves all input text across chunks (no content lost)", async () => {
    const { chunkRawText } = await import(
      "../../../lib/spec-parser/chunk-spec.js"
    );
    const sections = Array.from(
      { length: 10 },
      (_, i) => `# Section ${i + 1}\n\n${"Content line.\n".repeat(200)}`
    );
    const text = sections.join("\n");
    expect(text.length).toBeGreaterThan(15000);
    const chunks = chunkRawText(text);
    const reconstructed = chunks.join("");
    // All original content should be present (allow for whitespace trimming at boundaries)
    expect(reconstructed.replace(/\s+/g, " ").trim()).toBe(
      text.replace(/\s+/g, " ").trim()
    );
  });
});
