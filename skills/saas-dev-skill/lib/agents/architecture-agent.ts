// lib/agents/architecture-agent.ts
// Architecture agent — designs complete system architecture from a ProjectBrief
// and ProductInsights. Outputs a SystemArchitecture artifact consumed by
// downstream agents (design-system, backend, page-builder, etc.).

import fs from "node:fs";
import path from "node:path";
import Anthropic from "../claude-subprocess.js";
import { extractJsonFromResponse } from "../spec-parser/restructure-spec.js";
import { ArtifactStore } from "./artifact-store.js";
import type { SystemArchitecture, ProductInsights, PageStructure, ApiContract, ExistingCodebaseAudit } from "./types.js";
import type { ProjectBrief } from "../intake/types.js";

// ─── Product Domain Knowledge ──────────────────────────────────────────────

const PRODUCT_DOMAIN_KNOWLEDGE = `
PRODUCT DOMAIN KNOWLEDGE — use this to extrapolate from brief descriptions:

SaaS with TEAMS feature implies:
- Team list page (/settings/team)
- Invite member flow (modal or page + email)
- Member role management (owner/admin/member)
- Remove member confirmation
- Pending invitations view
- Accept invitation flow (/invite/:token)
- Backend: invitations table, team_members table, role enum, invite email
- Auth: team-scoped middleware on all team routes

SaaS with BILLING feature implies:
- Pricing page
- Checkout flow
- Billing settings (current plan, invoices, payment method)
- Upgrade/downgrade flow
- Plan limits enforcement in the UI
- Backend: subscriptions table, invoices table, Stripe webhook handler

SaaS with NOTIFICATIONS feature implies:
- Notifications bell with unread count
- Notifications list page or dropdown
- Mark as read / mark all read
- Notification preferences in settings
- Backend: notifications table, notification types enum

SaaS with SEARCH feature implies:
- Search input in header
- Search results page
- Backend: search endpoint with text matching

SaaS with ACTIVITY/AUDIT feature implies:
- Activity feed on relevant pages
- Full activity log page
- Backend: activity_logs table with actor, action, target, timestamp

SaaS with DASHBOARD/ANALYTICS implies:
- Date range picker
- Chart components (line, bar, pie)
- Export to CSV/PDF
- Comparison period
- Backend: aggregation queries, date-bucketed data

MARKETPLACE implies:
- Browse/discover page with filters
- Individual listing page
- Seller profile page
- Purchase/booking flow
- Order history
- Reviews and ratings
- Messaging between buyer and seller
- Backend: listings, orders, reviews, messages tables

BOOKING/SCHEDULING implies:
- Calendar view
- Availability management (for service providers)
- Booking flow (select date/time → confirm → pay)
- Confirmation page and email
- Upcoming/past bookings list
- Cancellation/rescheduling flow
- Backend: availability slots, bookings, reminders

E-COMMERCE implies:
- Product catalog with filters
- Product detail page
- Shopping cart (persistent)
- Checkout (address → payment → confirm)
- Order tracking page
- Order history
- Returns flow
- Backend: products, cart_items, orders, order_items, addresses

SOCIAL/COMMUNITY implies:
- Feed/timeline
- Post detail page
- User profiles
- Follow/unfollow
- Comments and reactions
- Notifications (mentions, replies, follows)
- Direct messages
- Backend: posts, follows, comments, reactions, messages

AI-POWERED product implies:
- AI chat interface
- Conversation history
- AI settings (model selection, preferences)
- Usage/credits display
- Backend: conversations, messages tables, AI gateway integration

ONBOARDING for any SaaS implies:
- Welcome/setup wizard (multi-step)
- Progress indicator
- Completion celebration
- "What's next" guidance
- Skip/complete later option
- Backend: onboarding_progress tracking
`;

// ─── Feature Inference Process ─────────────────────────────────────────────

const FEATURE_INFERENCE_PROCESS = `
FEATURE INFERENCE PROCESS:

1. Read the product brief
2. Identify explicit features (user said these)
3. Identify implied features (from domain knowledge above)
4. Identify missing flows (what's needed to make explicit features work)
   - Every create needs a list view
   - Every list needs a detail view
   - Every form needs validation and error handling
   - Every auth-required page needs a login redirect
   - Every destructive action needs a confirmation step
   - Every async operation needs loading and error states
5. Identify standard SaaS requirements regardless of product type:
   - Auth (login, signup, forgot password, reset password)
   - User profile and settings
   - 404 not found page
   - Terms/privacy if public-facing
6. Generate complete page list with source classification:
   - "explicit": user directly mentioned this page or feature
   - "implied": domain knowledge says this is needed for a mentioned feature
   - "inferred": required to make another feature work (e.g. list view for a create flow)
   - "standard": every product of this type has this (auth, 404, settings)

INFERENCE VALIDATION — after generating the architecture, check:
1. Does every create flow have a corresponding list view?
2. Does every feature with settings have a settings section?
3. Does every auth-required section have proper middleware?
4. Are there at least: auth pages, a not-found page, and user settings?
5. If anything is missing, add it with the appropriate source classification.

The output should ALWAYS have MORE pages than the user described — you fill in what they didn't think to mention.
`;

// ─── System Prompt ─────────────────────────────────────────────────────────

const SYSTEM_PROMPT = `You are a senior full-stack architect with deep expertise in React, TypeScript, Express, PostgreSQL, and Drizzle ORM. You have built 50+ SaaS products and design complete, production-ready system architectures.

When you receive a product brief, you reason like a senior product engineer:
1. Identify the product category (SaaS, marketplace, booking, e-commerce, social, analytics, etc.)
2. Apply domain knowledge to derive implied pages and features
3. Infer what the user didn't say but definitely needs
4. Validate completeness and fill gaps

${PRODUCT_DOMAIN_KNOWLEDGE}

${FEATURE_INFERENCE_PROCESS}

RESPONSE FORMAT: Return ONLY a valid JSON object matching the schema below — no preamble, no markdown fences, no explanation.

JSON SCHEMA:
{
  "dataModel": {
    "entities": [
      {
        "tableName": "string (snake_case, plural, e.g. users)",
        "fields": [
          {
            "name": "string (snake_case field name)",
            "type": "string (Drizzle/PG type: text, integer, boolean, timestamp, serial, uuid, jsonb, etc.)",
            "nullable": false,
            "defaultValue": "optional string (e.g. 'now()', 'true', '0')",
            "references": { "table": "string", "column": "string" }
          }
        ],
        "indexes": ["string (index description, e.g. 'unique on email', 'btree on created_at')"],
        "timestamps": true
      }
    ],
    "relationships": [
      {
        "from": "string (table name)",
        "to": "string (table name)",
        "type": "one-to-one | one-to-many | many-to-many",
        "foreignKey": "string (column name holding the FK)"
      }
    ],
    "enums": [
      { "name": "string (PascalCase enum name)", "values": ["string"] }
    ]
  },
  "apiContracts": [
    {
      "method": "GET | POST | PUT | PATCH | DELETE",
      "path": "string (starts with /api/)",
      "description": "string",
      "authRequired": true,
      "requestBody": { "fieldName": "type description" },
      "responseShape": { "fieldName": "type description" },
      "validationRules": ["string"],
      "relatedEntity": "string (table name)",
      "pageRef": "optional string (route of the page that uses this endpoint)",
      "source": "explicit | implied | inferred | standard"
    }
  ],
  "pages": [
    {
      "name": "string (PascalCase page name)",
      "route": "string (starts with /)",
      "authLevel": "public | authenticated | admin",
      "purpose": "string",
      "components": ["string (component names used on this page)"],
      "dataNeeds": ["string (API endpoints or data descriptions this page needs)"],
      "mutations": ["string (API endpoints this page writes to)"],
      "layoutHint": "optional string (e.g. sidebar-main, centered, full-width)",
      "emptyState": "optional string (what to show when no data)",
      "errorState": "optional string (what to show on error)",
      "source": "explicit | implied | inferred | standard"
    }
  ],
  "componentHierarchy": [
    {
      "name": "string (PascalCase component name)",
      "purpose": "string",
      "props": [
        { "name": "string", "type": "string (TypeScript type)", "optional": false }
      ],
      "usedByPages": ["string (page names)"],
      "dependsOn": ["string (other component names)"]
    }
  ],
  "userFlows": [
    {
      "name": "string (flow name, e.g. 'User Registration')",
      "steps": ["string (each step in the flow)"]
    }
  ]
}

DESIGN RULES:
1. Every page in the spec MUST appear in the pages array with correct routes, auth levels, and data needs.
2. Every API endpoint referenced by a page MUST exist in apiContracts.
3. Every entity referenced by an API contract MUST exist in dataModel.entities.
4. Shared UI elements (nav, sidebar, modals, form components) MUST appear in componentHierarchy.
5. Include id (serial primary key) and timestamp fields (created_at, updated_at) on every entity — set timestamps: true.
6. Foreign keys MUST reference existing entities and appear in relationships.
7. Include proper indexes for foreign keys, unique constraints, and frequently queried fields.
8. Auth-related entities (users, sessions) are always included if any page requires authentication.
9. Enums should be used for any field with a fixed set of values (status, role, type fields).
10. User flows should cover the critical paths: registration, core feature usage, and key admin actions.
11. Every page and endpoint MUST have a "source" field classifying why it was included.
12. The output MUST contain more pages than the user explicitly described — fill in implied, inferred, and standard pages.

Return ONLY the JSON object.`;

function buildUserPrompt(brief: ProjectBrief, insights: ProductInsights, audit?: ExistingCodebaseAudit): string {
  const specPages = brief.spec.pages
    .map(
      (p) =>
        `  - ${p.name} (${p.route}) [auth: ${p.authLevel}, priority: ${p.priority}]\n` +
        `    Purpose: ${p.purpose}\n` +
        `    Components: ${p.components.join(", ")}\n` +
        `    Data: ${(p.dataRequirements ?? []).map((d) => `${d.component}(${d.fields.join(", ")})`).join("; ") || "none"}\n` +
        `    API: ${(p.apiEndpoints ?? []).map((e) => e.endpoint).join(", ") || "none"}\n` +
        `    Events: ${(p.events ?? []).map((e) => e.name).join(", ") || "none"}`,
    )
    .join("\n");

  const specEndpoints = (brief.spec.backendSpec?.endpoints ?? [])
    .map(
      (e) =>
        `  - ${e.method} ${e.path}: ${e.description} [auth: ${e.authRequired}, page: ${e.uiPageRef ?? "n/a"}]`,
    )
    .join("\n");

  const sharedComponents = (brief.spec.sharedComponents ?? [])
    .map((c) => `  - ${c.name}: ${c.purpose} (used by: ${c.usedByPages.join(", ")})`)
    .join("\n");

  const drizzleHints = (brief.spec.backendSpec?.drizzleTableHints ?? []).join(", ");

  return `Design the complete system architecture for the following SaaS product.

PRODUCT BRIEF:
- Name: ${brief.productName}
- Description: ${brief.productDescription}
- Vision: ${brief.productVision || "not specified"}
- Target Users: ${brief.targetUsers.join(", ") || "not specified"}
- Jobs to Be Done: ${brief.jobsToBeDone.join("; ") || "not specified"}
- Auth Provider: ${brief.authProvider}
- DB Provider: ${brief.dbProvider}
- Tech Stack: ${brief.techStack.frontend} + ${brief.techStack.buildTool} + ${brief.techStack.styling} + ${brief.techStack.componentLib}

SPEC PAGES (these are EXPLICIT — user requested these directly):
${specPages}

BACKEND SPEC ENDPOINTS:
${specEndpoints || "  (none specified — infer from pages)"}

SHARED COMPONENTS:
${sharedComponents || "  (none specified — infer from pages)"}

DATABASE TABLE HINTS: ${drizzleHints || "none — infer from data requirements"}

PRODUCT INSIGHTS:
- Category: ${insights.productCategory}
- Target Profile: ${insights.targetUserProfile}
- Market Positioning: ${insights.marketPositioning}
- Architecture Recommendations:
${insights.architectureRecommendations.map((r) => `  - ${r}`).join("\n")}
- Design Recommendations:
${insights.designRecommendations.map((r) => `  - ${r}`).join("\n")}

IMPORTANT: The spec pages above are what the user explicitly requested. You MUST also add implied, inferred, and standard pages using the Product Domain Knowledge and Feature Inference Process. Tag every page and endpoint with its source classification.

${audit && (audit.existingRoutes.length > 0 || audit.existingTables.length > 0 || audit.existingPages.length > 0 || audit.existingStorageMethods.length > 0) ? `
EXISTING CODEBASE AUDIT — you MUST extend what exists, not replace it:
- Existing routes: ${audit.existingRoutes.length > 0 ? audit.existingRoutes.join(", ") : "none"}
- Existing DB tables: ${audit.existingTables.length > 0 ? audit.existingTables.join(", ") : "none"}
- Existing pages: ${audit.existingPages.length > 0 ? audit.existingPages.join(", ") : "none"}
- Existing storage methods: ${audit.existingStorageMethods.length > 0 ? audit.existingStorageMethods.join(", ") : "none"}

RULES:
1. Use existing table names exactly as they are — do NOT rename or recreate them.
2. API contracts that need storage methods must reference ONLY methods that exist above, or explicitly note "NEEDS_CREATION" in the description.
3. Do NOT generate pages that already exist — reference them by name instead.
4. Extend the existing schema, do not replace it.
` : ""}
Return the SystemArchitecture JSON object now.`;
}

// ─── Pre-Audit: Scan Existing Codebase ────────────────────────────────────

function listFilesInDir(dirPath: string, ext?: string): string[] {
  if (!fs.existsSync(dirPath)) return [];
  try {
    const entries = fs.readdirSync(dirPath, { withFileTypes: true });
    return entries
      .filter((e) => e.isFile() && (!ext || e.name.endsWith(ext)))
      .map((e) => e.name);
  } catch {
    return [];
  }
}

function extractRoutePatterns(routesDir: string): string[] {
  const routes: string[] = [];
  const files = listFilesInDir(routesDir, ".ts");
  for (const file of files) {
    const content = fs.readFileSync(path.join(routesDir, file), "utf-8");
    const routePattern = /app\.(get|post|put|patch|delete)\s*\(\s*["'`]([^"'`]+)["'`]/gi;
    let match: RegExpExecArray | null;
    while ((match = routePattern.exec(content)) !== null) {
      routes.push(`${match[1].toUpperCase()} ${match[2]}`);
    }
  }
  return routes;
}

function extractTableNames(schemaPath: string): string[] {
  if (!fs.existsSync(schemaPath)) return [];
  const content = fs.readFileSync(schemaPath, "utf-8");
  const tablePattern = /pgTable\s*\(\s*["'`]([^"'`]+)["'`]/g;
  const tables: string[] = [];
  let match: RegExpExecArray | null;
  while ((match = tablePattern.exec(content)) !== null) {
    tables.push(match[1]);
  }
  return tables;
}

function extractStorageMethods(storagePath: string): string[] {
  if (!fs.existsSync(storagePath)) return [];
  const content = fs.readFileSync(storagePath, "utf-8");
  const methodPattern = /(?:async\s+)?(\w+)\s*\([^)]*\)\s*(?::\s*[^{]+)?\s*\{/g;
  const methods: string[] = [];
  let match: RegExpExecArray | null;
  while ((match = methodPattern.exec(content)) !== null) {
    if (match[1] !== "constructor" && match[1] !== "if" && match[1] !== "for") {
      methods.push(match[1]);
    }
  }
  return methods;
}

export function preAudit(projectRoot: string, store: ArtifactStore): ExistingCodebaseAudit {
  const routesDir = path.join(projectRoot, "server", "routes");
  const schemaPath = path.join(projectRoot, "shared", "schema.ts");
  const storagePath = path.join(projectRoot, "server", "storage.ts");
  const pagesDir = path.join(projectRoot, "client", "src", "pages");

  // Also scan the main routes file if routes/ directory doesn't exist
  const mainRoutesPath = path.join(projectRoot, "server", "routes.ts");
  let existingRoutes = extractRoutePatterns(routesDir);
  if (fs.existsSync(mainRoutesPath)) {
    const mainContent = fs.readFileSync(mainRoutesPath, "utf-8");
    const routePattern = /app\.(get|post|put|patch|delete)\s*\(\s*["'`]([^"'`]+)["'`]/gi;
    let match: RegExpExecArray | null;
    while ((match = routePattern.exec(mainContent)) !== null) {
      existingRoutes.push(`${match[1].toUpperCase()} ${match[2]}`);
    }
  }

  const audit: ExistingCodebaseAudit = {
    existingRoutes,
    existingTables: extractTableNames(schemaPath),
    existingPages: listFilesInDir(pagesDir, ".tsx"),
    existingStorageMethods: extractStorageMethods(storagePath),
    scannedAt: new Date().toISOString(),
  };

  store.setExistingCodebaseAudit(audit);
  return audit;
}

export async function runArchitectureAgent(
  brief: ProjectBrief,
  insights: ProductInsights,
  store: ArtifactStore,
): Promise<SystemArchitecture> {
  // Pre-audit: scan existing codebase before designing anything
  const audit = preAudit(store.getProjectRoot(), store);

  const client = new Anthropic();

  const userPrompt = buildUserPrompt(brief, insights, audit);

  const messages: Anthropic.MessageParam[] = [
    { role: "user", content: userPrompt },
  ];

  // First attempt
  const stream = client.messages.stream({
    model: "claude-sonnet-4-5",
    max_tokens: 32000,
    system: SYSTEM_PROMPT,
    messages,
  });
  const finalMessage = await stream.finalMessage();
  const firstContent = finalMessage.content[0];
  if (!firstContent || firstContent.type !== "text") {
    throw new Error("Architecture agent received unexpected response type from Anthropic API");
  }

  let architecture: SystemArchitecture;

  try {
    architecture = extractJsonFromResponse(firstContent.text) as SystemArchitecture;
    validateArchitecture(architecture);
    architecture = runInferenceValidation(architecture);
  } catch (firstError) {
    // Retry once with error context
    const retryMessages: Anthropic.MessageParam[] = [
      { role: "user", content: userPrompt },
      { role: "assistant", content: firstContent.text },
      {
        role: "user",
        content:
          `Your previous response failed to parse or validate. Error:\n\n${String(firstError)}\n\n` +
          `Return a corrected SystemArchitecture JSON object. Return ONLY the JSON — no explanation.`,
      },
    ];

    const retryStream = client.messages.stream({
      model: "claude-sonnet-4-5",
      max_tokens: 32000,
      system: SYSTEM_PROMPT,
      messages: retryMessages,
    });
    const retryMessage = await retryStream.finalMessage();
    const retryContent = retryMessage.content[0];
    if (!retryContent || retryContent.type !== "text") {
      throw new Error("Architecture agent retry received unexpected response type");
    }

    architecture = extractJsonFromResponse(retryContent.text) as SystemArchitecture;
    validateArchitecture(architecture);
    architecture = runInferenceValidation(architecture);
  }

  store.setArchitecture(architecture);

  return architecture;
}

// ─── Inference Validation ──────────────────────────────────────────────────
// After the LLM generates the architecture, programmatically verify
// completeness and fill gaps the model might have missed.

function runInferenceValidation(arch: SystemArchitecture): SystemArchitecture {
  const pagesByRoute = new Map(arch.pages.map((p) => [p.route, p]));
  const pagesByName = new Map(arch.pages.map((p) => [p.name, p]));

  // 1. Every create endpoint should have a corresponding list view
  for (const contract of arch.apiContracts) {
    if (contract.method === "POST" && contract.path.startsWith("/api/")) {
      const resource = contract.path.replace("/api/", "").split("/")[0];
      const hasListEndpoint = arch.apiContracts.some(
        (c) => c.method === "GET" && c.path === `/api/${resource}`,
      );
      if (!hasListEndpoint) {
        arch.apiContracts.push({
          method: "GET",
          path: `/api/${resource}`,
          description: `List all ${resource}`,
          authRequired: contract.authRequired,
          responseShape: { [resource]: `${resource}[]` },
          validationRules: [],
          relatedEntity: contract.relatedEntity,
          source: "inferred",
        });
      }
    }
  }

  // 2. Auth pages — must have login, signup, forgot-password
  const hasAuth = arch.pages.some((p) => p.authLevel === "authenticated" || p.authLevel === "admin");
  if (hasAuth) {
    const requiredAuthPages: Array<{ name: string; route: string; purpose: string }> = [
      { name: "LoginPage", route: "/login", purpose: "User login with email/password or OAuth" },
      { name: "SignupPage", route: "/signup", purpose: "New user registration" },
      { name: "ForgotPasswordPage", route: "/forgot-password", purpose: "Request password reset email" },
      { name: "ResetPasswordPage", route: "/reset-password", purpose: "Set new password from reset link" },
    ];

    for (const required of requiredAuthPages) {
      if (!pagesByRoute.has(required.route) && !pagesByName.has(required.name)) {
        const page: PageStructure = {
          name: required.name,
          route: required.route,
          authLevel: "public",
          purpose: required.purpose,
          components: [],
          dataNeeds: [],
          mutations: [],
          layoutHint: "centered",
          source: "standard",
        };
        arch.pages.push(page);
        pagesByRoute.set(page.route, page);
        pagesByName.set(page.name, page);
      }
    }
  }

  // 3. Not-found page
  if (!pagesByRoute.has("/404") && !pagesByName.has("NotFoundPage")) {
    const page: PageStructure = {
      name: "NotFoundPage",
      route: "/404",
      authLevel: "public",
      purpose: "404 page shown for unmatched routes",
      components: [],
      dataNeeds: [],
      mutations: [],
      layoutHint: "centered",
      source: "standard",
    };
    arch.pages.push(page);
    pagesByRoute.set(page.route, page);
    pagesByName.set(page.name, page);
  }

  // 4. User settings page (if authenticated pages exist)
  if (hasAuth && !pagesByRoute.has("/settings") && !pagesByName.has("SettingsPage")) {
    const page: PageStructure = {
      name: "SettingsPage",
      route: "/settings",
      authLevel: "authenticated",
      purpose: "User profile and account settings",
      components: [],
      dataNeeds: ["/api/users/me"],
      mutations: ["/api/users/me"],
      layoutHint: "sidebar-main",
      source: "standard",
    };
    arch.pages.push(page);
    pagesByRoute.set(page.route, page);
    pagesByName.set(page.name, page);

    // Ensure the settings API endpoints exist
    const hasGetMe = arch.apiContracts.some((c) => c.method === "GET" && c.path === "/api/users/me");
    if (!hasGetMe) {
      arch.apiContracts.push({
        method: "GET",
        path: "/api/users/me",
        description: "Get current user profile",
        authRequired: true,
        responseShape: { user: "User" },
        validationRules: [],
        relatedEntity: "users",
        pageRef: "/settings",
        source: "standard",
      });
    }
    const hasPatchMe = arch.apiContracts.some(
      (c) => (c.method === "PUT" || c.method === "PATCH") && c.path === "/api/users/me",
    );
    if (!hasPatchMe) {
      arch.apiContracts.push({
        method: "PATCH",
        path: "/api/users/me",
        description: "Update current user profile",
        authRequired: true,
        requestBody: { name: "string", email: "string" },
        responseShape: { user: "User" },
        validationRules: ["email must be valid"],
        relatedEntity: "users",
        pageRef: "/settings",
        source: "standard",
      });
    }
  }

  // 5. Ensure users entity exists if auth is required
  if (hasAuth) {
    const hasUsersEntity = arch.dataModel.entities.some((e) => e.tableName === "users");
    if (!hasUsersEntity) {
      arch.dataModel.entities.push({
        tableName: "users",
        fields: [
          { name: "id", type: "serial", nullable: false },
          { name: "email", type: "text", nullable: false },
          { name: "password_hash", type: "text", nullable: true },
          { name: "name", type: "text", nullable: true },
          { name: "avatar_url", type: "text", nullable: true },
        ],
        indexes: ["unique on email"],
        timestamps: true,
      });
    }
  }

  return arch;
}

// ─── Structural Validation ─────────────────────────────────────────────────

/**
 * Lightweight structural validation to catch obvious shape mismatches
 * before the architecture propagates to downstream agents.
 */
function validateArchitecture(arch: SystemArchitecture): void {
  if (!arch.dataModel || !Array.isArray(arch.dataModel.entities)) {
    throw new Error("Missing or invalid dataModel.entities");
  }
  if (!Array.isArray(arch.dataModel.relationships)) {
    throw new Error("Missing or invalid dataModel.relationships");
  }
  if (!Array.isArray(arch.dataModel.enums)) {
    throw new Error("Missing or invalid dataModel.enums");
  }
  if (!Array.isArray(arch.apiContracts)) {
    throw new Error("Missing or invalid apiContracts");
  }
  if (!Array.isArray(arch.pages)) {
    throw new Error("Missing or invalid pages");
  }
  if (!Array.isArray(arch.componentHierarchy)) {
    throw new Error("Missing or invalid componentHierarchy");
  }
  if (!Array.isArray(arch.userFlows)) {
    throw new Error("Missing or invalid userFlows");
  }

  for (const entity of arch.dataModel.entities) {
    if (!entity.tableName || !Array.isArray(entity.fields)) {
      throw new Error(`Invalid entity: missing tableName or fields`);
    }
    for (const field of entity.fields) {
      if (!field.name || !field.type || typeof field.nullable !== "boolean") {
        throw new Error(
          `Invalid field in entity "${entity.tableName}": each field needs name, type, and nullable`,
        );
      }
    }
  }

  for (const contract of arch.apiContracts) {
    if (!contract.method || !contract.path || !contract.description) {
      throw new Error(`Invalid API contract: missing method, path, or description`);
    }
  }

  for (const page of arch.pages) {
    if (!page.name || !page.route || !page.authLevel) {
      throw new Error(`Invalid page: missing name, route, or authLevel`);
    }
  }

  for (const component of arch.componentHierarchy) {
    if (!component.name || !Array.isArray(component.props)) {
      throw new Error(`Invalid component: missing name or props array`);
    }
  }

  for (const flow of arch.userFlows) {
    if (!flow.name || !Array.isArray(flow.steps)) {
      throw new Error(`Invalid user flow: missing name or steps array`);
    }
  }
}
