import { describe, it, expect } from "vitest";
import { generateSchemaCode, generateMigrationSQL } from "../../../lib/backend-wirer/schema-generator.js";

describe("generateSchemaCode", () => {
  it("produces drizzle pgTable code with correct table name and fields", () => {
    const block = generateSchemaCode("widgets", ["name", "description", "companyId"]);
    expect(block.tableName).toBe("widgets");
    expect(block.drizzleCode).toContain('pgTable("widgets"');
    expect(block.drizzleCode).toContain("name:");
    expect(block.drizzleCode).toContain("description:");
    // Standard columns always present
    expect(block.drizzleCode).toContain('text("id").primaryKey()');
    expect(block.drizzleCode).toContain("createdAt:");
    expect(block.drizzleCode).toContain("updatedAt:");
  });

  it("produces zodInsertCode with z.object and field validations", () => {
    const block = generateSchemaCode("widgets", ["name", "description", "companyId"]);
    expect(block.zodInsertCode).toContain("z.object({");
    expect(block.zodInsertCode).toContain("z.string()");
    expect(block.zodInsertCode).toContain("companyId");
  });

  it("produces typeExportCode with $inferSelect pattern", () => {
    const block = generateSchemaCode("widgets", ["name", "companyId"]);
    expect(block.typeExportCode).toContain("typeof widgets.$inferSelect");
    expect(block.typeExportCode).toContain("Widget");
    expect(block.typeExportCode).toContain("InsertWidget");
  });

  it("PascalCase is correctly derived from tableName", () => {
    const block = generateSchemaCode("userProfiles", ["userId"]);
    expect(block.typeExportCode).toContain("UserProfile");
    expect(block.zodInsertCode).toContain("insertUserProfile");
  });
});

describe("generateMigrationSQL", () => {
  it("produces CREATE TABLE IF NOT EXISTS for each schema block", () => {
    const blocks = [
      generateSchemaCode("widgets", ["name", "companyId"]),
    ];
    const sql = generateMigrationSQL(blocks);
    expect(sql).toContain('CREATE TABLE IF NOT EXISTS "widgets"');
    expect(sql).toContain('"id" text PRIMARY KEY');
    expect(sql).toContain('"company_id" text NOT NULL');
    expect(sql).toContain('"created_at" timestamp DEFAULT now()');
    expect(sql).toContain('"updated_at" timestamp DEFAULT now()');
  });

  it("produces multiple CREATE TABLE statements for multiple blocks", () => {
    const blocks = [
      generateSchemaCode("widgets", ["name"]),
      generateSchemaCode("gadgets", ["title"]),
    ];
    const sql = generateMigrationSQL(blocks);
    expect(sql).toContain('CREATE TABLE IF NOT EXISTS "widgets"');
    expect(sql).toContain('CREATE TABLE IF NOT EXISTS "gadgets"');
  });
});
