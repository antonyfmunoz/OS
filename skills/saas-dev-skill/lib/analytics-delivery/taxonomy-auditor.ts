import type { PageSpecFull } from "@shared/spec-schema.js";
import type { TaxonomyReport } from "./types.js";

// ─── toSnakeCase ──────────────────────────────────────────────────────────────

/**
 * Normalizes an event name to snake_case per D-04.
 * Lowercase, replace spaces/hyphens/non-alphanumeric with underscores,
 * collapse consecutive underscores, trim leading/trailing underscores.
 */
export function toSnakeCase(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_|_$/g, "");
}

// ─── auditTaxonomy ────────────────────────────────────────────────────────────

/**
 * Audits PageSpec analytics layers and returns a structured TaxonomyReport.
 * Pure function — no I/O.
 *
 * Addresses Codex review concern: returns structured result on empty input,
 * does NOT throw. Addresses collision detection concern: detects when distinct
 * event names normalize to the same snake_case key.
 */
export function auditTaxonomy(pageSpecs: PageSpecFull[]): TaxonomyReport {
  // EMPTY INPUT — addresses Codex review: return structured result, not throw
  if (pageSpecs.length === 0) {
    return {
      valid: false,
      errors: [
        "auditTaxonomy: no page specs provided — Phase 2 pipeline_pages analytics layers must exist before auditing. Run spec-parser first.",
      ],
      warnings: [],
      totalPages: 0,
      pagesWithEvents: 0,
      pagesWithoutEvents: [],
      totalEvents: 0,
      allEvents: [],
      allFlagCandidates: [],
      collisions: [],
    };
  }

  const errors: string[] = [];
  const warnings: string[] = [];
  const pagesWithoutEvents: string[] = [];
  let pagesWithEvents = 0;
  let totalEvents = 0;
  const allEvents: TaxonomyReport["allEvents"] = [];
  const allFlagCandidates: string[] = [];

  for (const spec of pageSpecs) {
    const pageEvents = spec.events ?? [];

    if (pageEvents.length === 0) {
      pagesWithoutEvents.push(spec.name);
    } else {
      pagesWithEvents++;
    }

    totalEvents += pageEvents.length;

    for (const event of pageEvents) {
      const normalized = toSnakeCase(event.name);
      allEvents.push({
        pageName: spec.name,
        eventName: normalized,
        originalName: event.name,
        trigger: event.trigger,
      });
    }

    if (spec.featureFlagCandidates) {
      allFlagCandidates.push(...spec.featureFlagCandidates);
    }
  }

  // COLLISION DETECTION — addresses Codex review
  // Group events by normalized eventName, find where distinct originalNames share the same key
  const normalizedToOriginals = new Map<string, Set<string>>();
  for (const event of allEvents) {
    const originals = normalizedToOriginals.get(event.eventName) ?? new Set<string>();
    originals.add(event.originalName);
    normalizedToOriginals.set(event.eventName, originals);
  }

  const collisions: string[] = [];
  for (const [normalized, originals] of normalizedToOriginals.entries()) {
    if (originals.size > 1) {
      collisions.push(normalized);
      const originalList = Array.from(originals);
      for (let i = 0; i < originalList.length - 1; i++) {
        for (let j = i + 1; j < originalList.length; j++) {
          warnings.push(
            `Event name collision: '${originalList[i]}' and '${originalList[j]}' both normalize to '${normalized}'`
          );
        }
      }
    }
  }

  const valid = errors.length === 0;

  return {
    valid,
    errors,
    warnings,
    totalPages: pageSpecs.length,
    pagesWithEvents,
    pagesWithoutEvents,
    totalEvents,
    allEvents,
    allFlagCandidates,
    collisions,
  };
}
