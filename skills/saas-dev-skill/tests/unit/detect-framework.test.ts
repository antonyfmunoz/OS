import { describe, it, expect } from "vitest";
import { detectFramework } from "../../lib/detect-framework.js";

describe("detectFramework", () => {
  it("identifies react-vite-tailwind-shadcn with full stack", () => {
    const pkg = {
      dependencies: {
        react: "^18.3.1",
        "@radix-ui/react-dialog": "^1.1.2",
        "@radix-ui/react-dropdown-menu": "^2.1.2",
        "@radix-ui/react-select": "^2.1.2",
      },
      devDependencies: {
        vite: "^5.4.15",
        tailwindcss: "^3.4.14",
      },
    };
    const result = detectFramework(pkg);
    expect(result.framework).toBe("react-vite-tailwind-shadcn");
    expect(result.confidence).toBe("HIGH");
    expect(result.detected.react).toBe(true);
    expect(result.detected.vite).toBe(true);
    expect(result.detected.tailwind).toBe(true);
    expect(result.detected.shadcn).toBe(true);
    expect(result.missing).toHaveLength(0);
  });

  it("returns unknown with LOW for empty deps", () => {
    const result = detectFramework({});
    expect(result.framework).toBe("unknown");
    expect(result.confidence).toBe("LOW");
    expect(result.missing).toHaveLength(4);
  });

  it("returns unknown with MEDIUM for partial stack (react + vite only)", () => {
    const pkg = {
      dependencies: { react: "^18.0.0" },
      devDependencies: { vite: "^5.0.0" },
    };
    const result = detectFramework(pkg);
    expect(result.framework).toBe("unknown");
    expect(result.confidence).toBe("MEDIUM");
    expect(result.detected.react).toBe(true);
    expect(result.detected.vite).toBe(true);
    expect(result.detected.tailwind).toBe(false);
    expect(result.detected.shadcn).toBe(false);
    expect(result.missing).toContain("tailwindcss");
  });

  it("detects shadcn via components.json even without Radix packages", () => {
    const pkg = {
      dependencies: { react: "^18.0.0" },
      devDependencies: { vite: "^5.0.0", tailwindcss: "^3.0.0" },
    };
    const result = detectFramework(pkg, true);
    expect(result.framework).toBe("react-vite-tailwind-shadcn");
    expect(result.confidence).toBe("HIGH");
    expect(result.detected.shadcn).toBe(true);
  });
});
