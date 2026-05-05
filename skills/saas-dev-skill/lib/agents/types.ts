// lib/agents/types.ts
// Shared TypeScript interfaces for the v3 multi-agent architecture.
// All agents communicate through these types via the ArtifactStore.

import type { ProjectBrief } from "../intake/types.js";
import type { ProjectCopy, PageCopy } from "../copy-planner/types.js";
import type { CompetitiveIntel } from "../intake/competitive-researcher.js";
import type { PageSpecFull, SharedComponentSpec, BackendEndpointSpec } from "@shared/spec-schema.js";

// ─── Re-exports for convenience ─────────────────────────────────────────────

export type { ProjectBrief, ProjectCopy, PageCopy, CompetitiveIntel };

// ─── Product Intelligence ───────────────────────────────────────────────────

export interface ProductInsights {
  productCategory: string;
  targetUserProfile: string;
  competitiveIntel: CompetitiveIntel | null;
  designRecommendations: string[];
  copyRecommendations: string[];
  architectureRecommendations: string[];
  marketPositioning: string;
}

// ─── System Architecture ────────────────────────────────────────────────────

export interface EntityField {
  name: string;
  type: string;
  nullable: boolean;
  defaultValue?: string;
  references?: { table: string; column: string };
}

export interface EntityDefinition {
  tableName: string;
  fields: EntityField[];
  indexes: string[];
  timestamps: boolean;
}

export interface EntityRelationship {
  from: string;
  to: string;
  type: "one-to-one" | "one-to-many" | "many-to-many";
  foreignKey: string;
}

export interface DataModel {
  entities: EntityDefinition[];
  relationships: EntityRelationship[];
  enums: Array<{ name: string; values: string[] }>;
}

export type InferenceSource = "explicit" | "implied" | "inferred" | "standard";

export interface ApiContract {
  method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  path: string;
  description: string;
  authRequired: boolean;
  requestBody?: Record<string, string>;
  responseShape: Record<string, string>;
  validationRules: string[];
  relatedEntity: string;
  pageRef?: string;
  source?: InferenceSource;
}

export interface PageStructure {
  name: string;
  route: string;
  authLevel: "public" | "authenticated" | "admin";
  purpose: string;
  components: string[];
  dataNeeds: string[];
  mutations: string[];
  layoutHint?: string;
  emptyState?: string;
  errorState?: string;
  source?: InferenceSource;
}

export interface ComponentHierarchy {
  name: string;
  purpose: string;
  props: Array<{ name: string; type: string; optional: boolean }>;
  usedByPages: string[];
  dependsOn: string[];
}

export interface SystemArchitecture {
  dataModel: DataModel;
  apiContracts: ApiContract[];
  pages: PageStructure[];
  componentHierarchy: ComponentHierarchy[];
  userFlows: Array<{ name: string; steps: string[] }>;
}

// ─── Design System ──────────────────────────────────────────────────────────

export interface DesignTokens {
  colors: Record<string, string>;
  typography: {
    fontFamily: string;
    fontSizes: Record<string, string>;
    fontWeights: Record<string, number>;
    lineHeights: Record<string, string>;
  };
  spacing: Record<string, string>;
  borderRadius: Record<string, string>;
  shadows: Record<string, string>;
  breakpoints: Record<string, string>;
}

export interface DesignSystem {
  tokens: DesignTokens;
  tailwindConfigPath: string;
  cssCustomPropertiesPath: string;
  componentDesignGuidePath: string;
  aesthetic: string;
  colorMode: "light" | "dark" | "user-choice";
}

// ─── Component Interfaces ───────────────────────────────────────────────────

export interface ComponentInterface {
  name: string;
  filePath: string;
  exportName: string;
  props: Array<{ name: string; type: string; optional: boolean; description?: string }>;
  dependsOn: string[];
}

// ─── Page Output ────────────────────────────────────────────────────────────

export interface PageOutput {
  pageName: string;
  filePath: string;
  route: string;
  componentCode: string;
  reviewScore: number;
  reviewFeedback: string[];
  passed: boolean;
  tsErrors: string[];
  fixAttempts: number;
  compiledClean: boolean;
  importViolations: string[];
  nullSafetyIssues: string[];
}

// ─── Backend Route ──────────────────────────────────────────────────────────

export interface BackendRoute {
  method: string;
  path: string;
  filePath: string;
  entity: string;
  schemaGenerated: boolean;
  storageGenerated: boolean;
  migrationPath?: string;
}

// ─── QA Report ──────────────────────────────────────────────────────────────

export interface QAIssue {
  file: string;
  line?: number;
  severity: "error" | "warning";
  category: "typescript" | "import" | "contract" | "state" | "null-safety" | "design" | "consistency";
  message: string;
  autoFixed: boolean;
}

// ─── Design Consistency ────────────────────────────────────────────────────

export interface ConsistencyFinding {
  type: "color" | "component" | "spacing" | "typography";
  description: string;
  pages: string[];
  outlierPage: string;
  fix: string;
}

export interface ConsistencyReport {
  consistent: boolean;
  findings: ConsistencyFinding[];
  pagesChecked: number;
}

export interface QAReport {
  allPassed: boolean;
  totalIssues: number;
  issuesFixed: number;
  remainingIssues: QAIssue[];
  iterations: number;
  tscClean: boolean;
  pageResults: Array<{
    pageName: string;
    passed: boolean;
    issues: QAIssue[];
  }>;
}

// ─── Agent Infrastructure ───────────────────────────────────────────────────

export type AgentStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "retrying";

export interface AgentResult<T> {
  agentName: string;
  status: AgentStatus;
  data: T | null;
  error: string | null;
  durationMs: number;
  retries: number;
}

export interface AgentSignal {
  type: "progress" | "warning" | "error" | "complete";
  agentName: string;
  message: string;
  timestamp: number;
}

// ─── Build State ────────────────────────────────────────────────────────────

export type BuildPhase =
  | "intake"
  | "product-intel"
  | "architecture"
  | "design-system"
  | "copy"
  | "component-library"
  | "pages"
  | "backend"
  | "qa"
  | "complete"
  | "failed";

export interface BuildStatus {
  phase: BuildPhase;
  totalAgents: number;
  completedAgents: string[];
  currentAgents: string[];
  failedAgents: string[];
  startedAt: string;
  updatedAt: string;
}

export interface BuildState {
  projectRoot: string;
  brief: ProjectBrief | null;
  status: BuildStatus;
  agentResults: Record<string, AgentResult<unknown>>;
  checkpoints: Array<{ phase: BuildPhase; timestamp: string }>;
}

export interface BuildResult {
  success: boolean;
  buildState: BuildState;
  qaReport: QAReport | null;
  pagesBuilt: number;
  backendRoutes: number;
  errors: string[];
}

export interface EditResult {
  pagesEdited: string[];
  qaReport: QAReport | null;
  success: boolean;
  errors: string[];
}

// ─── User Defined Constraints ──────────────────────────────────────────────

export interface UserDefinedConstraints {
  explicit: Record<string, string>;
  implicit: Record<string, string>;
  open: string[];
}

export interface CreativeDecision {
  agent: string;
  decision: string;
  rationale: string;
  coherenceCheck: string;
}

// ─── Component Library Recommendations ─────────────────────────────────────

export interface ComponentLibraryRecommendations {
  animationLibrary: string;
  componentLibrary: string;
  premiumComponents: string[];
  rationale: string;
  installCommands: string[];
}

// ─── Existing Codebase Audit ────────────────────────────────────────────────

export interface ExistingCodebaseAudit {
  existingRoutes: string[];
  existingTables: string[];
  existingPages: string[];
  existingStorageMethods: string[];
  scannedAt: string;
}

// ─── Pre-flight Check ──────────────────────────────────────────────────────

export interface PreFlightResult {
  passed: boolean;
  checks: Array<{ name: string; passed: boolean; message: string }>;
}

// ─── Build Plan (approval gate) ─────────────────────────────────────────────

export interface BuildPlan {
  brief: ProjectBrief;
  insights: ProductInsights;
  architecture: SystemArchitecture;
  designSystem: DesignSystem;
  estimatedPages: number;
  estimatedEndpoints: number;
  estimatedComponents: number;
}
