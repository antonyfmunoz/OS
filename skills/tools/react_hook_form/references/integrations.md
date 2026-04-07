# React Hook Form — Integrations (Composition with the EOS Stack)

RHF composes with every layer of `/opt/OS/saas`. This doc is the single
map of how they fit together.

---

## Zod + @hookform/resolvers/zod

The canonical pairing. RHF owns state + submission; Zod owns shape +
validation + messages.

```ts
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

const LoginSchema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(8, "At least 8 characters"),
  remember: z.boolean().default(false),
});

// IMPORTANT: z.input, not z.infer — see "TypeScript" section below
type LoginValues = z.input<typeof LoginSchema>;

const form = useForm<LoginValues>({
  resolver: zodResolver(LoginSchema),
  defaultValues: { email: "", password: "", remember: false },
  mode: "onBlur",
});
```

How it works under the hood:
1. On submit / blur / change (per `mode`), RHF calls
   `zodResolver(Schema)(values, context, options)`.
2. Resolver calls `Schema.safeParseAsync(values)`.
3. On success, returns `{ values: parsed, errors: {} }`.
4. On failure, converts `ZodError` issues into RHF's `FieldErrors`
   shape: `{ field: { type: issue.code, message: issue.message } }`.
5. Shadcn's `<FormMessage>` reads `fieldState.error?.message` and
   renders the Zod message verbatim.

**Rule:** the error messages you write in
`.email("Enter a valid email")` are the ones the user sees. Write
them for the user.

---

## shadcn/ui `<Form>` primitives

shadcn ships seven components in `components/ui/form.tsx`:
`<Form>`, `<FormField>`, `<FormItem>`, `<FormLabel>`, `<FormControl>`,
`<FormDescription>`, `<FormMessage>`. Every one is a thin layer over
RHF.

### What each component actually does

- **`<Form>`** — `FormProvider` from RHF. Provides the `form` context
  to every `<FormField>` below. Usage: `<Form {...form}>`.
- **`<FormField>`** — wraps RHF's `<Controller>`. Provides a React
  Context with the field's name + id so siblings
  (`<FormLabel>`, `<FormMessage>`) can find the field without
  prop-drilling. Usage:
  ```tsx
  <FormField control={form.control} name="email" render={({ field }) => JSX} />
  ```
- **`<FormItem>`** — a `<div>` that generates a stable `useId()` and
  provides it via context. This is what wires `<FormLabel htmlFor>`
  to `<input id>` for ARIA.
- **`<FormLabel>`** — a Radix `<Label>` bound to the field's id.
  Applies `text-destructive` when the field has an error.
- **`<FormControl>`** — a Radix `<Slot>` that injects `id`,
  `aria-describedby`, and `aria-invalid` into its child. This is how
  any `<Input>` inside `<FormControl>` becomes accessible without
  writing ARIA manually.
- **`<FormDescription>`** — a `<p>` whose id is referenced by the
  input's `aria-describedby`. Used for help text.
- **`<FormMessage>`** — reads `fieldState.error?.message` and renders
  it in `text-destructive`. Renders nothing when there's no error.

### Data flow

```
useForm()
  → form.control
    → <Form {...form}>                    (FormProvider)
      → <FormField control name render>   (Controller)
        → render({ field, fieldState })
          → <FormItem>                    (provides useId)
            → <FormLabel />               (reads id from context)
            → <FormControl>               (injects id + aria into child)
              → <Input {...field} />      (field.value, onChange, onBlur, ref, name)
            → <FormMessage />             (reads fieldState.error.message)
```

### The canonical pattern

```tsx
<Form {...form}>
  <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
    <FormField
      control={form.control}
      name="email"
      render={({ field }) => (
        <FormItem>
          <FormLabel>Email</FormLabel>
          <FormControl>
            <Input type="email" {...field} />
          </FormControl>
          <FormDescription>We only use this for account recovery.</FormDescription>
          <FormMessage />
        </FormItem>
      )}
    />
  </form>
</Form>
```

---

## React Query (@tanstack/react-query)

Three integration points: async defaults, mutations, and cache updates.

### 1. Async defaults — use `values`, not `defaultValues`

```tsx
const { data } = useQuery({ queryKey: ["user", id], queryFn: fetchUser });

const form = useForm<UserValues>({
  resolver: zodResolver(UserSchema),
  defaultValues: emptyUser,              // empty shell renders first
  values: data,                           // reactive — syncs on every query update
  resetOptions: { keepDirtyValues: true } // don't clobber in-progress edits
});
```

Why not `useEffect + reset`? `values` is declarative and doesn't
require an effect or a dep array. TkDodo's official recommendation.

### 2. Mutations — submission via `useMutation`

```tsx
const mutation = useMutation({
  mutationFn: async (values: UserValues) => {
    const res = await fetch(`/api/users/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(values),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw Object.assign(new Error(body.message ?? "Save failed"), {
        status: res.status,
        fieldErrors: body.errors,
      });
    }
    return UserSchema.parse(await res.json());
  },
  onSuccess: (saved) => {
    qc.setQueryData(["user", id], saved);
    form.reset(saved); // reset baseline so isDirty = false
  },
  onError: (err: any) => {
    if (err.fieldErrors) {
      for (const [name, message] of Object.entries(err.fieldErrors)) {
        form.setError(name as any, { type: "server", message: message as string });
      }
    } else {
      form.setError("root.server", {
        type: String(err.status ?? 500),
        message: err.message,
      });
    }
  },
});

function onSubmit(values: UserValues) {
  form.clearErrors("root.server"); // critical
  mutation.mutate(values);
}
```

### 3. Cache invalidation

```tsx
onSuccess: (saved) => {
  qc.setQueryData(["user", id], saved);        // update the specific entry
  qc.invalidateQueries({ queryKey: ["users"] }); // refetch list views
  form.reset(saved);
},
```

**Never** try to write form state back into the query cache manually.
The form is the form; the cache is the cache.

---

## React 18 vs React 19 (Actions comparison)

React 19 shipped Server Actions + `useActionState` + `useOptimistic`.
This does NOT obsolete RHF. Here's when to use each.

### Use RHF when:
- You need rich client-side validation (Zod schemas, cross-field rules).
- You have dynamic field arrays (`useFieldArray`).
- You have multi-step wizards with partial validation.
- You need dirty tracking, touched tracking, programmatic focus, or
  field-level error state.
- You're composing with shadcn/ui `<Form>` primitives.
- **Default for EOS.** Almost every form falls here.

### Use React 19 Actions + `useActionState` when:
- You want progressive enhancement (the form works without JS).
- Your form is simple: a handful of fields, no dynamic rows, no
  cross-field validation.
- Validation happens entirely server-side and you're fine with a full
  round-trip per submit.
- You're on Next.js App Router and want the zero-boilerplate Server
  Function path.

### The bridge pattern — RHF + Actions together

When you need BOTH rich client validation AND Server Actions (e.g. Next
App Router + complex form):

```tsx
// From Markus Oberlehner's pattern
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useActionState } from "react";
import { createUserAction } from "@/actions/user"; // "use server" function

type State = {
  values?: Partial<UserValues>;
  errors?: Partial<Record<keyof UserValues, string>>;
  rootError?: string;
};

export function CreateUserForm() {
  const [state, formAction, isPending] = useActionState<State, FormData>(
    createUserAction,
    {}
  );

  const form = useForm<UserValues>({
    resolver: zodResolver(UserSchema),
    defaultValues: state.values ?? { name: "", email: "" },
    values: state.values as any, // re-hydrate on server response
    mode: "onBlur",
  });

  // Inject server errors into RHF
  useEffect(() => {
    if (state.errors) {
      for (const [name, message] of Object.entries(state.errors)) {
        form.setError(name as keyof UserValues, { type: "server", message });
      }
    }
    if (state.rootError) {
      form.setError("root.server", { message: state.rootError });
    }
  }, [state, form]);

  return (
    <Form {...form}>
      {/* NOTE: action={formAction}, NOT onSubmit — this is what makes it
          a React 19 Action */}
      <form action={formAction}>
        <FormField control={form.control} name="email" render={...} />
        <button type="submit" disabled={isPending}>Create</button>
      </form>
    </Form>
  );
}
```

Split of responsibility:
- **RHF** — client-side validation, field errors, dirty tracking.
- **React 19 Action** — server submission, pending state, progressive
  enhancement, server-side validation.
- **`useActionState`** — bridge that carries the server's response
  (errors, values) back into RHF via `setError` / `values`.

Don't migrate existing RHF forms just because React 19 shipped. The
bridge pattern is only worth the complexity for new forms that need
both client richness AND progressive enhancement.

---

## TypeScript (strict) — `z.input` vs `z.infer` vs `z.output`

This trips up every new dev. The rule:

| Type         | When                                           |
|--------------|------------------------------------------------|
| `z.input<S>` | `useForm<T>`, form values, unsubmitted state   |
| `z.infer<S>` | Same as `z.output` — post-parse, post-transform |
| `z.output<S>`| Parsed server values, API request bodies      |

Why the distinction matters:

```ts
const Schema = z.object({
  email: z.string().email(),
  remember: z.boolean().default(false),        // default makes it optional on input
  age: z.coerce.number(),                       // coerce transforms string → number
});

type Input  = z.input<typeof Schema>;
// { email: string; remember?: boolean; age: string | number }

type Output = z.output<typeof Schema>;
// { email: string; remember: boolean; age: number }

// Form state is the INPUT type — before the resolver runs:
const form = useForm<Input>({
  resolver: zodResolver(Schema),
  defaultValues: { email: "", remember: false, age: "" as any },
});

// handleSubmit receives the OUTPUT type (if you set the 3rd generic):
const form2 = useForm<Input, any, Output>({ resolver: zodResolver(Schema) });
form2.handleSubmit((values) => {
  // values is Output here — age is number
});
```

Rules for EOS:
1. **Always `z.input` for `useForm<T>`**. Never `z.infer`.
2. For the submitted values type, use `z.output` or set the third
   `useForm` generic.
3. Schemas live in `src/schemas/`. Export both types:
   ```ts
   export const LeadSchema = z.object({...});
   export type LeadInput = z.input<typeof LeadSchema>;
   export type Lead = z.output<typeof LeadSchema>;
   ```

---

## Vite

RHF has no build-time requirements. It's a runtime library — it works
with any bundler. For Vite specifically:

- No config needed beyond installing `react-hook-form` and
  `@hookform/resolvers`.
- Vite's Fast Refresh plays nicely with `useForm` — the form state
  survives most HMR updates. If the schema changes, you'll see a
  re-mount and lose field values, which is correct.
- Dev-only: install `@hookform/devtools` for a React DevTools panel
  showing the live form state. Add `<DevTool control={form.control} />`
  inside `<Form>` during development.

```tsx
import { DevTool } from "@hookform/devtools";

<Form {...form}>
  <form onSubmit={form.handleSubmit(onSubmit)}>{/* ... */}</form>
  {import.meta.env.DEV && <DevTool control={form.control} />}
</Form>
```

---

## Composition summary (EOS stack map)

```
Zod schema              (src/schemas/)
  ↓ z.input<typeof S>
useForm<T>              (react-hook-form)
  ↓ form.control
<Form> (FormProvider)   (shadcn/ui/form.tsx → react-hook-form)
  ↓ context
<FormField>             (→ Controller)
  ↓ render({ field })
<Input /> or <Select>   (shadcn/ui — spread field into primitive)
  ↓ user interaction
form.handleSubmit(onValid)
  ↓ validated values
useMutation.mutate()    (@tanstack/react-query)
  ↓ server
Express validate(Schema)    ← SAME Zod schema
  ↓ 400 { errors: { field: [msg] } }
mutation.onError
  ↓ form.setError('field', { type:'server', message })
<FormMessage />         (renders the error from Zod or server)
```

One schema. One type system. One source of truth. Every boundary
validated. Every error surfaced in the exact JSX the form already
renders.
