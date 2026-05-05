import { describe, it, expect, vi, beforeEach } from "vitest";
import { BackendSpecSchema } from "@shared/spec-schema";
import type { PageSpecFull } from "@shared/spec-schema";

// ─── Mock Anthropic SDK ───────────────────────────────────────────────────────

const mockCreate = vi.fn();

vi.mock("@anthropic-ai/sdk", () => ({
  default: vi.fn().mockImplementation(() => ({
    messages: {
      create: mockCreate,
    },
  })),
}));

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const authenticatedPage: PageSpecFull = {
  name: "Dashboard",
  route: "/dashboard",
  purpose: "Main dashboard showing user analytics",
  components: ["StatsCard", "ActivityFeed"],
  authLevel: "authenticated",
  priority: 2,
  dependsOn: ["/login"],
  specVersion: 1,
  source: "explicit",
  dataRequirements: [
    {
      component: "StatsCard",
      fields: ["totalUsers", "revenue", "activeProjects"],
    },
    {
      component: "ActivityFeed",
      fields: ["recentActions", "timestamp"],
    },
  ],
  apiEndpoints: [
    { endpoint: "/api/stats", source: "explicit" },
  ],
  validationRules: [],
  events: [],
  featureFlagCandidates: [],
};

const publicPage: PageSpecFull = {
  name: "Login",
  route: "/login",
  purpose: "Authentication page",
  components: ["LoginForm"],
  authLevel: "public",
  priority: 1,
  dependsOn: [],
  specVersion: 1,
  source: "inferred",
  dataRequirements: [
    {
      component: "LoginForm",
      fields: ["email", "password"],
    },
  ],
  apiEndpoints: [],
  validationRules: ["email must be valid", "password min 8 chars"],
  events: [],
  featureFlagCandidates: [],
};

const adminPage: PageSpecFull = {
  name: "AdminPanel",
  route: "/admin",
  purpose: "Admin control panel",
  components: ["UserTable", "AuditLog"],
  authLevel: "admin",
  priority: 4,
  dependsOn: ["/dashboard"],
  specVersion: 1,
  source: "explicit",
  dataRequirements: [
    {
      component: "UserTable",
      fields: ["id", "email", "role", "createdAt"],
    },
  ],
  apiEndpoints: [],
  validationRules: [],
  events: [],
  featureFlagCandidates: [],
};

const mockBackendSpec = {
  endpoints: [
    {
      method: "GET",
      path: "/api/stats",
      description: "Get stats for StatsCard component",
      requestBody: [],
      responseFields: ["totalUsers", "revenue", "activeProjects"],
      authRequired: true,
      uiPageRef: "/dashboard",
      source: "explicit",
    },
    {
      method: "GET",
      path: "/api/activity",
      description: "Get recent activity for ActivityFeed component",
      requestBody: [],
      responseFields: ["recentActions", "timestamp"],
      authRequired: true,
      uiPageRef: "/dashboard",
      source: "inferred",
    },
    {
      method: "POST",
      path: "/api/auth/login",
      description: "Authenticate user with email and password",
      requestBody: ["email", "password"],
      responseFields: ["token", "userId"],
      authRequired: false,
      uiPageRef: "/login",
      source: "inferred",
    },
    {
      method: "GET",
      path: "/api/admin/users",
      description: "List all users for admin panel",
      requestBody: [],
      responseFields: ["id", "email", "role", "createdAt"],
      authRequired: true,
      uiPageRef: "/admin",
      source: "inferred",
    },
  ],
  drizzleTableHints: ["users", "activity_logs"],
  backgroundJobs: [],
  mismatches: [],
};

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("deriveBackendSpec", () => {
  beforeEach(() => {
    mockCreate.mockReset();
    mockCreate.mockResolvedValue({
      content: [{ type: "text", text: JSON.stringify(mockBackendSpec) }],
    });
  });

  it("produces BackendSpec with endpoints inferred from PageSpec[] data layer", async () => {
    const { deriveBackendSpec } = await import(
      "../../../lib/spec-parser/derive-backend-spec.js"
    );
    const result = await deriveBackendSpec([authenticatedPage, publicPage]);
    expect(result.endpoints.length).toBeGreaterThan(0);
    expect(result.endpoints[0].path).toMatch(/^\//);
    expect(result.endpoints[0].method).toMatch(/^(GET|POST|PUT|PATCH|DELETE)$/);
  });

  it("returns valid BackendSpecSchema.parse()-able output", async () => {
    const { deriveBackendSpec } = await import(
      "../../../lib/spec-parser/derive-backend-spec.js"
    );
    const result = await deriveBackendSpec([authenticatedPage, publicPage, adminPage]);
    expect(() => BackendSpecSchema.parse(result)).not.toThrow();
  });

  it("sets authRequired=true for pages with authLevel 'authenticated' or 'admin'", async () => {
    // Only return endpoints for authenticated/admin pages
    const authOnlySpec = {
      ...mockBackendSpec,
      endpoints: mockBackendSpec.endpoints.filter(
        (e) => e.uiPageRef === "/dashboard" || e.uiPageRef === "/admin"
      ),
    };
    mockCreate.mockResolvedValue({
      content: [{ type: "text", text: JSON.stringify(authOnlySpec) }],
    });
    const { deriveBackendSpec } = await import(
      "../../../lib/spec-parser/derive-backend-spec.js"
    );
    const result = await deriveBackendSpec([authenticatedPage, adminPage]);
    const protectedEndpoints = result.endpoints.filter(
      (e) => e.uiPageRef === "/dashboard" || e.uiPageRef === "/admin"
    );
    protectedEndpoints.forEach((endpoint) => {
      expect(endpoint.authRequired).toBe(true);
    });
  });

  it("sets authRequired=false for pages with authLevel 'public'", async () => {
    const publicOnlySpec = {
      ...mockBackendSpec,
      endpoints: [mockBackendSpec.endpoints[2]], // POST /api/auth/login
    };
    mockCreate.mockResolvedValue({
      content: [{ type: "text", text: JSON.stringify(publicOnlySpec) }],
    });
    const { deriveBackendSpec } = await import(
      "../../../lib/spec-parser/derive-backend-spec.js"
    );
    const result = await deriveBackendSpec([publicPage]);
    const publicEndpoints = result.endpoints.filter(
      (e) => e.uiPageRef === "/login"
    );
    publicEndpoints.forEach((endpoint) => {
      expect(endpoint.authRequired).toBe(false);
    });
  });

  it("marks auto-derived endpoints with source 'inferred' and explicit apiEndpoints matches with source 'explicit'", async () => {
    const { deriveBackendSpec } = await import(
      "../../../lib/spec-parser/derive-backend-spec.js"
    );
    const result = await deriveBackendSpec([authenticatedPage, publicPage, adminPage]);
    // The /api/stats endpoint was in authenticatedPage's explicit apiEndpoints
    const explicitEndpoint = result.endpoints.find(
      (e) => e.path === "/api/stats"
    );
    expect(explicitEndpoint?.source).toBe("explicit");
    // The /api/activity endpoint was auto-derived
    const inferredEndpoint = result.endpoints.find(
      (e) => e.path === "/api/activity"
    );
    expect(inferredEndpoint?.source).toBe("inferred");
  });

  it("infers CRUD endpoints for dataRequirements without explicit source field", async () => {
    // adminPage has dataRequirements but no apiEndpoints
    const adminOnlySpec = {
      ...mockBackendSpec,
      endpoints: [
        {
          method: "GET",
          path: "/api/admin/users",
          description: "List users for UserTable",
          requestBody: [],
          responseFields: ["id", "email", "role", "createdAt"],
          authRequired: true,
          uiPageRef: "/admin",
          source: "inferred",
        },
      ],
    };
    mockCreate.mockResolvedValue({
      content: [{ type: "text", text: JSON.stringify(adminOnlySpec) }],
    });
    const { deriveBackendSpec } = await import(
      "../../../lib/spec-parser/derive-backend-spec.js"
    );
    const result = await deriveBackendSpec([adminPage]);
    // Should still infer endpoints from dataRequirements even without explicit apiEndpoints
    expect(result.endpoints.length).toBeGreaterThan(0);
    expect(result.endpoints.some((e) => e.uiPageRef === "/admin")).toBe(true);
  });
});
