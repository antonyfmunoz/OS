import { describe, it, expect } from "vitest";
import {
  PageSpecCore,
  PageSpecUI,
  PageSpecData,
  PageSpecAnalytics,
  PageSpecFull,
  SharedComponentSpec,
  BackendEndpointSpec,
  BackendSpecSchema,
  SpecOutputSchema,
  SpecItemSource,
} from "@shared/spec-schema";

// ─── SpecItemSource ───────────────────────────────────────────────────────────

describe("SpecItemSource", () => {
  it("accepts 'explicit'", () => {
    const result = SpecItemSource.safeParse("explicit");
    expect(result.success).toBe(true);
  });

  it("accepts 'inferred'", () => {
    const result = SpecItemSource.safeParse("inferred");
    expect(result.success).toBe(true);
  });

  it("rejects other strings", () => {
    const result = SpecItemSource.safeParse("user-provided");
    expect(result.success).toBe(false);
  });
});

// ─── PageSpecCore ─────────────────────────────────────────────────────────────

describe("PageSpecCore", () => {
  const validCore = {
    name: "Dashboard",
    route: "/dashboard",
    purpose: "Main analytics overview for authenticated users",
    components: ["StatsCard", "ActivityFeed"],
    authLevel: "authenticated" as const,
    priority: 2,
  };

  it("accepts valid object with all required fields", () => {
    const result = PageSpecCore.safeParse(validCore);
    expect(result.success).toBe(true);
  });

  it("rejects object missing required field 'route'", () => {
    const { route, ...withoutRoute } = validCore;
    const result = PageSpecCore.safeParse(withoutRoute);
    expect(result.success).toBe(false);
  });

  it("rejects route that does not start with '/'", () => {
    const result = PageSpecCore.safeParse({ ...validCore, route: "dashboard" });
    expect(result.success).toBe(false);
  });

  it("accepts route starting with '/'", () => {
    const result = PageSpecCore.safeParse({ ...validCore, route: "/dashboard" });
    expect(result.success).toBe(true);
  });

  it("defaults source to 'inferred' when omitted", () => {
    const result = PageSpecCore.safeParse(validCore);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.source).toBe("inferred");
    }
  });

  it("accepts explicit source: 'explicit'", () => {
    const result = PageSpecCore.safeParse({ ...validCore, source: "explicit" });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.source).toBe("explicit");
    }
  });

  it("defaults dependsOn to empty array when omitted", () => {
    const result = PageSpecCore.safeParse(validCore);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.dependsOn).toEqual([]);
    }
  });

  it("defaults specVersion to 1 when omitted", () => {
    const result = PageSpecCore.safeParse(validCore);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.specVersion).toBe(1);
    }
  });
});

// ─── PageSpecUI ───────────────────────────────────────────────────────────────

describe("PageSpecUI", () => {
  it("accepts valid object with all optional fields", () => {
    const result = PageSpecUI.safeParse({
      layoutHint: "sidebar-main",
      emptyState: "No data yet. Start by adding your first item.",
      loadingState: "Loading analytics data...",
      errorState: "Failed to load data. Please refresh.",
      mobileConsiderations: "Stack cards vertically on mobile",
    });
    expect(result.success).toBe(true);
  });

  it("accepts empty object (all fields optional)", () => {
    const result = PageSpecUI.safeParse({});
    expect(result.success).toBe(true);
  });
});

// ─── PageSpecData ─────────────────────────────────────────────────────────────

describe("PageSpecData", () => {
  it("accepts valid object with dataRequirements, apiEndpoints, validationRules", () => {
    const result = PageSpecData.safeParse({
      dataRequirements: [
        { component: "StatsCard", fields: ["totalUsers", "revenue"] },
      ],
      apiEndpoints: [
        { endpoint: "/api/stats", source: "inferred" },
      ],
      validationRules: ["date range must not exceed 90 days"],
    });
    expect(result.success).toBe(true);
  });

  it("accepts object with just dataRequirements (other fields default)", () => {
    const result = PageSpecData.safeParse({
      dataRequirements: [
        { component: "ActivityFeed", fields: ["events"] },
      ],
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.apiEndpoints).toEqual([]);
      expect(result.data.validationRules).toEqual([]);
    }
  });
});

// ─── PageSpecAnalytics ────────────────────────────────────────────────────────

describe("PageSpecAnalytics", () => {
  it("accepts valid object with events and featureFlagCandidates", () => {
    const result = PageSpecAnalytics.safeParse({
      events: [
        {
          name: "dashboard_viewed",
          trigger: "page load",
          properties: ["userId", "plan"],
          source: "inferred",
        },
      ],
      featureFlagCandidates: ["new-dashboard-layout"],
    });
    expect(result.success).toBe(true);
  });

  it("accepts empty object (all fields default to empty arrays)", () => {
    const result = PageSpecAnalytics.safeParse({});
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.events).toEqual([]);
      expect(result.data.featureFlagCandidates).toEqual([]);
    }
  });
});

// ─── PageSpecFull (merge) ─────────────────────────────────────────────────────

describe("PageSpecFull", () => {
  const validFull = {
    name: "Dashboard",
    route: "/dashboard",
    purpose: "Analytics overview",
    components: ["StatsCard"],
    authLevel: "authenticated" as const,
    priority: 1,
    layoutHint: "sidebar-main",
    emptyState: "No data yet.",
    loadingState: "Loading...",
    errorState: "Error loading data.",
    mobileConsiderations: "Stack vertically",
    dataRequirements: [{ component: "StatsCard", fields: ["count"] }],
    apiEndpoints: [{ endpoint: "/api/stats" }],
    validationRules: [],
    events: [{ name: "page_viewed", trigger: "load", properties: [] }],
    featureFlagCandidates: [],
  };

  it("accepts a complete page spec with all four layers", () => {
    const result = PageSpecFull.safeParse(validFull);
    expect(result.success).toBe(true);
  });

  it("PageSpecCore.merge(PageSpecUI) produces a schema that accepts a combined object", () => {
    const CorePlusUI = PageSpecCore.merge(PageSpecUI);
    const result = CorePlusUI.safeParse({
      name: "Login",
      route: "/login",
      purpose: "Authentication page",
      components: ["LoginForm"],
      authLevel: "public" as const,
      priority: 1,
      layoutHint: "centered",
      emptyState: undefined,
    });
    expect(result.success).toBe(true);
  });

  it("PageSpecCore.merge(PageSpecData) produces a schema that accepts a combined object", () => {
    const CorePlusData = PageSpecCore.merge(PageSpecData);
    const result = CorePlusData.safeParse({
      name: "Settings",
      route: "/settings",
      purpose: "User account settings",
      components: ["ProfileForm"],
      authLevel: "authenticated" as const,
      priority: 3,
      dataRequirements: [{ component: "ProfileForm", fields: ["name", "email"] }],
      apiEndpoints: [],
      validationRules: ["email must be valid"],
    });
    expect(result.success).toBe(true);
  });
});

// ─── SharedComponentSpec ──────────────────────────────────────────────────────

describe("SharedComponentSpec", () => {
  it("accepts valid shared component with all fields", () => {
    const result = SharedComponentSpec.safeParse({
      id: "shared-nav-sidebar",
      name: "NavSidebar",
      purpose: "Primary navigation sidebar used across all authenticated pages",
      usedByPages: ["/dashboard", "/settings", "/profile"],
      props: ["currentRoute", "userName"],
      source: "inferred",
    });
    expect(result.success).toBe(true);
  });

  it("defaults source to 'inferred' when omitted", () => {
    const result = SharedComponentSpec.safeParse({
      id: "shared-header",
      name: "Header",
      purpose: "Top navigation bar",
      usedByPages: ["/dashboard"],
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.source).toBe("inferred");
    }
  });

  it("defaults props to empty array when omitted", () => {
    const result = SharedComponentSpec.safeParse({
      id: "shared-footer",
      name: "Footer",
      purpose: "Page footer",
      usedByPages: ["/dashboard"],
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.props).toEqual([]);
    }
  });
});

// ─── BackendEndpointSpec ──────────────────────────────────────────────────────

describe("BackendEndpointSpec", () => {
  it("accepts valid endpoint spec with all fields", () => {
    const result = BackendEndpointSpec.safeParse({
      method: "GET",
      path: "/api/users",
      description: "Fetch all users for the current company",
      requestBody: [],
      responseFields: ["id", "email", "name"],
      authRequired: true,
      uiPageRef: "/users",
      source: "explicit",
    });
    expect(result.success).toBe(true);
  });

  it("rejects endpoint path that does not start with '/'", () => {
    const result = BackendEndpointSpec.safeParse({
      method: "GET",
      path: "api/users",
      description: "Fetch users",
      authRequired: true,
      source: "inferred",
    });
    expect(result.success).toBe(false);
  });

  it("defaults source to 'inferred' when omitted", () => {
    const result = BackendEndpointSpec.safeParse({
      method: "POST",
      path: "/api/auth/login",
      description: "Authenticate user",
      authRequired: false,
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.source).toBe("inferred");
    }
  });
});

// ─── BackendSpecSchema ────────────────────────────────────────────────────────

describe("BackendSpecSchema", () => {
  it("accepts valid backend spec with endpoints, hints, jobs, mismatches", () => {
    const result = BackendSpecSchema.safeParse({
      endpoints: [
        {
          method: "GET",
          path: "/api/stats",
          description: "Dashboard statistics",
          authRequired: true,
        },
      ],
      drizzleTableHints: ["users", "sessions"],
      backgroundJobs: ["send-welcome-email"],
      mismatches: [],
    });
    expect(result.success).toBe(true);
  });

  it("accepts empty endpoints array (all defaults)", () => {
    const result = BackendSpecSchema.safeParse({
      endpoints: [],
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.drizzleTableHints).toEqual([]);
      expect(result.data.backgroundJobs).toEqual([]);
      expect(result.data.mismatches).toEqual([]);
    }
  });
});

// ─── SpecOutputSchema ─────────────────────────────────────────────────────────

describe("SpecOutputSchema", () => {
  const minimalPage = {
    name: "Home",
    route: "/",
    purpose: "Landing page",
    components: ["HeroSection"],
    authLevel: "public" as const,
    priority: 1,
    dataRequirements: [],
  };

  it("accepts full spec output with pages, sharedComponents, suggestedOrder, backendSpec", () => {
    const result = SpecOutputSchema.safeParse({
      pages: [minimalPage],
      sharedComponents: [
        {
          id: "shared-nav",
          name: "NavBar",
          purpose: "Top navigation",
          usedByPages: ["/"],
        },
      ],
      suggestedOrder: ["/"],
      backendSpec: {
        endpoints: [
          {
            method: "GET",
            path: "/api/health",
            description: "Health check",
            authRequired: false,
          },
        ],
      },
    });
    expect(result.success).toBe(true);
  });

  it("accepts spec without optional backendSpec", () => {
    const result = SpecOutputSchema.safeParse({
      pages: [minimalPage],
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.backendSpec).toBeUndefined();
    }
  });

  it("rejects when pages array is empty (minLength 1)", () => {
    const result = SpecOutputSchema.safeParse({
      pages: [],
    });
    expect(result.success).toBe(false);
  });

  it("defaults sharedComponents and suggestedOrder to empty arrays", () => {
    const result = SpecOutputSchema.safeParse({
      pages: [minimalPage],
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.sharedComponents).toEqual([]);
      expect(result.data.suggestedOrder).toEqual([]);
    }
  });
});
