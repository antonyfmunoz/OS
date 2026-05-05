import type { PageSpecFull, SpecOutput } from "@shared/spec-schema.js";

// ─── applySpecEdit ────────────────────────────────────────────────────────────

/**
 * Applies a surgical edit to a single page in the spec by route.
 *
 * Implements D-16: version bumping — bumps specVersion on the replaced page.
 * Implements D-18: all other pages remain unchanged.
 * Returns a new SpecOutput (immutable — does not mutate the input).
 *
 * @throws If the target page route is not found in spec.pages
 */
export function applySpecEdit(
  spec: SpecOutput,
  targetRoute: string,
  updatedPage: PageSpecFull
): SpecOutput {
  const pageIndex = spec.pages.findIndex((p) => p.route === targetRoute);

  if (pageIndex === -1) {
    throw new Error(
      `Page with route '${targetRoute}' not found in spec`
    );
  }

  const originalPage = spec.pages[pageIndex];
  const bumpedPage: PageSpecFull = {
    ...updatedPage,
    specVersion: (originalPage.specVersion ?? 1) + 1,
  };

  const newPages = [
    ...spec.pages.slice(0, pageIndex),
    bumpedPage,
    ...spec.pages.slice(pageIndex + 1),
  ];

  return {
    ...spec,
    pages: newPages,
  };
}

// ─── flagDependentPages ───────────────────────────────────────────────────────

/**
 * Scans all pages and returns routes of pages whose dependsOn array includes
 * the edited page's route.
 *
 * Implements D-17: these pages should be flagged for review but not modified.
 * The caller is responsible for showing the confirmation gate for flagged pages.
 */
export function flagDependentPages(
  spec: SpecOutput,
  editedRoute: string
): string[] {
  return spec.pages
    .filter((page) => page.dependsOn.includes(editedRoute))
    .map((page) => page.route);
}

// ─── markProvenance ───────────────────────────────────────────────────────────

/**
 * Marks provenance on all items in a SpecOutput by comparing against the
 * original user input page names.
 *
 * - Pages whose name appears in originalInputPageNames → source: "explicit"
 * - All other pages → source: "inferred"
 * - SharedComponents whose name appears in originalInputPageNames → source: "explicit"
 * - All other shared components → source: "inferred"
 *
 * This is called by the skill after restructuring to mark provenance based on
 * comparing AI output against the user's original input.
 *
 * Returns a new SpecOutput (immutable — does not mutate the input).
 */
export function markProvenance(
  spec: SpecOutput,
  originalInputPageNames: string[]
): SpecOutput {
  const nameSet = new Set(originalInputPageNames);

  const markedPages: PageSpecFull[] = spec.pages.map((page) => ({
    ...page,
    source: nameSet.has(page.name) ? ("explicit" as const) : ("inferred" as const),
  }));

  const markedComponents = spec.sharedComponents.map((component) => ({
    ...component,
    source: nameSet.has(component.name) ? ("explicit" as const) : ("inferred" as const),
  }));

  return {
    ...spec,
    pages: markedPages,
    sharedComponents: markedComponents,
  };
}
