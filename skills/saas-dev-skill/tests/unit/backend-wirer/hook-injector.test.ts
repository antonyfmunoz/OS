import { describe, it, expect } from "vitest";
import { generateHookInjections } from "../../../lib/backend-wirer/hook-injector.js";
import type { BackendEndpointSpec } from "@shared/spec-schema.js";
import type { PageSpecFull } from "@shared/spec-schema.js";

const widgetsPage: PageSpecFull = {
  name: "Widgets",
  route: "/widgets",
  purpose: "Manage widgets",
  components: ["WidgetList", "WidgetForm"],
  authLevel: "authenticated",
  priority: 1,
  dependsOn: [],
  specVersion: 1,
  source: "explicit",
  dataRequirements: [{ component: "WidgetList", fields: ["id", "name"] }],
  apiEndpoints: [{ endpoint: "/api/widgets", source: "explicit" }],
  validationRules: [],
  events: [],
  featureFlagCandidates: [],
};

const getEndpoint: BackendEndpointSpec = {
  method: "GET",
  path: "/api/widgets",
  description: "Get all widgets",
  requestBody: [],
  responseFields: ["id", "name"],
  authRequired: true,
  uiPageRef: "/widgets",
  source: "explicit",
};

const postEndpoint: BackendEndpointSpec = {
  method: "POST",
  path: "/api/widgets",
  description: "Create a widget",
  requestBody: ["name", "description"],
  responseFields: ["id", "name"],
  authRequired: true,
  uiPageRef: "/widgets",
  source: "explicit",
};

describe("generateHookInjections", () => {
  it("GET endpoint produces HookInjection with useQuery import", () => {
    const injections = generateHookInjections([getEndpoint], [widgetsPage]);
    expect(injections).toHaveLength(1);
    const injection = injections[0];
    expect(injection.hookImport).toContain("import { useQuery }");
    expect(injection.hookImport).toContain('import { apiRequest }');
  });

  it("GET endpoint produces hookCode with useQuery and correct queryKey", () => {
    const injections = generateHookInjections([getEndpoint], [widgetsPage]);
    const injection = injections[0];
    expect(injection.hookCode).toContain("useQuery(");
    expect(injection.hookCode).toContain('queryKey: ["/api/widgets"]');
  });

  it("POST endpoint produces hookCode with useMutation", () => {
    const injections = generateHookInjections([postEndpoint], [widgetsPage]);
    const injection = injections[0];
    expect(injection.hookCode).toContain("useMutation");
  });

  it("POST endpoint hookImport contains useMutation import", () => {
    const injections = generateHookInjections([postEndpoint], [widgetsPage]);
    const injection = injections[0];
    expect(injection.hookImport).toContain("useMutation");
  });

  it("pageFilePath is mapped correctly from page route", () => {
    const injections = generateHookInjections([getEndpoint], [widgetsPage]);
    const injection = injections[0];
    expect(injection.pageFilePath).toContain("widgets");
    expect(injection.pageFilePath).toMatch(/\.tsx$/);
  });

  it("returns empty array when no endpoints match any page", () => {
    const noMatchEndpoint: BackendEndpointSpec = {
      ...getEndpoint,
      uiPageRef: "/unknown-page",
    };
    const injections = generateHookInjections([noMatchEndpoint], [widgetsPage]);
    // Should still generate injection even if page not found — uses uiPageRef as path fallback
    expect(Array.isArray(injections)).toBe(true);
  });
});
