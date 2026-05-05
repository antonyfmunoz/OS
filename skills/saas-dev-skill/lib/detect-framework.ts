export interface FrameworkDetectionResult {
  framework: "react-vite-tailwind-shadcn" | "unknown";
  detected: {
    react: boolean;
    vite: boolean;
    tailwind: boolean;
    shadcn: boolean;
  };
  confidence: "HIGH" | "MEDIUM" | "LOW";
  /** Components that are missing from a full react-vite-tailwind-shadcn stack */
  missing: string[];
}

/**
 * Detects the frontend framework stack from parsed package.json content.
 * Pure function — no I/O, no file reads. Caller reads package.json and passes parsed object.
 *
 * @param pkg - Parsed package.json with dependencies and devDependencies
 * @param hasComponentsJson - Whether components.json exists in repo root (shadcn/ui marker file).
 *   Pass `true` if file exists, `false` or omit if not. Caller checks file existence.
 */
export function detectFramework(
  pkg: {
    dependencies?: Record<string, string>;
    devDependencies?: Record<string, string>;
  },
  hasComponentsJson: boolean = false
): FrameworkDetectionResult {
  const allDeps = { ...pkg.dependencies, ...pkg.devDependencies };

  const react = "react" in allDeps;
  const vite = "vite" in allDeps;
  const tailwind = "tailwindcss" in allDeps;

  // shadcn detection: components.json is definitive; 3+ Radix packages is heuristic fallback
  const radixKeys = Object.keys(allDeps).filter((k) =>
    k.startsWith("@radix-ui/react-")
  );
  const shadcn = hasComponentsJson || radixKeys.length >= 3;

  const detected = { react, vite, tailwind, shadcn };

  // Track what's missing for MEDIUM confidence results (review suggestion: Gemini)
  const missing: string[] = [];
  if (!react) missing.push("react");
  if (!vite) missing.push("vite");
  if (!tailwind) missing.push("tailwindcss");
  if (!shadcn) missing.push("shadcn/ui (@radix-ui packages or components.json)");

  const score = [react, vite, tailwind, shadcn].filter(Boolean).length;
  const framework: FrameworkDetectionResult["framework"] =
    score === 4 ? "react-vite-tailwind-shadcn" : "unknown";
  const confidence: FrameworkDetectionResult["confidence"] =
    score === 4 ? "HIGH" : score >= 2 ? "MEDIUM" : "LOW";

  return { framework, detected, confidence, missing };
}
