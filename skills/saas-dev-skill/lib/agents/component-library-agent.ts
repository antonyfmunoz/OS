// lib/agents/component-library-agent.ts
// Wraps the shared-component-builder with design system context and
// interface extraction. Builds all shared components, then extracts
// TypeScript interfaces from the generated files and persists them
// in the ArtifactStore for downstream page agents to consume.

import fs from "node:fs";
import path from "node:path";
import { buildSharedComponents, SHARED_COMPONENTS } from "../react-gen/shared-component-builder.js";
import {
  autoFixImports,
  validateImports,
  scanForNullUnsafePatterns,
  runTscCheck,
} from "../react-gen/component-writer.js";
import { ArtifactStore } from "./artifact-store.js";
import type { ComponentInterface, SystemArchitecture, DesignSystem } from "./types.js";
import type { ProjectBrief } from "../intake/types.js";

// ─── Component Design Standards (injected into shared-component-builder context) ─

export const COMPONENT_DESIGN_STANDARDS = `
COMPONENT DESIGN STANDARDS:
Every component must be production-grade and visually distinctive:

- Buttons: not flat rectangles. Consider subtle depth, precise hover states, micro-animations on click
- Cards: use shadow and layering for depth. Hover states should feel satisfying.
- Inputs: styled focus states with color. Not just a border color change — consider glow, scale.
- Navigation: clear active states. Smooth transitions between states.
- Loading states: skeleton screens that match the layout, not generic spinners
- Empty states: illustrated or typographic — never just "No data found"
- Motion: use the animation library chosen for this product. Page loads should feel orchestrated.
`;

/**
 * Build dynamic component library knowledge from the recommendations
 * stored in the ArtifactStore by the design system agent's research step.
 */
export function buildComponentLibraryKnowledge(store: ArtifactStore): string {
  const recs = store.getComponentLibraryRecommendations();
  if (!recs) {
    return `COMPONENT LIBRARY KNOWLEDGE:
shadcn/ui components available. No premium component recommendations available — use shadcn/ui primitives only.`;
  }

  const sections: string[] = [
    `COMPONENT LIBRARY KNOWLEDGE (researched for this product):`,
    ``,
    `Animation library: ${recs.animationLibrary}`,
    `Component library: ${recs.componentLibrary}`,
    `Premium sources: ${recs.premiumComponents.length > 0 ? recs.premiumComponents.join(", ") : "none"}`,
    `Rationale: ${recs.rationale}`,
    ``,
    `Install commands:`,
    ...recs.installCommands.map((cmd) => `  ${cmd}`),
    ``,
    `When building components:`,
    `1. If a premium component is needed, check if it's available via MCP (shadcn MCP, MagicUI MCP, 21st.dev MCP)`,
    `2. If MCP available: fetch the actual component code via MCP`,
    `3. If no MCP: generate an equivalent from scratch based on the library's patterns`,
    `4. Install it to client/src/components/ui/{name}.tsx`,
    ``,
    `Use ONLY the animation library above. Do not use any other animation library.`,
    `Build what THIS product needs — not a generic component set.`,
  ];

  return sections.join("\n");
}

// ─── MCP Component Discovery ────────────────────────────────────────────────

export interface ComponentReference {
  name: string;
  source: "shadcn" | "magicui" | "21st-dev" | "built-in";
  description: string;
  installCommand?: string;
  props?: Array<{ name: string; type: string; optional: boolean }>;
  usageExample?: string;
}

export async function discoverComponentsFromMCP(
  componentNames: string[],
  mcpInvoker?: (tool: string, args: unknown) => Promise<unknown>,
): Promise<ComponentReference[]> {
  if (!mcpInvoker) {
    console.log("  [component-library] Running headless — using built-in component knowledge");
    return componentNames.map((name) => resolveFromBuiltInKnowledge(name));
  }

  const results: ComponentReference[] = [];

  for (const name of componentNames) {
    let found = false;

    // Query shadcn MCP
    try {
      const shadcnResult = await mcpInvoker("mcp__magicui__getRegistryItem", { name: name.toLowerCase() });
      if (shadcnResult) {
        results.push({
          name,
          source: "shadcn",
          description: `shadcn/ui ${name} component`,
          installCommand: `npx shadcn@latest add ${name.toLowerCase()}`,
          props: extractPropsFromMCPResult(shadcnResult),
        });
        found = true;
      }
    } catch {
      // Not found in shadcn, continue
    }

    // Query MagicUI MCP for animated variants
    if (!found) {
      try {
        const magicResult = await mcpInvoker("mcp__magicui__searchRegistryItems", { query: name });
        if (magicResult && Array.isArray(magicResult) && magicResult.length > 0) {
          const item = magicResult[0] as { name?: string; description?: string };
          results.push({
            name,
            source: "magicui",
            description: item.description ?? `MagicUI ${name} component`,
            installCommand: `npx magicui-cli@latest add ${(item.name ?? name).toLowerCase()}`,
          });
          found = true;
        }
      } catch {
        // Not found in MagicUI, continue
      }
    }

    // Query 21st.dev MCP for design patterns
    if (!found) {
      try {
        const patternResult = await mcpInvoker("mcp__magic21__21st_magic_component_inspiration", {
          message: `${name} component pattern`,
        });
        if (patternResult) {
          results.push({
            name,
            source: "21st-dev",
            description: `21st.dev pattern for ${name}`,
            usageExample: typeof patternResult === "string" ? patternResult : undefined,
          });
          found = true;
        }
      } catch {
        // Not found via 21st.dev, continue
      }
    }

    // Fall back to built-in knowledge
    if (!found) {
      results.push(resolveFromBuiltInKnowledge(name));
    }
  }

  return results;
}

const SHADCN_COMPONENTS = new Set([
  "Button", "Input", "Label", "Card", "CardHeader", "CardContent", "CardFooter",
  "Dialog", "DialogContent", "DialogHeader", "DialogFooter", "Sheet", "SheetContent",
  "Tabs", "TabsList", "TabsTrigger", "TabsContent", "Table", "TableHeader", "TableBody",
  "TableRow", "TableCell", "Select", "SelectTrigger", "SelectContent", "SelectItem",
  "Checkbox", "RadioGroup", "RadioGroupItem", "Switch", "Slider", "Textarea", "Badge",
  "Avatar", "AvatarImage", "AvatarFallback", "Separator", "Skeleton", "Toast", "Toaster",
  "ScrollArea", "DropdownMenu", "DropdownMenuContent", "DropdownMenuItem", "Tooltip",
  "TooltipContent", "Alert", "AlertTitle", "AlertDescription", "Progress", "Calendar",
  "Popover", "PopoverContent", "Command", "CommandInput", "CommandList", "CommandItem",
]);

function resolveFromBuiltInKnowledge(name: string): ComponentReference {
  if (SHADCN_COMPONENTS.has(name)) {
    return {
      name,
      source: "shadcn",
      description: `shadcn/ui ${name} component`,
      installCommand: `npx shadcn@latest add ${name.toLowerCase()}`,
    };
  }

  // No hardcoded premium component list — discovery via MCP or generation at build time
  return {
    name,
    source: "built-in",
    description: `Custom ${name} component — will be generated or fetched via MCP`,
  };
}

function extractPropsFromMCPResult(result: unknown): Array<{ name: string; type: string; optional: boolean }> | undefined {
  // MCP results vary in shape — extract props if structured data is present
  if (result && typeof result === "object" && "props" in result && Array.isArray((result as { props: unknown }).props)) {
    return ((result as { props: Array<{ name?: string; type?: string; optional?: boolean }> }).props).map((p) => ({
      name: p.name ?? "unknown",
      type: p.type ?? "unknown",
      optional: p.optional ?? false,
    }));
  }
  return undefined;
}

// ─── Interface Extraction ────────────────────────────────────────────────────

interface ExtractedProp {
  name: string;
  type: string;
  optional: boolean;
}

function extractPropsFromBlock(block: string): ExtractedProp[] {
  const props: ExtractedProp[] = [];
  // Match each line inside the interface/type body: name?: type; or name: type;
  const propPattern = /^\s*(\w+)(\?)?:\s*(.+?);?\s*$/gm;
  let match: RegExpExecArray | null;
  while ((match = propPattern.exec(block)) !== null) {
    const name = match[1];
    const optional = match[2] === "?";
    const type = match[3].replace(/;$/, "").trim();
    // Skip index signatures and methods
    if (name === "children" || /^\[/.test(name)) continue;
    props.push({ name, type, optional });
  }
  return props;
}

function extractComponentInterface(
  fileContent: string,
  filePath: string,
  componentName: string,
): ComponentInterface {
  // Extract props interface: interface FooProps { ... }
  const interfacePattern = /(?:export\s+)?interface\s+(\w+Props)\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}/gs;
  const typePattern = /(?:export\s+)?type\s+(\w+Props)\s*=\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}/gs;

  let props: ExtractedProp[] = [];
  let propsTypeName = "";

  // Try interface first
  let propsMatch = interfacePattern.exec(fileContent);
  if (propsMatch) {
    propsTypeName = propsMatch[1];
    props = extractPropsFromBlock(propsMatch[2]);
  } else {
    // Fall back to type alias
    propsMatch = typePattern.exec(fileContent);
    if (propsMatch) {
      propsTypeName = propsMatch[1];
      props = extractPropsFromBlock(propsMatch[2]);
    }
  }

  // Extract export name: export default function Foo or export function Foo
  let exportName = componentName;
  const defaultExportMatch = /export\s+default\s+function\s+(\w+)/.exec(fileContent);
  if (defaultExportMatch) {
    exportName = defaultExportMatch[1];
  } else {
    const namedExportMatch = /export\s+function\s+(\w+)/.exec(fileContent);
    if (namedExportMatch) {
      exportName = namedExportMatch[1];
    }
  }

  // Extract dependsOn from import statements
  const dependsOn: string[] = [];
  const importPattern = /import\s+.*?\s+from\s+['"]([^'"]+)['"]/g;
  let importMatch: RegExpExecArray | null;
  while ((importMatch = importPattern.exec(fileContent)) !== null) {
    const source = importMatch[1];
    // Only track internal component dependencies, not external packages
    if (source.startsWith("@/components/") && !source.includes("/ui/")) {
      // Extract the component file name from the import path
      const segments = source.split("/");
      const last = segments[segments.length - 1];
      dependsOn.push(last.replace(/\.tsx?$/, ""));
    } else if (source.startsWith("@/lib/")) {
      const segments = source.split("/");
      const last = segments[segments.length - 1];
      dependsOn.push(last.replace(/\.ts$/, ""));
    }
  }

  return {
    name: componentName,
    filePath,
    exportName,
    props: props.map((p) => ({
      name: p.name,
      type: p.type,
      optional: p.optional,
    })),
    dependsOn,
  };
}

// ─── Agent Entry Point ───────────────────────────────────────────────────────

export async function runComponentLibraryAgent(
  brief: ProjectBrief,
  store: ArtifactStore,
): Promise<Record<string, string>> {
  const projectRoot = store.getProjectRoot();

  // Read design context from the store (informational — building delegates to
  // the existing shared-component-builder which has its own design token injection)
  const architecture = store.getArchitecture();
  const designSystem = store.getDesignSystem();

  if (architecture) {
    console.log(
      `  [component-library] Architecture loaded: ${architecture.pages.length} pages, ` +
      `${architecture.componentHierarchy.length} hierarchy entries`,
    );
  }
  if (designSystem) {
    console.log(
      `  [component-library] Design system loaded: ${designSystem.aesthetic} aesthetic, ` +
      `${designSystem.colorMode} mode`,
    );
  }

  // Delegate the actual build to the existing shared-component-builder.
  // It handles generation, validation (autoFixImports, validateImports,
  // scanForNullUnsafePatterns, runTscCheck), and fix loops internally.
  console.log("  [component-library] Building shared components...");
  const componentPaths = await buildSharedComponents(brief, projectRoot);

  // Extract TypeScript interfaces from each built component file
  console.log("  [component-library] Extracting component interfaces...");
  const interfaces: ComponentInterface[] = [];

  for (const def of SHARED_COMPONENTS) {
    const filePath = componentPaths[def.name];
    if (!filePath || !fs.existsSync(filePath)) {
      console.warn(`  ⚠ [component-library] Missing file for ${def.name}: ${filePath}`);
      continue;
    }

    const fileContent = fs.readFileSync(filePath, "utf-8");
    const iface = extractComponentInterface(fileContent, filePath, def.name);
    interfaces.push(iface);

    console.log(
      `  ✓ [component-library] ${def.name}: export=${iface.exportName}, ` +
      `${iface.props.length} props, ${iface.dependsOn.length} deps`,
    );
  }

  // Persist to artifact store for downstream agents (page builder, QA)
  store.setComponentInterfaces(interfaces);
  store.setComponentPaths(componentPaths);

  console.log(
    `  [component-library] Done: ${interfaces.length} interfaces extracted, ` +
    `${Object.keys(componentPaths).length} components built`,
  );

  return componentPaths;
}
