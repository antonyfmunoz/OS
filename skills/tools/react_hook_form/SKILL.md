---
name: react_hook_form
description: "Use when building, modifying, or debugging forms in EOS SaaS (/opt/OS/saas) — covers useForm, register vs Controller, zodResolver integration, shadcn <Form> primitives, useFieldArray for dynamic lists, defaultValues/values/reset/watch/setValue, handleSubmit flows, server error injection via setError, and re-render optimization with useWatch/useFormState. Also use when choosing between RHF and React 19 Actions, when forms desync from React Query data, or when diagnosing 'Controller has no defaultValue' / 'field.id overwrite' issues."
allowed-tools: "Read, Write, Edit, Bash, WebFetch, WebSearch"
version: 2.0
source_url: "https://react-hook-form.com"
last_researched: "2026-04-06"
api_version: "7.x"
sdk_version: "react-hook-form@7 (+ @hookform/resolvers@3)"
speed_category: "medium"
trigger: both
effort: high
context: fork
sources:
  - https://react-hook-form.com
  - https://react-hook-form.com/docs/useform
  - https://react-hook-form.com/docs/usecontroller/controller
  - https://react-hook-form.com/docs/usefieldarray
  - https://react-hook-form.com/docs/useform/seterror
  - https://react-hook-form.com/advanced-usage
  - https://react-hook-form.com/faqs
  - https://ui.shadcn.com/docs/components/form
  - https://github.com/react-hook-form/resolvers
  - https://github.com/orgs/react-hook-form/discussions/11832
  - https://tkdodo.eu/blog/react-query-and-forms
  - https://markus.oberlehner.net/blog/using-react-hook-form-with-react-19-use-action-state-and-next-js-15-app-router
  - https://blog.logrocket.com/whats-new-in-react-hook-form-v7/
---

# Tool: React Hook Form

React Hook Form (RHF) is the form state layer for every EOS SaaS surface.
It is the engine underneath shadcn/ui's `<Form>` primitives, the partner to
Zod for client-side validation, and the bridge to React Query for submission
and server-derived defaults. If a component in `/opt/OS/saas` accepts user
input and that input is going somewhere — RHF is how it gets there.

This skill exists so the Developer Agent writes forms the way Bill Luo
(RHF's creator) intended: uncontrolled-first, ref-based registration,
subscription-scoped re-renders, and the schema (Zod) as the single source
of truth for shape + validation + error messages.

## What This Tool Does

RHF is a ~9kb gzipped, zero-dependency React library for form state and
validation. The core insight from its creator:

> The best way to handle form state in React is to avoid putting it in
> React state at all.

Instead of controlled inputs (`value` + `onChange` → `setState` on every
keystroke), RHF attaches refs to native inputs via `register()` and reads
values from the DOM only when needed — on submit, on blur, on validation.
This collapses form typing from O(keystrokes × tree size) re-renders to
effectively zero re-renders of the parent tree.

Core surface:
- **`useForm<T>(options)`** — creates the form instance. Returns `register`,
  `handleSubmit`, `control`, `formState`, `watch`, `setValue`, `getValues`,
  `reset`, `resetField`, `setError`, `clearErrors`, `trigger`, `setFocus`,
  `getFieldState`, `unregister`.
- **`register(name, options?)`** — ref-based registration for native inputs.
  Spread into an `<input>` / `<select>` / `<textarea>`. This is the hot path.
- **`<Controller>` / `useController`** — controlled-component bridge for
  inputs that don't expose a ref (MUI, Radix Select, custom date pickers,
  react-select). Isolates re-renders to the Controller's own subtree.
- **`handleSubmit(onValid, onInvalid?)`** — runs the resolver, gathers
  values, and invokes your callback with a fully typed, validated object.
- **`useFieldArray({ control, name })`** — dynamic lists: append, prepend,
  insert, swap, move, update, replace, remove. Each field gets a stable
  `field.id` — always use it as the React `key`.
- **`useWatch` / `useFormState`** — subscription hooks that isolate
  re-renders to a specific subtree. Use these instead of `watch()` from
  `useForm` anywhere you care about performance.
- **`zodResolver`** — from `@hookform/resolvers/zod`. Adapts a Zod schema
  to RHF's resolver interface; async refines work transparently.

## EOS Integration

**Where RHF lives:**
- `/opt/OS/saas/*/src/components/ui/form.tsx` — shadcn `<Form>` primitives.
  These are a thin layer over RHF's `<FormProvider>` + `<Controller>`.
- `/opt/OS/saas/*/src/components/**/*-form.tsx` — every feature form
  (signup, login, lead intake, settings, billing).
- `/opt/OS/saas/*/src/schemas/` — Zod schemas shared client/server. The
  `useForm` type parameter always comes from `z.input<typeof Schema>`.
- `/opt/OS/saas/*/src/hooks/` — occasionally, custom form hooks that
  wrap `useForm` + a mutation for reuse across pages.

**Stack partners:**
- **Zod + @hookform/resolvers/zod** — validation. See `skills/tools/zod`.
- **shadcn/ui `<Form>`** — JSX primitives. See `skills/tools/shadcn_ui`.
- **@tanstack/react-query** — `mutation.onSuccess → form.reset(data)`,
  `mutation.onError → setError('root.server', ...)`. For async
  defaults, use the `values` prop, not `defaultValues`. See below.
- **React 18 + TypeScript strict** — every `useForm` is typed with
  `z.input<typeof Schema>`, not a hand-written interface.

**The canonical EOS form pattern:**
```
Zod schema in src/schemas/ → useForm<z.input<typeof S>>({
  resolver: zodResolver(S), defaultValues: {...}
}) → shadcn <Form> + <FormField> primitives → handleSubmit
→ React Query mutation → onSuccess: form.reset() /
onError: form.setError('root.server', { message })
```

Never: hand-roll `<Controller>` wrappers when shadcn already gives you
`<FormField>`. Never: duplicate validation messages between Zod and JSX —
let `<FormMessage />` render whatever Zod returned.

## Authentication

N/A — RHF is a client-side library. No keys, no accounts, no tokens.

The version pinning rules that replace auth for a library:
- `react-hook-form@^7.54` — latest 7.x as of April 2026. v8 is in beta
  with TypeScript perf improvements; do NOT adopt in EOS yet.
- `@hookform/resolvers@^3.9` — required for Zod 3.23+ and Zod 4.
- Must match `react@18.3` (current EOS stack). RHF v7 supports React 16.8+
  through React 19.

Check installed versions:
```bash
cd /opt/OS/saas/<app> && npm ls react-hook-form @hookform/resolvers
```

## Quick Reference

### 1. Login form — shadcn + Zod + RHF (the canonical pattern)

```tsx
// src/schemas/auth.ts
import { z } from "zod";
export const LoginSchema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(8, "At least 8 characters"),
  remember: z.boolean().default(false),
});

// src/components/login-form.tsx
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { z } from "zod";
import { LoginSchema } from "@/schemas/auth";
import {
  Form, FormField, FormItem, FormLabel,
  FormControl, FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";

type LoginValues = z.input<typeof LoginSchema>;

export function LoginForm() {
  const form = useForm<LoginValues>({
    resolver: zodResolver(LoginSchema),
    defaultValues: { email: "", password: "", remember: false },
    mode: "onBlur",
  });

  const mutation = useMutation({
    mutationFn: async (values: LoginValues) => {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw Object.assign(new Error(body.message ?? "Login failed"), {
          status: res.status,
          fieldErrors: body.fieldErrors as Record<string, string> | undefined,
        });
      }
      return res.json() as Promise<{ token: string }>;
    },
    onSuccess: () => form.reset(),
    onError: (err: any) => {
      if (err.fieldErrors) {
        for (const [name, message] of Object.entries(err.fieldErrors)) {
          form.setError(name as keyof LoginValues, { type: "server", message: message as string });
        }
      } else {
        form.setError("root.server", { type: String(err.status ?? 500), message: err.message });
      }
    },
  });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit((v) => mutation.mutate(v))} className="space-y-4">
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl><Input type="email" autoComplete="email" {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Password</FormLabel>
              <FormControl><Input type="password" autoComplete="current-password" {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="remember"
          render={({ field }) => (
            <FormItem className="flex items-center gap-2">
              <FormControl>
                <Checkbox checked={field.value} onCheckedChange={field.onChange} />
              </FormControl>
              <FormLabel className="!mt-0">Remember me</FormLabel>
            </FormItem>
          )}
        />
        {form.formState.errors.root?.server && (
          <p className="text-sm text-destructive">
            {form.formState.errors.root.server.message}
          </p>
        )}
        <Button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "Signing in..." : "Sign in"}
        </Button>
      </form>
    </Form>
  );
}
```

### 2. Dynamic list — useFieldArray

```tsx
const { control, register, handleSubmit } = useForm<{ leads: { name: string; email: string }[] }>({
  defaultValues: { leads: [{ name: "", email: "" }] },
});
const { fields, append, remove } = useFieldArray({ control, name: "leads" });

return (
  <form onSubmit={handleSubmit(console.log)}>
    {fields.map((field, index) => (
      // IMPORTANT: field.id, NEVER index
      <div key={field.id} className="flex gap-2">
        <Input {...register(`leads.${index}.name` as const)} placeholder="Name" />
        <Input {...register(`leads.${index}.email` as const)} placeholder="Email" />
        <Button type="button" variant="ghost" onClick={() => remove(index)}>×</Button>
      </div>
    ))}
    <Button type="button" onClick={() => append({ name: "", email: "" })}>
      Add lead
    </Button>
  </form>
);
```

### 3. Async defaults from React Query — use `values`, NOT `defaultValues`

```tsx
const { data } = useQuery({ queryKey: ["user", id], queryFn: fetchUser });

const form = useForm<UserFormValues>({
  resolver: zodResolver(UserSchema),
  defaultValues: { name: "", email: "", bio: "" }, // empty shell for SSR / first render
  values: data,                                     // reacts to query updates automatically
  resetOptions: { keepDirtyValues: true },          // don't clobber user edits on refetch
});
```

## Conceptual Model

Think of RHF as three layers stacked on top of native browser forms:

1. **Ref layer (`register`).** Inputs are uncontrolled. RHF attaches a ref
   to each registered input and reads `input.value` directly from the DOM
   when it needs it. Typing into a registered input causes **zero**
   re-renders of the form component. This is the entire performance story.

2. **Subscription layer (`watch`, `useWatch`, `formState`, `useFormState`).**
   When you DO need to react to a field's value (enable a button, show a
   conditional subtree), you subscribe. `formState` is a Proxy — it only
   triggers re-renders for the specific keys you read (`isDirty`,
   `isValid`, `errors`). `useWatch` lets you subscribe from a child
   component so only that child re-renders, not the whole form.

3. **Controller layer (`<Controller>`).** For inputs that don't expose a
   ref (Radix Select, MUI TextField, react-select, custom date pickers),
   RHF falls back to controlled mode via `<Controller>`. Each Controller
   has its **own re-render scope** — typing in a Controller-wrapped field
   re-renders only that field, not the form. This is how shadcn's
   `<FormField>` works under the hood: it's a Controller wired to
   `form.control` plus ARIA plumbing.

The mental rule: **native HTML input → `register`. Third-party controlled
input → `Controller` (or `<FormField>`)**. Never wrap a controlled input
with `register` (it won't know how to read the value), and never wrap a
native input with `<Controller>` (you give up the whole performance win).

The second rule: **`defaultValues` is a one-shot initializer**. It's
cached at mount. If your data arrives later, use `values` (reactive) or
`reset(data)` (imperative). If you forget this, your form will silently
render empty while your data sits right there in React Query's cache.

## Gotchas

- **`useFieldArray` silently overwrites your `id` field.** If your row
  data already has an `id` (from the database), RHF replaces it with its
  own internal UUID. Either rename your DB field (`dbId`) or pass
  `keyName: "rhfId"` to `useFieldArray`. Always use `field.id` as the
  React `key` — never the index, or reorder/remove will break state.

- **`defaultValues` does NOT react to updates.** `useForm({ defaultValues:
  data })` reads `data` exactly once at mount. If `data` arrives later
  from React Query, the form stays empty. Use the `values` prop instead —
  it's reactive — or call `form.reset(data)` in a `useEffect`. Combine
  `values` with `resetOptions: { keepDirtyValues: true }` so a background
  refetch doesn't clobber the user's in-progress edits.

- **`Controller` requires `defaultValues` for every controlled field.**
  Without it, you get "A component is changing an uncontrolled input to
  controlled" warnings. Always pass a complete `defaultValues` object to
  `useForm` — every field listed, no `undefined`. `""` for strings,
  `false` for booleans, `[]` for arrays, `null` for optional numbers.

- **`mode: "onChange"` + async Zod refine = request storm.** Async
  refines fire on every keystroke. Use `mode: "onBlur"` (or the default
  `"onSubmit"`) for schemas that hit the network. If you need live
  validation on one specific field, call `form.trigger("fieldName")` on
  blur instead of flipping the whole form to `onChange`.

- **`setError("root.server", ...)` persists across submissions.** Root
  errors are not tied to a field, so the next `handleSubmit` won't clear
  them automatically. You must call `form.clearErrors("root.server")` at
  the top of your submit handler, or accept that the server error sticks
  until you manually clear it.

- **Wrapping a controlled input with `register()` fails silently.**
  `<Select {...register("role")} />` on a Radix/MUI Select does nothing —
  they don't forward refs to a DOM input. You'll see the form submit
  without that field. Always use `<FormField>` / `<Controller>` for
  anything that isn't a raw `<input>` / `<select>` / `<textarea>`.

- **`watch()` from `useForm` re-renders the whole form on every change.**
  If you only care about one field in a child component, use `useWatch({
  control, name: "fieldName" })` — it isolates the re-render to the
  subscribing component. This is the single biggest perf mistake in
  large forms.

- **`react-hook-form` + React 19 Actions is NOT a drop-in swap.** RHF
  still owns client-side validation, dirty state, and field arrays.
  React 19 Actions own pending state and server-side validation via
  `useActionState`. The published pattern is: keep RHF for the form
  state, pass `form.handleSubmit(action)` through a wrapper, and feed
  `useActionState`'s returned errors back via `form.setError`. Do not
  migrate existing RHF forms to raw Actions just because React 19 shipped.

## References

- `references/best_practices.md` — full 19-section creator-level protocol
- `references/examples.md` — EOS-aligned patterns (login, field array,
  async defaults, wizard, dependent fields, Controller + date picker,
  server error injection)
- `references/anti_patterns.md` — real failure modes and fixes
- `references/integrations.md` — Zod, shadcn, React Query, React 18/19, TS

## Sources (live-fetched 2026-04-06)

- https://react-hook-form.com — official site (Bill Luo / bluebill1049)
- https://react-hook-form.com/docs/useform — useForm options + returns
- https://react-hook-form.com/docs/usecontroller/controller — Controller API
- https://react-hook-form.com/docs/usefieldarray — useFieldArray API
- https://react-hook-form.com/docs/useform/seterror — setError + root errors
- https://react-hook-form.com/advanced-usage — wizard, async defaults
- https://github.com/react-hook-form/resolvers — zodResolver
- https://ui.shadcn.com/docs/components/form — shadcn Form over RHF
- https://github.com/orgs/react-hook-form/discussions/11832 — React 19 thread
- https://tkdodo.eu/blog/react-query-and-forms — TkDodo forms + RQ pattern
- https://markus.oberlehner.net/blog/using-react-hook-form-with-react-19-use-action-state-and-next-js-15-app-router — RHF + useActionState bridge
- https://blog.logrocket.com/whats-new-in-react-hook-form-v7/ — v7 subscription model
