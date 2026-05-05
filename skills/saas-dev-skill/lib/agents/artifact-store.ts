// lib/agents/artifact-store.ts
// Central artifact store for inter-agent communication.
// All agents read/write typed artifacts through this store.
// Artifacts are persisted as JSON under .planning/artifacts/.

import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import type {
  ProductInsights,
  SystemArchitecture,
  DesignSystem,
  ComponentInterface,
  ComponentLibraryRecommendations,
  UserDefinedConstraints,
  CreativeDecision,
  PageOutput,
  BackendRoute,
  QAReport,
  BuildState,
  BuildStatus,
  AgentResult,
  ExistingCodebaseAudit,
} from "./types.js";
import type { ProjectBrief } from "../intake/types.js";
import type { ProjectCopy } from "../copy-planner/types.js";
import type { CompetitiveIntel } from "../intake/competitive-researcher.js";

type ArtifactKey =
  | "brief"
  | "product-insights"
  | "competitive-intel"
  | "existing-codebase-audit"
  | "user-defined-constraints"
  | "creative-decisions"
  | "component-library-recommendations"
  | "architecture"
  | "design-system"
  | "project-copy"
  | "component-interfaces"
  | "component-paths"
  | "page-outputs"
  | "backend-routes"
  | "qa-report"
  | "build-state"
  | "build-status";

export class ArtifactStore {
  private readonly artifactsDir: string;
  private readonly projectRoot: string;

  constructor(projectRoot: string) {
    this.projectRoot = projectRoot;
    this.artifactsDir = path.join(projectRoot, ".planning", "artifacts");
    if (!fs.existsSync(this.artifactsDir)) {
      fs.mkdirSync(this.artifactsDir, { recursive: true });
    }
  }

  // ─── Generic read/write ─────────────────────────────────────────────────

  private artifactPath(key: ArtifactKey): string {
    return path.join(this.artifactsDir, `${key}.json`);
  }

  private writeAtomic(filePath: string, data: unknown): void {
    const content = JSON.stringify(data, null, 2);
    const tmpPath = path.join(
      os.tmpdir(),
      `artifact-${Date.now()}-${Math.random().toString(36).slice(2)}.json`,
    );
    fs.writeFileSync(tmpPath, content, "utf-8");
    const dir = path.dirname(filePath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    fs.renameSync(tmpPath, filePath);
  }

  private readJson<T>(filePath: string): T | null {
    if (!fs.existsSync(filePath)) return null;
    const content = fs.readFileSync(filePath, "utf-8");
    return JSON.parse(content) as T;
  }

  exists(key: ArtifactKey): boolean {
    return fs.existsSync(this.artifactPath(key));
  }

  // ─── Brief ──────────────────────────────────────────────────────────────

  setBrief(brief: ProjectBrief): void {
    this.writeAtomic(this.artifactPath("brief"), brief);
  }

  getBrief(): ProjectBrief | null {
    return this.readJson<ProjectBrief>(this.artifactPath("brief"));
  }

  // ─── Product Insights ───────────────────────────────────────────────────

  setProductInsights(insights: ProductInsights): void {
    this.writeAtomic(this.artifactPath("product-insights"), insights);
  }

  getProductInsights(): ProductInsights | null {
    return this.readJson<ProductInsights>(this.artifactPath("product-insights"));
  }

  // ─── Competitive Intel ──────────────────────────────────────────────────

  setCompetitiveIntel(intel: CompetitiveIntel): void {
    this.writeAtomic(this.artifactPath("competitive-intel"), intel);
  }

  getCompetitiveIntel(): CompetitiveIntel | null {
    return this.readJson<CompetitiveIntel>(this.artifactPath("competitive-intel"));
  }

  // ─── Existing Codebase Audit ─────────────────────────────────────────────

  setExistingCodebaseAudit(audit: ExistingCodebaseAudit): void {
    this.writeAtomic(this.artifactPath("existing-codebase-audit"), audit);
  }

  getExistingCodebaseAudit(): ExistingCodebaseAudit | null {
    return this.readJson<ExistingCodebaseAudit>(this.artifactPath("existing-codebase-audit"));
  }

  // ─── User Defined Constraints ────────────────────────────────────────────

  setUserDefinedConstraints(constraints: UserDefinedConstraints): void {
    this.writeAtomic(this.artifactPath("user-defined-constraints"), constraints);
  }

  getUserDefinedConstraints(): UserDefinedConstraints | null {
    return this.readJson<UserDefinedConstraints>(this.artifactPath("user-defined-constraints"));
  }

  // ─── Creative Decisions ─────────────────────────────────────────────────

  appendCreativeDecision(decision: CreativeDecision): void {
    const existing = this.getCreativeDecisions();
    existing.push(decision);
    this.writeAtomic(this.artifactPath("creative-decisions"), existing);
  }

  getCreativeDecisions(): CreativeDecision[] {
    return this.readJson<CreativeDecision[]>(this.artifactPath("creative-decisions")) ?? [];
  }

  // ─── Component Library Recommendations ───────────────────────────────────

  setComponentLibraryRecommendations(recs: ComponentLibraryRecommendations): void {
    this.writeAtomic(this.artifactPath("component-library-recommendations"), recs);
  }

  getComponentLibraryRecommendations(): ComponentLibraryRecommendations | null {
    return this.readJson<ComponentLibraryRecommendations>(this.artifactPath("component-library-recommendations"));
  }

  // ─── Architecture ───────────────────────────────────────────────────────

  setArchitecture(arch: SystemArchitecture): void {
    this.writeAtomic(this.artifactPath("architecture"), arch);
  }

  getArchitecture(): SystemArchitecture | null {
    return this.readJson<SystemArchitecture>(this.artifactPath("architecture"));
  }

  // ─── Design System ──────────────────────────────────────────────────────

  setDesignSystem(ds: DesignSystem): void {
    this.writeAtomic(this.artifactPath("design-system"), ds);
  }

  getDesignSystem(): DesignSystem | null {
    return this.readJson<DesignSystem>(this.artifactPath("design-system"));
  }

  // ─── Project Copy ───────────────────────────────────────────────────────

  setProjectCopy(copy: ProjectCopy): void {
    this.writeAtomic(this.artifactPath("project-copy"), copy);
  }

  getProjectCopy(): ProjectCopy | null {
    return this.readJson<ProjectCopy>(this.artifactPath("project-copy"));
  }

  // ─── Component Interfaces ───────────────────────────────────────────────

  setComponentInterfaces(interfaces: ComponentInterface[]): void {
    this.writeAtomic(this.artifactPath("component-interfaces"), interfaces);
  }

  getComponentInterfaces(): ComponentInterface[] | null {
    return this.readJson<ComponentInterface[]>(this.artifactPath("component-interfaces"));
  }

  // ─── Component Paths ────────────────────────────────────────────────────

  setComponentPaths(paths: Record<string, string>): void {
    this.writeAtomic(this.artifactPath("component-paths"), paths);
  }

  getComponentPaths(): Record<string, string> | null {
    return this.readJson<Record<string, string>>(this.artifactPath("component-paths"));
  }

  // ─── Page Outputs ───────────────────────────────────────────────────────

  setPageOutputs(pages: PageOutput[]): void {
    this.writeAtomic(this.artifactPath("page-outputs"), pages);
  }

  getPageOutputs(): PageOutput[] | null {
    return this.readJson<PageOutput[]>(this.artifactPath("page-outputs"));
  }

  addPageOutput(page: PageOutput): void {
    const existing = this.getPageOutputs() ?? [];
    const idx = existing.findIndex((p) => p.pageName === page.pageName);
    if (idx >= 0) {
      existing[idx] = page;
    } else {
      existing.push(page);
    }
    this.setPageOutputs(existing);
  }

  // ─── Backend Routes ─────────────────────────────────────────────────────

  setBackendRoutes(routes: BackendRoute[]): void {
    this.writeAtomic(this.artifactPath("backend-routes"), routes);
  }

  getBackendRoutes(): BackendRoute[] | null {
    return this.readJson<BackendRoute[]>(this.artifactPath("backend-routes"));
  }

  addBackendRoute(route: BackendRoute): void {
    const existing = this.getBackendRoutes() ?? [];
    const idx = existing.findIndex(
      (r) => r.method === route.method && r.path === route.path,
    );
    if (idx >= 0) {
      existing[idx] = route;
    } else {
      existing.push(route);
    }
    this.setBackendRoutes(existing);
  }

  // ─── QA Report ──────────────────────────────────────────────────────────

  setQAReport(report: QAReport): void {
    this.writeAtomic(this.artifactPath("qa-report"), report);
  }

  getQAReport(): QAReport | null {
    return this.readJson<QAReport>(this.artifactPath("qa-report"));
  }

  // ─── Build State ────────────────────────────────────────────────────────

  setBuildState(state: BuildState): void {
    this.writeAtomic(this.artifactPath("build-state"), state);
  }

  getBuildState(): BuildState | null {
    return this.readJson<BuildState>(this.artifactPath("build-state"));
  }

  // ─── Build Status (for overlay) ─────────────────────────────────────────

  setBuildStatus(status: BuildStatus): void {
    this.writeAtomic(this.artifactPath("build-status"), status);
    // Also write to public/ for the browser overlay
    const publicPath = path.join(this.projectRoot, "public", "build-status.json");
    const publicDir = path.dirname(publicPath);
    if (!fs.existsSync(publicDir)) {
      fs.mkdirSync(publicDir, { recursive: true });
    }
    this.writeAtomic(publicPath, status);
  }

  getBuildStatus(): BuildStatus | null {
    return this.readJson<BuildStatus>(this.artifactPath("build-status"));
  }

  // ─── Agent Results ──────────────────────────────────────────────────────

  /** Sanitize agent names for use as filenames (colons are illegal on Windows). */
  private sanitizeFilename(name: string): string {
    return name.replace(/:/g, "-");
  }

  setAgentResult(name: string, result: AgentResult<unknown>): void {
    const safeName = this.sanitizeFilename(name);
    const resultsPath = path.join(this.artifactsDir, "agent-results", `${safeName}.json`);
    this.writeAtomic(resultsPath, result);
  }

  getAgentResult<T>(name: string): AgentResult<T> | null {
    const safeName = this.sanitizeFilename(name);
    const resultsPath = path.join(this.artifactsDir, "agent-results", `${safeName}.json`);
    return this.readJson<AgentResult<T>>(resultsPath);
  }

  // ─── Build Log ──────────────────────────────────────────────────────────

  appendBuildLog(entry: { agent: string; event: string; timestamp: number; detail?: string }): void {
    const logPath = path.join(this.artifactsDir, "build-log.jsonl");
    const line = JSON.stringify(entry) + "\n";
    fs.appendFileSync(logPath, line, "utf-8");
  }

  // ─── Project File Writes ────────────────────────────────────────────────

  writeProjectFile(relativePath: string, content: string): void {
    const fullPath = path.join(this.projectRoot, relativePath);
    const dir = path.dirname(fullPath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    fs.writeFileSync(fullPath, content, "utf-8");
  }

  readProjectFile(relativePath: string): string | null {
    const fullPath = path.join(this.projectRoot, relativePath);
    if (!fs.existsSync(fullPath)) return null;
    return fs.readFileSync(fullPath, "utf-8");
  }

  getProjectRoot(): string {
    return this.projectRoot;
  }
}
