# React — Stack Integrations for EOS SaaS

How React 18 composes with the rest of the `/opt/OS/saas` stack.

---

## Vite

Vite is the bundler and dev server. React support comes from
`@vitejs/plugin-react` (Babel) or `@vitejs/plugin-react-swc` (SWC,
faster).

**`vite.config.ts` essentials:**
```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: { port: 5173 },
});
```

**Fast Refresh gotchas:**
- Only *default* or *named* exports at module top level survive HMR.
- Mixing exported components with exported constants in the same file
  can break Fast Refresh. Keep non-component exports in separate files.
- If state is lost on every save, you likely have an anonymous export
  or a re-exported re-wrapper.

**Env vars:** `import.meta.env.VITE_*` (prefix required to expose).

---

## TypeScript (strict)

**`tsconfig.json` must include:**
```json
{
  "compilerOptions": {
    "strict": true,
    "jsx": "react-jsx",
    "moduleResolution": "bundler",
    "noUncheckedIndexedAccess": true,
    "paths": { "@/*": ["./src/*"] }
  }
}
```

Typing rules:
- Props: `interface Props { ... }` or `type Props = { ... }`.
- Children: `children: ReactNode` (not `JSX.Element`).
- Events: `React.ChangeEvent<HTMLInputElement>`, etc. Or use the
  inferred handler from `<input onChange={(e) => ...}>`.
- Refs: `useRef<HTMLDivElement>(null)` — note `null` initial for DOM refs.
- Never `React.FC` — it implies implicit children and is discouraged.
- Discriminated unions for variant props: `type Props = { variant: "a"; ... } | { variant: "b"; ... }`.

---

## Tailwind CSS

Utility-first styling. Co-located in JSX via `className`.

**Composition helper** — `cn()` (clsx + tailwind-merge):
```ts
import clsx from "clsx";
import { twMerge } from "tailwind-merge";
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

Rules:
- Use `cn()` whenever conditionally combining classes.
- Design tokens live in `tailwind.config.ts` under `theme.extend`.
- Use CSS variables + shadcn theme tokens (`bg-background`, `text-foreground`, `border-border`) — never hardcode colors.
- Dark mode is `class`-based: toggle `class="dark"` on `<html>`.

---

## shadcn/ui

shadcn is not a library — it's a **CLI that copies source files** into
`src/components/ui/`. You own the code. Built on Radix primitives +
Tailwind + `cva` (class-variance-authority) for variants.

**Add a component:**
```bash
npx shadcn@latest add button dialog form input select toast
```

**Use:**
```tsx
import { Button } from "@/components/ui/button";
<Button variant="destructive" size="sm">Delete</Button>
```

Rules:
- Never install a second component library alongside shadcn.
- Extend shadcn components via the copied file — don't wrap them in
  yet another component unless adding genuine new behavior.
- Don't re-run `add` on a customized component without review — it'll
  overwrite your changes.

---

## TanStack Query (React Query)

The single source of truth for server state. Install at the root:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const qc = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

export function App() {
  return (
    <QueryClientProvider client={qc}>
      <AppRoutes />
    </QueryClientProvider>
  );
}
```

Patterns:
- **Query keys are hierarchies.** `["leads"]`, `["leads", id]`,
  `["leads", "search", query]`. Invalidate by prefix.
- **Separate read hooks** (`useLeads`, `useLead(id)`) from
  **mutation hooks** (`useCreateLead`, `useUpdateLead`).
- **Invalidate on success** — `qc.invalidateQueries({ queryKey: ["leads"] })`.
- **Optimistic updates** for snappy UIs (see examples.md).
- **Never mix React Query and useEffect fetching** in the same component.
- Use `useSuspenseQuery` when you have Suspense boundaries set up.

---

## Zod

Runtime validation + TypeScript type inference from one schema.

```ts
const schema = z.object({
  email: z.string().email(),
  age: z.number().int().positive(),
});
type Values = z.infer<typeof schema>;
```

Rules:
- Define schemas in `lib/schemas/` and share them between client forms
  and server route validation.
- Prefer `z.infer<typeof schema>` over hand-written types.
- Use `.transform()` for data shape conversion only when unavoidable.
- Error messages via `.min(1, "Required")` inline; localize later if needed.

---

## React Hook Form + zodResolver

Standard form stack. RHF is uncontrolled by default — performs better
than Formik for large forms because it avoids re-rendering siblings on
each keystroke.

```tsx
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

const form = useForm<Values>({
  resolver: zodResolver(schema),
  defaultValues: { email: "", age: 0 },
});
```

Rules:
- Always provide `defaultValues` — avoids uncontrolled→controlled warnings.
- Use shadcn `<Form>` + `<FormField>` wrapper so labels, errors, and
  a11y are handled.
- For async submit, use `form.handleSubmit(async (v) => { ... })` and
  read `form.formState.isSubmitting` for button state.
- Reset on success: `form.reset()`.

---

## Router (Wouter or React Router)

EOS repos use Wouter (tiny) or React Router v6+ (full-featured).
Check the specific repo. Core rules either way:

- URL is state. Don't mirror it into `useState` unless you need
  debouncing.
- Route-level code splitting via `React.lazy()` + Suspense boundary.
- Keep route components thin — compose feature components inside them.

---

## Composition summary

```
Vite            → dev server, bundle, HMR
  React 18      → rendering + component model
    TypeScript  → static types, strict mode
    Tailwind    → styling tokens and utilities
    shadcn/ui   → composable primitives on Radix
    React Query → all server state
    RHF + Zod   → all forms (validation + type inference)
    Router      → URL as state
```

Anything outside this stack is a deliberate exception, not a default.

---

## React 19 Migration Plan for EOS SaaS

**Current state:** React 18.3.1 across all `/opt/OS/saas/*` apps.
**Target state:** React 19.x with Compiler opt-in per-directory.

### Phase 1 — Staging on 18.3 (safe)
- Confirm every `/opt/OS/saas/*` app is on `react@18.3.1` / `react-dom@18.3.1`.
- Enable the `react-hooks/exhaustive-deps` ESLint rule as an error, not a warning.
- Remove every `// eslint-disable-next-line react-hooks/exhaustive-deps`
  suppression. Each one is a latent bug the Compiler will refuse to optimize.
- Replace any remaining `useEffect` data fetches with React Query (we already do this, but audit).

### Phase 2 — Upgrade to React 19
- Bump `react`, `react-dom`, `@types/react`, `@types/react-dom` to 19.x.
- Verify shadcn/ui, Radix primitives, react-hook-form, @tanstack/react-query,
  and Wouter/React Router are on versions that list React 19 in peer deps.
  (Radix and RHF added 19 support in 2025; RQ v5 is compatible.)
- Run the codemod: `npx codemod@latest react/19/migration-recipe`.
- Hand-review the diff for:
  - `forwardRef` → ref-as-prop conversions
  - `useFormState` → `useActionState` (import moves from `react-dom` to `react`)
  - Removed `propTypes` and `defaultProps` on function components
  - Legacy context / string refs (unlikely in our codebase)
- Run the full Vitest suite and Playwright e2e pass.
- Keep React Hook Form for complex forms. Evaluate Actions only for
  brand-new server-bound forms with no client validation complexity.

### Phase 3 — React Compiler opt-in
- Install `babel-plugin-react-compiler` and wire it into the Vite config
  via `@vitejs/plugin-react`'s Babel pass.
- Start with one low-risk directory (e.g. `components/ui/` copy is
  already pure by shadcn's design). Enable the compiler for that path
  only via Babel `overrides`.
- Measure: bundle size delta, Lighthouse scores, React DevTools Profiler
  before/after on the top 3 pages.
- Expand compiler coverage directory by directory. Use the
  `"use no memo"` file directive to opt out any file where the compiler
  trips on a rule violation (and then fix the violation).
- Once 100% opted in, remove all manual `useMemo` / `useCallback` /
  `React.memo` from new code in code review.

### What NOT to do during migration
- Do NOT migrate to Server Components. EOS SaaS is a Vite SPA —
  Server Components require a framework that owns the server (Next.js
  App Router, TanStack Start). Revisit only when EOS needs SSR for
  SEO/marketing surfaces.
- Do NOT replace React Query with `use()` + hand-rolled caches.
  TanStack Query owns the cache and composes with `use()` and
  `useSuspenseQuery` cleanly.
- Do NOT mix `forwardRef` and ref-as-prop components in the same file.
