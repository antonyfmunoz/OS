// lib/react-gen/build-status-overlay.ts
// Injects a build progress overlay into the running Vite app during generation.
// Communicates via public/build-status.json which the overlay polls.

import fs from "node:fs";
import path from "node:path";

export interface BuildStatus {
  phase: "shared-components" | "pages";
  total: number;
  completed: string[];
  current: string | null;
  failed: string[];
}

const OVERLAY_COMPONENT = `// AUTO-GENERATED — removed after build completes
import { useState, useEffect } from "react";

interface BuildStatus {
  phase: "shared-components" | "pages";
  total: number;
  completed: string[];
  current: string | null;
  failed: string[];
}

export function BuildStatusOverlay() {
  const [status, setStatus] = useState<BuildStatus | null>(null);

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch("/build-status.json?" + Date.now());
        if (res.ok) {
          setStatus(await res.json());
        } else {
          setStatus(null);
        }
      } catch {
        setStatus(null);
      }
    }, 500);
    return () => clearInterval(interval);
  }, []);

  if (!status) return null;

  const pct = status.total > 0
    ? Math.round((status.completed.length / status.total) * 100)
    : 0;

  return (
    <div style={{
      position: "fixed",
      bottom: 24,
      right: 24,
      width: 320,
      background: "rgba(255,255,255,0.85)",
      backdropFilter: "blur(16px)",
      borderRadius: 12,
      padding: 20,
      boxShadow: "0 8px 32px rgba(106,55,212,0.12)",
      fontFamily: "Inter, sans-serif",
      fontSize: 13,
      color: "#2c2f30",
      zIndex: 99999,
    }}>
      <div style={{ fontWeight: 600, marginBottom: 8 }}>
        Building {status.phase === "shared-components" ? "shared components" : "pages"}...
      </div>
      <div style={{
        height: 6,
        borderRadius: 3,
        background: "#eff1f2",
        marginBottom: 8,
        overflow: "hidden",
      }}>
        <div style={{
          height: "100%",
          width: pct + "%",
          background: "#6a37d4",
          borderRadius: 3,
          transition: "width 0.3s ease",
        }} />
      </div>
      <div style={{ color: "#595c5d" }}>
        {status.current ? \`Generating: \${status.current}\` : \`\${status.completed.length}/\${status.total} complete\`}
      </div>
      {status.failed.length > 0 && (
        <div style={{ color: "#dc2626", marginTop: 4 }}>
          Failed: {status.failed.join(", ")}
        </div>
      )}
    </div>
  );
}
`;

export async function injectBuildOverlay(projectRoot: string): Promise<void> {
  const overlayPath = path.join(projectRoot, "client", "src", "components", "BuildStatusOverlay.tsx");
  const dir = path.dirname(overlayPath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  fs.writeFileSync(overlayPath, OVERLAY_COMPONENT, "utf-8");

  // Inject into App.tsx
  const appTsxPath = path.join(projectRoot, "client", "src", "App.tsx");
  if (fs.existsSync(appTsxPath)) {
    let appContent = fs.readFileSync(appTsxPath, "utf-8");

    // Add import if not present
    if (!appContent.includes("BuildStatusOverlay")) {
      const importLine = 'import { BuildStatusOverlay } from "@/components/BuildStatusOverlay";\n';
      // Insert after the last import
      const lastImportIdx = appContent.lastIndexOf("import ");
      if (lastImportIdx !== -1) {
        const lineEnd = appContent.indexOf("\n", lastImportIdx);
        appContent = appContent.slice(0, lineEnd + 1) + importLine + appContent.slice(lineEnd + 1);
      } else {
        appContent = importLine + appContent;
      }

      // Add component before closing fragment or div
      // Look for the return statement's closing
      const closingPatterns = ["</Router>", "</QueryClientProvider>", "</div>"];
      for (const pattern of closingPatterns) {
        const idx = appContent.lastIndexOf(pattern);
        if (idx !== -1) {
          appContent = appContent.slice(0, idx) + "      <BuildStatusOverlay />\n      " + appContent.slice(idx);
          break;
        }
      }

      fs.writeFileSync(appTsxPath, appContent, "utf-8");
    }
  }

  // Initialize build-status.json
  const statusPath = path.join(projectRoot, "public", "build-status.json");
  const publicDir = path.dirname(statusPath);
  if (!fs.existsSync(publicDir)) {
    fs.mkdirSync(publicDir, { recursive: true });
  }
  const initial: BuildStatus = {
    phase: "shared-components",
    total: 0,
    completed: [],
    current: null,
    failed: [],
  };
  fs.writeFileSync(statusPath, JSON.stringify(initial), "utf-8");
}

export async function updateBuildStatus(
  status: BuildStatus,
  projectRoot: string,
): Promise<void> {
  const statusPath = path.join(projectRoot, "public", "build-status.json");
  fs.writeFileSync(statusPath, JSON.stringify(status), "utf-8");
}

export async function removeBuildOverlay(projectRoot: string): Promise<void> {
  // Remove build-status.json
  const statusPath = path.join(projectRoot, "public", "build-status.json");
  if (fs.existsSync(statusPath)) {
    fs.unlinkSync(statusPath);
  }

  // Remove overlay component
  const overlayPath = path.join(projectRoot, "client", "src", "components", "BuildStatusOverlay.tsx");
  if (fs.existsSync(overlayPath)) {
    fs.unlinkSync(overlayPath);
  }

  // Remove import + usage from App.tsx
  const appTsxPath = path.join(projectRoot, "client", "src", "App.tsx");
  if (fs.existsSync(appTsxPath)) {
    let appContent = fs.readFileSync(appTsxPath, "utf-8");
    appContent = appContent.replace(/import\s*\{?\s*BuildStatusOverlay\s*\}?\s*from\s*["'][^"']+["'];?\n?/g, "");
    appContent = appContent.replace(/\s*<BuildStatusOverlay\s*\/>\s*\n?/g, "\n");
    fs.writeFileSync(appTsxPath, appContent, "utf-8");
  }
}
