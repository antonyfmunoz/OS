# Vitest — Runnable Examples

All snippets are real, copy-pasteable TypeScript/React. Tested against
vitest@2.1.9, @testing-library/react@16.1.0, msw@2.7.0.

## 1. vitest.config.ts (React + jsdom + setup file)

```ts
// vitest.config.ts
import { defineConfig, mergeConfig } from "vitest/config";
import viteConfig from "./vite.config";

export default mergeConfig(viteConfig, defineConfig({
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: false,
    restoreMocks: true,
    clearMocks: true,
    testTimeout: 5000,
    coverage: {
      provider: "v8",
      reporter: ["text", "html", "lcov"],
      exclude: ["**/*.config.*", "**/*.d.ts", "src/main.tsx", "src/test/**"],
      thresholds: { lines: 80, functions: 80, branches: 70, statements: 80 },
    },
  },
}));
```

## 2. src/test/setup.ts — jest-dom + Radix stubs + MSW

```ts
import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll, vi } from "vitest";
import { cleanup } from "@testing-library/react";
import { server } from "@/mocks/server";

// Radix UI / jsdom stubs — required for Select, Dialog, Popover, DropdownMenu
beforeAll(() => {
  Element.prototype.hasPointerCapture = vi.fn(() => false) as never;
  Element.prototype.releasePointerCapture = vi.fn() as never;
  Element.prototype.scrollIntoView = vi.fn() as never;

  window.ResizeObserver = class {
    observe() {} unobserve() {} disconnect() {}
  } as never;

  window.IntersectionObserver = class {
    root = null; rootMargin = ""; thresholds = [];
    observe() {} unobserve() {} disconnect() {} takeRecords() { return []; }
  } as never;

  // MSW
  server.listen({ onUnhandledRequest: "error" });
});

afterEach(() => {
  cleanup();
  server.resetHandlers();
});

afterAll(() => server.close());
```

## 3. src/test/test-utils.tsx — custom render with all providers

```tsx
import { ReactElement } from "react";
import { render, RenderOptions } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TooltipProvider } from "@/components/ui/tooltip";

export function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: Infinity, staleTime: Infinity },
      mutations: { retry: false },
    },
    // silence error console noise from intentional failure tests
    logger: { log: () => {}, warn: () => {}, error: () => {} } as never,
  });
}

export function renderWithProviders(ui: ReactElement, options?: RenderOptions) {
  const qc = makeQueryClient();
  return {
    qc,
    ...render(
      <QueryClientProvider client={qc}>
        <TooltipProvider>{ui}</TooltipProvider>
      </QueryClientProvider>,
      options,
    ),
  };
}
```

## 4. Component test — userEvent + getByRole

```tsx
// src/components/Counter.test.tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Counter } from "./Counter";

describe("Counter", () => {
  it("increments on click", async () => {
    const user = userEvent.setup();
    render(<Counter initial={0} />);
    const btn = screen.getByRole("button", { name: /increment/i });
    await user.click(btn);
    await user.click(btn);
    expect(screen.getByRole("status")).toHaveTextContent("2");
  });
});
```

## 5. React Hook Form + Zod form test

```tsx
// src/features/leads/LeadForm.test.tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LeadForm } from "./LeadForm";

describe("LeadForm", () => {
  it("shows validation errors for empty submit", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<LeadForm onSubmit={onSubmit} />);

    await user.click(screen.getByRole("button", { name: /create lead/i }));

    expect(await screen.findByText(/name is required/i)).toBeInTheDocument();
    expect(screen.getByText(/valid email required/i)).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("submits valid input", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<LeadForm onSubmit={onSubmit} />);

    await user.type(screen.getByLabelText(/name/i), "Antony Munoz");
    await user.type(screen.getByLabelText(/email/i), "antony@lyfe.institute");
    await user.click(screen.getByRole("button", { name: /create lead/i }));

    await vi.waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({
        name: "Antony Munoz",
        email: "antony@lyfe.institute",
      });
    });
  });
});
```

## 6. React Query test — fresh QueryClient per test

```tsx
// src/features/leads/LeadList.test.tsx
import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "@/mocks/server";
import { renderWithProviders } from "@/test/test-utils";
import { LeadList } from "./LeadList";

describe("LeadList", () => {
  it("renders fetched leads", async () => {
    server.use(
      http.get("/api/leads", () =>
        HttpResponse.json([{ id: 1, name: "Mock Lead" }, { id: 2, name: "Other" }]),
      ),
    );

    renderWithProviders(<LeadList />);
    expect(await screen.findByText("Mock Lead")).toBeInTheDocument();
    expect(screen.getByText("Other")).toBeInTheDocument();
  });

  it("shows error toast on failure", async () => {
    server.use(http.get("/api/leads", () => new HttpResponse(null, { status: 500 })));
    renderWithProviders(<LeadList />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/failed to load/i);
  });
});
```

## 7. MSW v2 setup

```ts
// src/mocks/handlers.ts
import { http, HttpResponse } from "msw";

export const handlers = [
  http.get("/api/leads", () => HttpResponse.json([{ id: 1, name: "Default" }])),
  http.post("/api/leads", async ({ request }) => {
    const body = (await request.json()) as { name: string };
    return HttpResponse.json({ id: 99, ...body }, { status: 201 });
  }),
  http.delete("/api/leads/:id", ({ params }) =>
    HttpResponse.json({ deleted: params.id }),
  ),
];
```

```ts
// src/mocks/server.ts
import { setupServer } from "msw/node";
import { handlers } from "./handlers";

export const server = setupServer(...handlers);
```

## 8. useMutation success/error toast assertion

```tsx
// src/features/leads/CreateLead.test.tsx
import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "@/mocks/server";
import { renderWithProviders } from "@/test/test-utils";
import { CreateLead } from "./CreateLead";

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn(), promise: vi.fn() },
}));

import { toast } from "sonner";

describe("CreateLead mutation", () => {
  it("fires success toast on 201", async () => {
    const user = userEvent.setup();
    renderWithProviders(<CreateLead />);
    await user.type(screen.getByLabelText(/name/i), "Antony");
    await user.click(screen.getByRole("button", { name: /create/i }));
    await vi.waitFor(() => expect(toast.success).toHaveBeenCalledWith("Lead created"));
  });

  it("fires error toast on 500", async () => {
    server.use(http.post("/api/leads", () => new HttpResponse(null, { status: 500 })));
    const user = userEvent.setup();
    renderWithProviders(<CreateLead />);
    await user.type(screen.getByLabelText(/name/i), "X");
    await user.click(screen.getByRole("button", { name: /create/i }));
    await vi.waitFor(() => expect(toast.error).toHaveBeenCalled());
  });
});
```

## 9. Async data loading with findBy*

```tsx
it("loads async data", async () => {
  renderWithProviders(<Dashboard />);
  // findBy* polls until found OR times out — built-in waitFor
  expect(await screen.findByText(/welcome, antony/i)).toBeInTheDocument();
  // For multiple async appearances:
  const items = await screen.findAllByRole("listitem");
  expect(items).toHaveLength(3);
});
```

## 10. Fake timers — debounce test

```ts
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { debounce } from "@/lib/debounce";

describe("debounce", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("collapses rapid calls", async () => {
    const fn = vi.fn();
    const debounced = debounce(fn, 200);
    debounced("a"); debounced("b"); debounced("c");
    expect(fn).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(200);
    expect(fn).toHaveBeenCalledTimes(1);
    expect(fn).toHaveBeenCalledWith("c");
  });
});
```

## 11. vi.mock with hoisted ref

```ts
const { mockTrack } = vi.hoisted(() => ({ mockTrack: vi.fn() }));

vi.mock("@/lib/analytics", () => ({
  track: mockTrack,
  identify: vi.fn(),
}));

import { logSignup } from "@/features/auth/logSignup";

it("tracks signup", () => {
  logSignup({ id: "u1" });
  expect(mockTrack).toHaveBeenCalledWith("signup", { userId: "u1" });
});
```

## 12. test.each table

```ts
import { describe, it, expect } from "vitest";
import { slugify } from "@/lib/slug";

describe("slugify", () => {
  it.each([
    ["Hello World", "hello-world"],
    ["Foo  Bar  Baz", "foo-bar-baz"],
    ["  Trim Me  ", "trim-me"],
    ["UPPER", "upper"],
    ["with-dash", "with-dash"],
    ["café", "cafe"],
  ])("slugify(%s) === %s", (input, expected) => {
    expect(slugify(input)).toBe(expected);
  });
});
```

## 13. In-source testing

```ts
// src/lib/math.ts
export function add(a: number, b: number) {
  return a + b;
}

if (import.meta.vitest) {
  const { it, expect } = import.meta.vitest;
  it("adds", () => {
    expect(add(2, 3)).toBe(5);
  });
}
```

```ts
// vitest.config.ts must include:
test: { includeSource: ["src/**/*.{js,ts}"] },
// vite.config.ts (production) must include:
define: { "import.meta.vitest": "undefined" },
```

## 14. Snapshot test (use sparingly)

```tsx
// Acceptable: stable, prop-driven, presentational
import { render } from "@testing-library/react";
import { Badge } from "./Badge";

it("matches inline snapshot", () => {
  const { container } = render(<Badge variant="success">OK</Badge>);
  expect(container.firstChild).toMatchInlineSnapshot(`
    <span class="badge badge-success">
      OK
    </span>
  `);
});
// PREFER: expect(screen.getByText("OK")).toHaveClass("badge-success");
// behavior tests survive refactors that snapshots don't.
```

## 15. Coverage with v8 + thresholds

```bash
# package.json
"scripts": {
  "test": "vitest",
  "test:run": "vitest run",
  "test:coverage": "vitest run --coverage",
  "test:ui": "vitest --ui"
}
```

```ts
// vitest.config.ts → test.coverage
coverage: {
  provider: "v8",
  reporter: ["text", "json-summary", "html", "lcov"],
  reportsDirectory: "./coverage",
  include: ["src/**/*.{ts,tsx}"],
  exclude: [
    "**/*.config.*", "**/*.d.ts", "src/main.tsx",
    "src/test/**", "src/mocks/**", "**/*.stories.tsx",
  ],
  thresholds: {
    lines: 80, functions: 80, branches: 70, statements: 80,
    // Per-file thresholds (Vitest 2.1+):
    perFile: true,
  },
}
```

## 16. Workspace projects (multi-config)

```ts
// vitest.config.ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    projects: [
      {
        test: {
          name: "unit",
          environment: "jsdom",
          include: ["src/**/*.test.{ts,tsx}"],
          setupFiles: ["./src/test/setup.ts"],
        },
      },
      {
        test: {
          name: "node",
          environment: "node",
          include: ["src/server/**/*.test.ts"],
        },
      },
      {
        test: {
          name: "browser",
          browser: {
            enabled: true,
            provider: "playwright",
            instances: [{ browser: "chromium" }],
          },
          include: ["src/**/*.browser.test.tsx"],
        },
      },
    ],
  },
});
```

Run only one: `vitest --project=unit`.
