---
name: saas-dev:detect-framework
description: Detects the frontend framework stack of a SaaS project by reading its package.json. Use when the saas-dev pipeline needs to identify whether a project uses React+Vite+Tailwind+shadcn/ui or another supported framework configuration before integration or code generation steps.
---

# detect-framework

Detects the frontend framework stack from a project's package.json. Returns a structured result with detected components, confidence level, and a list of missing stack elements.

## Output

Returns a `FrameworkDetectionResult` object:

- `framework` -- `"react-vite-tailwind-shadcn"` if full stack detected, `"unknown"` otherwise
- `detected` -- boolean flags: `{ react, vite, tailwind, shadcn }`
- `confidence` -- `"HIGH"` (all 4 detected), `"MEDIUM"` (2-3 detected), `"LOW"` (0-1 detected)
- `missing` -- array of missing stack component names (empty when confidence is HIGH)

## Detection Logic

1. Read `package.json` from project root (caller responsibility -- pass parsed object)
2. Merge `dependencies` and `devDependencies` into a single key set
3. Check for presence of:
   - `react` in merged deps
   - `vite` in devDependencies
   - `tailwindcss` in devDependencies
   - shadcn/ui: `components.json` file exists in repo root (definitive), OR 3+ `@radix-ui/react-*` packages (heuristic fallback)
4. Score: 4/4 = HIGH + full framework name; 2-3/4 = MEDIUM + unknown; 0-1 = LOW + unknown

## Implementation

Function at `lib/detect-framework.ts`. Pure function -- no file I/O, no side effects.

Usage example:

```typescript
import { detectFramework } from "../../lib/detect-framework.js";
import fs from "fs";
import path from "path";

const pkg = JSON.parse(fs.readFileSync(path.join(repoPath, "package.json"), "utf-8"));
const hasComponentsJson = fs.existsSync(path.join(repoPath, "components.json"));
const result = detectFramework(pkg, hasComponentsJson);
```

## Extensibility

To add support for a new framework (e.g., Next.js, Vue/Nuxt):

1. Add new detection keys to the function's check logic (check for `next`, `nuxt`, etc.)
2. Update the `framework` union type in `FrameworkDetectionResult`
3. Update the `framework` enum in `ProjectConfigSchema` in `shared/design-schema.ts`
4. Add confidence scoring thresholds for the new stack
5. Add corresponding test cases in `tests/unit/detect-framework.test.ts`
