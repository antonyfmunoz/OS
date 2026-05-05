import { describe, it, expect } from "vitest";
import { generateRouteCode, generateStorageCode } from "../../../lib/backend-wirer/route-generator.js";
import type { BackendEndpointSpec } from "@shared/spec-schema.js";
import type { BackendBrownfieldInventory } from "../../../lib/backend-wirer/types.js";

const emptyInventory: BackendBrownfieldInventory = {
  existingRoutePaths: [],
  existingStorageFunctions: [],
  existingTableNames: [],
  routesInsertionOffset: -1,
  storageInsertionOffset: -1,
  schemaInsertionOffset: -1,
};

const getEndpoint: BackendEndpointSpec = {
  method: "GET",
  path: "/api/widgets",
  description: "Get all widgets",
  requestBody: [],
  responseFields: ["id", "name"],
  authRequired: true,
  source: "explicit",
};

const postEndpoint: BackendEndpointSpec = {
  method: "POST",
  path: "/api/widgets",
  description: "Create a widget",
  requestBody: ["name", "description"],
  responseFields: ["id", "name"],
  authRequired: true,
  source: "explicit",
};

const deleteEndpoint: BackendEndpointSpec = {
  method: "DELETE",
  path: "/api/widgets/:id",
  description: "Delete a widget",
  requestBody: [],
  responseFields: [],
  authRequired: true,
  source: "explicit",
};

const publicGetEndpoint: BackendEndpointSpec = {
  method: "GET",
  path: "/api/public/widgets",
  description: "Get public widgets",
  requestBody: [],
  responseFields: ["id", "name"],
  authRequired: false,
  source: "explicit",
};

describe("generateRouteCode", () => {
  it("GET endpoint produces correct Express handler structure", () => {
    const block = generateRouteCode(getEndpoint, emptyInventory);
    expect(block.method).toBe("get");
    expect(block.path).toBe("/api/widgets");
    expect(block.code).toContain('app.get("/api/widgets"');
    expect(block.code).toContain("req.isAuthenticated()");
    expect(block.code).toContain("res.status(401)");
    expect(block.code).toContain("try {");
    expect(block.code).toContain("catch (error: any)");
    expect(block.code).toContain("res.json(data)");
  });

  it("POST endpoint with requestBody produces inline Zod safeParse", () => {
    const block = generateRouteCode(postEndpoint, emptyInventory);
    expect(block.code).toContain('app.post("/api/widgets"');
    expect(block.code).toContain(".safeParse(req.body)");
    expect(block.code).toContain("res.status(400)");
    expect(block.code).toContain("res.status(201)");
    expect(block.code).toContain("req.isAuthenticated()");
  });

  it("DELETE endpoint produces 204 end response", () => {
    const block = generateRouteCode(deleteEndpoint, emptyInventory);
    expect(block.code).toContain('app.delete("/api/widgets/:id"');
    expect(block.code).toContain("res.status(204).end()");
    expect(block.code).toContain("req.isAuthenticated()");
  });

  it("authRequired=false omits the isAuthenticated check", () => {
    const block = generateRouteCode(publicGetEndpoint, emptyInventory);
    expect(block.code).not.toContain("req.isAuthenticated()");
    expect(block.code).toContain('app.get("/api/public/widgets"');
  });
});

describe("generateStorageCode", () => {
  it("GET endpoint produces getWidgets function with db.select", () => {
    const block = generateStorageCode(getEndpoint);
    expect(block.functionName).toMatch(/getWidgets/);
    expect(block.code).toContain("async getWidgets(");
    expect(block.code).toContain("db.select().from(");
  });

  it("POST endpoint produces createWidget function with db.insert and returning", () => {
    const block = generateStorageCode(postEndpoint);
    expect(block.functionName).toMatch(/createWidget/);
    expect(block.code).toContain("async createWidget(");
    expect(block.code).toContain("db.insert(");
    expect(block.code).toContain(".returning()");
  });

  it("DELETE endpoint produces deleteWidget function with db.delete", () => {
    const block = generateStorageCode(deleteEndpoint);
    expect(block.functionName).toMatch(/deleteWidget/);
    expect(block.code).toContain("async deleteWidget(");
    expect(block.code).toContain("db.delete(");
  });
});
