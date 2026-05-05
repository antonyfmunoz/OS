import { describe, it, expect } from "vitest";
import { injectImport } from "../../../lib/orchestrator/phases/deploy-adapter.js";

// Bug 4 regression: PostHog import injection must respect multi-line import
// blocks. Previously we inserted after the first line matching /^import/,
// which wedged the new import between `import {` and its members.
describe("injectImport (Bug 4)", () => {
  const POSTHOG_IMPORT = `import posthog from "posthog-js";`;

  it("inserts after a simple single-line import", () => {
    const source = [
      `import React from "react";`,
      ``,
      `export default function Page() { return null; }`,
    ].join("\n");
    const result = injectImport(source, POSTHOG_IMPORT);
    expect(result).toContain(`import React from "react";\nimport posthog from "posthog-js";`);
  });

  it("does not corrupt a multi-line lucide-react import block", () => {
    const source = [
      `import { useState } from "react";`,
      `import {`,
      `  Bot,`,
      `  ArrowRight,`,
      `  Settings,`,
      `} from "lucide-react";`,
      ``,
      `export default function Page() { return null; }`,
    ].join("\n");

    const result = injectImport(source, POSTHOG_IMPORT);

    // The original multi-line import must be intact.
    expect(result).toContain(`import {\n  Bot,\n  ArrowRight,\n  Settings,\n} from "lucide-react";`);
    // The new import lands AFTER the closing `} from "lucide-react";`
    const lucideCloseIdx = result.indexOf(`} from "lucide-react";`);
    const posthogIdx = result.indexOf(POSTHOG_IMPORT);
    expect(posthogIdx).toBeGreaterThan(lucideCloseIdx);
  });

  it("is idempotent when posthog-js is already imported", () => {
    const source = `import posthog from "posthog-js";\nexport default function X() {}`;
    const result = injectImport(source, POSTHOG_IMPORT);
    expect(result).toBe(source);
  });

  it("prepends when no imports exist", () => {
    const source = `export default function X() {}`;
    const result = injectImport(source, POSTHOG_IMPORT);
    expect(result.startsWith(POSTHOG_IMPORT)).toBe(true);
  });
});
