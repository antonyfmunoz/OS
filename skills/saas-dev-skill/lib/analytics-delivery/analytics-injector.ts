import type { AnalyticsInjection } from "./types.js";
import { toSnakeCase } from "./taxonomy-auditor.js";

// ─── Types ────────────────────────────────────────────────────────────────────

interface PageEventSpec {
  name: string;
  trigger: string;
  properties: string[];
}

interface PageSpec {
  name: string;
  filePath: string;
  events: PageEventSpec[];
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

// Triggers that can be auto-injected as useEffect load events
const LOAD_TRIGGERS = new Set(["load", "page_view", "mount"]);

function buildPropsObj(properties: string[]): string {
  if (properties.length === 0) return "";
  const props = properties.map((p) => `${p}: undefined /* TODO: wire */`).join(", ");
  return `, { ${props} }`;
}

// ─── generateAnalyticsInjections ─────────────────────────────────────────────

/**
 * Generates PostHog capture injection descriptors for each page component.
 *
 * Load/page_view/mount triggers -> auto-injectable useEffect with useRef dedupe guard
 * Click/submit triggers -> structured manualCaptures with copy-paste captureSnippet
 *
 * Addresses consensus review concern: click events are NOT comment markers —
 * they appear in manualCaptures as structured objects with captureSnippet.
 * Addresses React 18 Strict Mode concern: useRef dedupe guard prevents double-fire.
 */
export function generateAnalyticsInjections(pageSpecs: PageSpec[]): AnalyticsInjection[] {
  const injections: AnalyticsInjection[] = [];

  for (const spec of pageSpecs) {
    // Skip pages with no events
    if (spec.events.length === 0) continue;

    const loadEvents = spec.events.filter((e) => LOAD_TRIGGERS.has(e.trigger));
    const manualEvents = spec.events.filter((e) => !LOAD_TRIGGERS.has(e.trigger));

    // importCode — includes useRef for React 18 Strict Mode dedupe
    const importCode = [
      `import { usePostHog } from "posthog-js/react";`,
      `import { useEffect, useRef } from "react";`,
    ].join("\n");

    // hookCode — posthog hook initialization
    const hookCode = `const posthog = usePostHog();`;

    // captureCode — useRef dedupe guard + useEffect per React 18 Strict Mode recommendation
    // The useRef(false) is included here so captureCode is self-contained for injection
    let captureCode = "";
    if (loadEvents.length > 0) {
      const captureLines = loadEvents.map((event) => {
        const eventName = toSnakeCase(event.name);
        const propsObj = buildPropsObj(event.properties);
        return `    posthog?.capture("${eventName}"${propsObj});`;
      });
      captureCode = [
        `const hasFired = useRef(false);`,
        `useEffect(() => {`,
        `  if (hasFired.current) return;`,
        `  hasFired.current = true;`,
        ...captureLines,
        `}, []);`,
      ].join("\n");
    }

    // manualCaptures — structured objects with copy-paste captureSnippet (NOT comment markers)
    const manualCaptures = manualEvents.map((event) => {
      const eventName = toSnakeCase(event.name);
      const propsObj = buildPropsObj(event.properties);
      return {
        eventName,
        trigger: event.trigger,
        captureSnippet: `posthog?.capture("${eventName}"${propsObj})`,
        properties: event.properties,
      };
    });

    // events — full list for reference
    const events = spec.events.map((event) => ({
      name: toSnakeCase(event.name),
      trigger: event.trigger,
      properties: event.properties,
    }));

    injections.push({
      pageFilePath: spec.filePath,
      pageName: spec.name,
      importCode,
      hookCode,
      captureCode,
      manualCaptures,
      events,
    });
  }

  return injections;
}

// ─── buildProviderCode ────────────────────────────────────────────────────────

/**
 * Returns PostHogProvider initialization code for App.tsx.
 * Guards init behind VITE_POSTHOG_API_KEY check per D-03.
 * Per Research Pattern 1: App.tsx provider approach.
 */
export function buildProviderCode(): string {
  return [
    `import posthog from "posthog-js";`,
    `import { PostHogProvider } from "posthog-js/react";`,
    ``,
    `// Initialize PostHog — guarded by env var so builds without key still work`,
    `if (import.meta.env.VITE_POSTHOG_API_KEY) {`,
    `  posthog.init(import.meta.env.VITE_POSTHOG_API_KEY, {`,
    `    api_host: import.meta.env.VITE_POSTHOG_HOST ?? "https://app.posthog.com",`,
    `    capture_pageview: true,`,
    `    capture_pageleave: true,`,
    `  });`,
    `}`,
    ``,
    `// Wrap your root component:`,
    `// <PostHogProvider client={posthog}>`,
    `//   {children}`,
    `// </PostHogProvider>`,
  ].join("\n");
}

// ─── buildIdentifyCode ────────────────────────────────────────────────────────

/**
 * Returns identify/reset code for the auth context hook.
 * Per D-05: identifies users on login, resets on logout.
 *
 * "firebase" | "passport" -> returns useEffect with posthog.identify/reset
 * null -> returns "" (anonymous events only, no identify wiring)
 */
export function buildIdentifyCode(authProvider: "firebase" | "passport" | null): string {
  if (authProvider === null) return "";

  // Both firebase and passport use the same identify pattern
  // firebase: user.id is a string UID; passport: user.id is numeric (toString)
  const idExpr = authProvider === "firebase" ? "user.id" : "user.id.toString()";

  return [
    `useEffect(() => {`,
    `  if (user) {`,
    `    posthog.identify(${idExpr}, { email: user.email, name: user.username });`,
    `  } else {`,
    `    posthog.reset();`,
    `  }`,
    `}, [user]);`,
  ].join("\n");
}
