# React Hook Form — Creator-Level Best Practices

Protocol version 1.0 — 19 sections. Covers react-hook-form@7.x +
@hookform/resolvers@3.x as used in `/opt/OS/saas`. Last researched
2026-04-06.

---

# Tier 1 — Technical Mastery

## 1. Authentication

N/A. RHF is a client-side library with no service, no API key, and no
account. The "auth equivalent" for a library is **version pinning**:

- `react-hook-form@^7.54.x` — current stable series (April 2026).
- `@hookform/resolvers@^3.9.x` — required for `zodResolver` with Zod
  3.23+ / Zod 4.
- Must match the React major in use (`react@18.3` in EOS today).
- RHF v8 is in beta (TypeScript perf + composable lens operations for
  deeply nested schemas). Do NOT adopt v8 in EOS until lockstep with
  shadcn/ui and @hookform/resolvers ship a confirmed-compatible release.

Check the install:

```bash
cd /opt/OS/saas/<app>
npm ls react-hook-form @hookform/resolvers react react-dom
```

If `npm ls` shows mismatched peer versions (e.g. two copies of
`react-hook-form`), a `<FormProvider>` from one copy cannot be consumed
by `useFormContext` from the other — `form` will appear `undefined`
inside every `<FormField>`. Hoist to a single copy in the workspace.

---

## 2. Core Operations with Exact Signatures

### `useForm<TFieldValues>(options?)`

```ts
useForm<TFieldValues extends FieldValues = FieldValues, TContext = any, TTransformedValues = TFieldValues>(
  props?: {
    mode?: "onSubmit" | "onBlur" | "onChange" | "onTouched" | "all";   // default: "onSubmit"
    reValidateMode?: "onChange" | "onBlur" | "onSubmit";                // default: "onChange"
    defaultValues?: DefaultValues<TFieldValues> | (() => Promise<DefaultValues<TFieldValues>>);
    values?: TFieldValues;                                              // reactive — replaces defaultValues on change
    errors?: FieldErrors<TFieldValues>;                                 // reactive errors from server
    resetOptions?: KeepStateOptions;                                    // { keepDirtyValues, keepErrors, ... }
    resolver?: Resolver<TFieldValues, TContext, TTransformedValues>;    // zodResolver, yupResolver, etc.
    context?: TContext;                                                 // passed to resolver
    criteriaMode?: "firstError" | "all";                                // default: "firstError"
    shouldFocusError?: boolean;                                         // default: true — focus first invalid field on submit
    delayError?: number;                                                // debounce error display in ms
    shouldUnregister?: boolean;                                         // default: false — unmount should remove field state
    shouldUseNativeValidation?: boolean;                                // default: false
    progressive?: boolean;                                              // for progressive-enhancement SSR forms
    disabled?: boolean;                                                 // disables the entire form
  }
): UseFormReturn<TFieldValues, TContext, TTransformedValues>
```

Returned methods:

```ts
register: (name, options?: RegisterOptions) => {
  onChange, onBlur, ref, name                           // spread onto an input
};

unregister: (name | name[], options?) => void;

handleSubmit: (
  onValid: SubmitHandler<T>,
  onInvalid?: SubmitErrorHandler<T>
) => (e?: BaseSyntheticEvent) => Promise<void>;

watch: {
  (): T;                                                // whole form — causes parent re-render on any change
  (name: Path<T>): unknown;                             // one field
  (name: Path<T>[]): unknown[];                         // array of fields
  (callback: (values, { name, type }) => void): Subscription;
};

setValue: (name, value, options?: {
  shouldValidate?: boolean;
  shouldDirty?: boolean;
  shouldTouch?: boolean;
}) => void;

getValues: {
  (): T;
  (name: Path<T>): unknown;
  (names: Path<T>[]): unknown[];
};

getFieldState: (name, formState?) => {
  invalid: boolean;
  isDirty: boolean;
  isTouched: boolean;
  error?: FieldError;
};

reset: (
  values?: Partial<T> | ((previous: T) => T),
  keepStateOptions?: KeepStateOptions
) => void;

resetField: (name, options?: { keepDirty, keepTouched, keepError, defaultValue }) => void;

setError: (name | "root" | `root.${string}`, error: { type, message, types? }, options?: { shouldFocus?: boolean }) => void;

clearErrors: (name?: Path<T> | Path<T>[] | "root" | `root.${string}`) => void;

trigger: (name?: Path<T> | Path<T>[], options?: { shouldFocus?: boolean }) => Promise<boolean>;

setFocus: (name, options?: { shouldSelect?: boolean }) => void;

formState: {
  isDirty: boolean;
  dirtyFields: Partial<Record<keyof T, boolean>>;
  touchedFields: Partial<Record<keyof T, boolean>>;
  defaultValues: Readonly<DeepPartial<T>> | undefined;
  isSubmitted: boolean;
  isSubmitSuccessful: boolean;
  isSubmitting: boolean;
  isLoading: boolean;                                   // while async defaultValues resolve
  submitCount: number;
  isValid: boolean;
  isValidating: boolean;
  errors: FieldErrors<T>;
  disabled: boolean;
};

control: Control<T>;                                    // passed to <Controller> / useFieldArray
```

### `<Controller>` / `useController`

```ts
<Controller
  name="fieldName"
  control={form.control}
  defaultValue={...}                                    // only if not in useForm defaultValues
  rules={...}                                           // RHF native rules, skip if using resolver
  shouldUnregister={false}
  disabled={false}
  render={({ field, fieldState, formState }) => JSX}
/>
```

`field` = `{ onChange, onBlur, value, disabled, name, ref }`.
`fieldState` = `{ invalid, isTouched, isDirty, isValidating, error }`.

### `useFieldArray`

```ts
const {
  fields,                                               // { id: string, ...values }[]
  append,                                               // (value | value[], options?) => void
  prepend,                                              // (value | value[], options?) => void
  insert,                                               // (index, value | value[], options?) => void
  swap,                                                 // (from, to) => void
  move,                                                 // (from, to) => void
  update,                                               // (index, value) => void
  replace,                                              // (value[]) => void
  remove,                                               // (index?: number | number[]) => void
} = useFieldArray({
  control,
  name: "items",
  keyName: "id",                                        // default — RHF will OVERWRITE existing id fields
  rules: {},
  shouldUnregister: false,
});
```

### `zodResolver`

```ts
import { zodResolver } from "@hookform/resolvers/zod";

zodResolver(
  schema: ZodSchema,
  schemaOptions?: Partial<z.ParseParams>,
  resolverOptions?: { mode?: "async" | "sync"; raw?: boolean }
): Resolver<z.input<typeof schema>>
```

Default `mode` is `"async"` — supports `.refine(async ...)` transparently.
Use `raw: true` to bypass Zod's parse and hand the raw values through
(rare — use when you need to let Zod transform but keep the raw inputs
in the form state).

---

## 3. Pagination Patterns

N/A in the API sense. The RHF equivalent is the **multi-step wizard**
pattern — pagination across form steps rather than across API pages:

```tsx
// Single form, one schema per step, trigger() to validate before advancing.
const fullSchema = z.object({ ...step1Schema.shape, ...step2Schema.shape });
type Values = z.input<typeof fullSchema>;

const form = useForm<Values>({ resolver: zodResolver(fullSchema), defaultValues: {...} });
const [step, setStep] = useState(0);

async function next() {
  const step1Fields: (keyof Values)[] = ["email", "name"];
  const ok = await form.trigger(step1Fields);
  if (ok) setStep(1);
}
```

Alternative: one form per step, each with its own schema; accumulate
results in a parent state object. The single-form approach is preferred
because `reset` + `resetField` + `formState.isDirty` all work cleanly.

---

## 4. Rate Limits

N/A — no network. Two RHF-specific "rate" concerns:

- **Validation debouncing.** `mode: "onChange"` + async refines (e.g.
  "is this email taken?") will fire a request per keystroke. Fixes:
  (a) switch to `mode: "onBlur"`, (b) use `delayError: 300` to debounce
  error *display* but not validation itself, or (c) debounce the refine
  at the fetch layer. Prefer (a) for EOS forms.
- **`useWatch` callback fan-out.** If 20 fields subscribe to the whole
  form via `useWatch()`, each keystroke triggers 20 re-renders. Scope
  each `useWatch` to the smallest `name` path possible.

---

## 5. Error Codes and Recovery

RHF errors are surfaced via `formState.errors`, keyed by field path.
Each error has shape `{ type: string, message?: string, ref?: Ref }`.

Standard `type` values:
- From Zod: `"invalid_type"`, `"too_small"`, `"too_big"`,
  `"invalid_string"`, `"custom"`, etc. — from `ZodError.issues[].code`.
- From RHF native rules: `"required"`, `"min"`, `"max"`, `"minLength"`,
  `"maxLength"`, `"pattern"`, `"validate"`.
- User-defined via `setError`: any string. By convention use
  `"server"` for server-returned field errors.

**Root errors** — errors not tied to a field:
```ts
setError("root.serverError", { type: "500", message: "Try again" });
// read via form.formState.errors.root?.serverError
```
Root errors persist across submissions — you MUST call
`clearErrors("root.serverError")` at the top of the submit handler
before retrying, or they stick around visibly.

**Recovery patterns:**

| Error source         | Pattern                                                   |
|----------------------|-----------------------------------------------------------|
| Zod schema fail      | Auto — zodResolver populates `formState.errors`           |
| Server 400 per-field | Iterate `body.fieldErrors`, `setError(name, {type, msg})` |
| Server 400 generic   | `setError("root.server", {type:"400", message})`          |
| Server 5xx           | `setError("root.server", {type:String(status), message})`|
| Network failure      | React Query catches → `onError` → `setError("root.server")`|

---

## 6. SDK Idioms

- **Always type `useForm` with `z.input<typeof Schema>`**, not
  `z.infer` / `z.output`. Input type matches the form state *before*
  transforms and defaults — which is what the form fields actually hold.
- **Always pass `defaultValues`** — even empty strings. Omitting them
  causes "uncontrolled → controlled" warnings on any `Controller`.
- **Spread `register(name)` directly**; never wrap it in props you
  construct yourself. `<input {...register("email")} />` is the idiom.
- **`handleSubmit(onValid, onInvalid)` swallows throws** — wrap submit
  handlers that call async code in try/catch or use React Query's
  mutation and put the side effects in `onSuccess` / `onError`. Never
  rely on an unhandled promise rejection bubbling out of `handleSubmit`.
- **Subscribe via `useFormState({ control, name })` in child components**
  instead of reading `form.formState` directly — this isolates re-renders
  to the child that actually needs the state.
- **Use `as const` on indexed paths** in field arrays:
  ``register(`items.${index}.name` as const)``. Without `as const`, TS
  widens to `string` and you lose the typed path.
- **`form.reset()` with no args** resets to the original `defaultValues`
  captured at mount. `form.reset(newValues)` resets AND updates the
  captured defaults. Pick consciously — the difference matters for
  `isDirty`.
- **`keepDirtyValues: true` on `reset`** when syncing from React Query
  data so the user's in-progress edits survive a background refetch.

---

## 7. Anti-Patterns (see anti_patterns.md for code)

1. Re-creating the Zod schema inside the component body.
2. Passing async `defaultValues` without any `reset`/`values` plan.
3. `mode: "onChange"` with async refines (request storm).
4. `watch()` instead of `useWatch()` in performance-sensitive children.
5. Mutating `defaultValues` directly (e.g. `defaultValues.items.push(...)`).
6. Wrapping a controlled component (Radix Select) with `register()`.
7. Using array index as React `key` in `useFieldArray` (use `field.id`).
8. Forgetting to `clearErrors("root.server")` before the next submit.
9. Forgetting `as const` on indexed paths → loses type safety.
10. `getValues()` in render to read a value that should be `useWatch`.

---

## 8. Data Model

RHF represents a form as a **deeply nested object**, reachable via dot/
bracket paths. Every path that gets typed is a `FieldPath<T>`.

```
useForm<{ user: { name: string; emails: string[] }; agreed: boolean }>()
→ register("user.name")
→ register("user.emails.0")
→ register("agreed")
```

Types to know:
- `FieldValues` — base constraint, any object.
- `Path<T>` — all valid field paths (autocompleted by TS).
- `PathValue<T, P>` — the type at a given path.
- `FieldPathByValue<T, TValue>` — paths whose value matches `TValue`.
- `DeepPartial<T>` — used for `defaultValues`.
- `FieldErrors<T>` — mirror of `T` with `FieldError` at each leaf,
  plus `root?: Record<string, FieldError>` for non-field errors.

Internally, RHF stores:
- `_formValues` — the current values (derived lazily on `getValues`).
- `_formState` — Proxy-wrapped subscriptions.
- `_fields` — the registered field map (refs + options).
- `_defaultValues` — the original defaults captured at mount.

`formState` is a **Proxy**. Reading `formState.isDirty` subscribes the
component to `isDirty` changes only. Destructuring via
`const { isDirty } = formState` works the same way; RHF tracks Proxy
`get` operations at render time.

---

## 9. Webhooks

N/A — RHF is not event-sourced. The closest analogue is the `watch`
callback form: `form.watch((values, { name, type }) => { ... })` gives
you a subscription over every form change with the field name and
change type (`"change"`, `"blur"`, etc.). Remember to clean up:

```ts
useEffect(() => {
  const sub = form.watch((values, { name, type }) => {
    console.log(name, type, values);
  });
  return () => sub.unsubscribe();
}, [form.watch]);
```

---

## 10. Limits

- **No hard field count limit**, but `useForm` type inference slows
  noticeably around 50-100 fields with deeply nested Zod schemas. v8
  addresses this with lens types.
- **Max recursion depth** for path strings ≈ 5 levels nested before
  TypeScript gives up on autocomplete (this is a TS limitation, not RHF).
- **Bundle size** — `react-hook-form@7` is ~9kb gzipped core; the Zod
  resolver adds ~1kb; Zod itself is ~12kb gzipped. Total form stack
  cost: ~22kb gzipped vs Formik+Yup at ~45kb.

---

## 11. Cost Model

No money cost. Engineering cost dimensions:

- **Re-render cost.** `register` inputs: 0 parent re-renders per
  keystroke. `Controller` inputs: 1 re-render per keystroke, scoped to
  the Controller's subtree. `watch()` (from useForm): 1 re-render of
  the component holding the `useForm` per keystroke on any field.
  `useWatch({ name })`: 1 re-render of the subscribing child per
  matched change.
- **Validation cost.** Sync Zod schemas: <1ms for typical forms.
  Async refines: bounded by network. `mode` choice directly multiplies
  validation cost by keystroke count.
- **Learning curve cost.** The register/Controller split is the single
  biggest confusion point; every new dev asks the same questions. This
  skill is the primary mitigation.

---

## 12. Version Pinning

- **Current stable**: `react-hook-form@7.54.x` (April 2026).
- **Resolvers**: `@hookform/resolvers@3.9.x` — version lockstep with
  Zod. Resolvers 3.x supports both Zod 3.23+ and Zod 4 (`zod/v4`
  import path).
- **v8 beta**: shipped `8.0.0-beta` with TS perf improvements and
  composable lens operations. Breaking changes not finalized.
- **Peer dep**: `react@^16.8 || ^17 || ^18 || ^19`. Works with React
  19 with the bridge pattern documented in integrations.md.
- **Deprecation watch**: nothing deprecated in v7. v8 will deprecate the
  `keyName` option (internal `_id` replaces it) — but v8 is not in EOS.

Pin exact in package.json:
```json
"react-hook-form": "7.54.2",
"@hookform/resolvers": "3.9.1"
```

---

# Tier 2 — Creator Intelligence

## 13. Design Intent and Tradeoffs

React Hook Form was launched in 2019 by **Bill Luo (bluebill1049)**
with a single thesis: **form state does not belong in React state**.
Every other React form library up to that point (Formik, Final Form,
Redux-Form) stored values in React state and triggered a re-render on
every keystroke. For small forms nobody noticed. For a 30-field
onboarding form on a mid-range Android phone, that's hundreds of
re-renders per typed word and dropped frames on every field.

Bill's insight: the browser already has form state. It's in the DOM.
Every `<input>` holds its own value. React's "controlled component"
model is a convention we impose on top of that — it isn't required.

RHF's design choices all fall out of this one insight:

- **Refs over state.** `register` attaches a ref. Values are read from
  the DOM on demand (submit, blur, trigger) — not stored in React.
- **Subscriptions over broadcasts.** The Proxy-wrapped `formState` and
  the `useWatch` / `useFormState` hooks let components subscribe to
  exactly the keys they care about. Nothing else re-renders.
- **Controller as an escape hatch, not a default.** For libraries that
  don't expose refs (MUI, Radix, react-select), `<Controller>` bridges
  back to the controlled model — but even then, the Controller's
  subtree is isolated, so the damage is contained.
- **Schema-first validation via resolvers.** RHF doesn't own validation.
  It exposes a `resolver` interface and ships adapters for Zod, Yup,
  Joi, Vest, Superstruct, class-validator, etc. The form library and
  the validation library should be independent.
- **Zero dependencies.** No peer besides React itself. No Yup. No
  Immutable. No Proxy polyfill. 9kb gzipped is the result.

What RHF is explicitly NOT:
- Not a UI library. It ships no JSX components except `Controller` and
  `FormProvider`.
- Not a state manager. It does not replace Redux / Zustand / Jotai for
  non-form state.
- Not opinionated about submission. It doesn't know about fetch, axios,
  or mutations. `handleSubmit(onValid)` just hands you validated values.

The tradeoff Bill made: **power over beauty**. RHF's API surface is
intimidating on first read — `register` vs `Controller` vs `useController`,
`watch` vs `useWatch`, `formState` vs `useFormState`, `reset` vs
`resetField`, `getValues` vs `getFieldState`. TanStack Form's designer
explicitly rejected this — TanStack Form has one primitive (controlled
fields) and more ergonomic TS at the cost of the uncontrolled perf
story. Both choices are defensible. RHF won the market because in 2019,
the perf story was the one nobody else had.

---

## 14. Problem-Solution Map and Hidden Capabilities

Problems RHF actually solves beyond "validates a form":

1. **Keystroke-level perf on large forms.** The headline story.
2. **Dynamic lists with stable identity.** `useFieldArray` plus
   `field.id` gives you add/remove/reorder without juggling your own
   keys or losing input focus on rerenders.
3. **Multi-step wizards without prop drilling.** Single `useForm` at
   the top, `<FormProvider>` below, `useFormContext()` in each step
   component. Values and errors survive across steps automatically.
4. **Conditional field trees.** `shouldUnregister: true` on a field
   means the moment it's unmounted, RHF forgets it ever existed —
   including its validation. Makes "show these fields only if X is
   checked" trivial.
5. **Async defaultValues from server data.** The `values` prop (added
   in v7.25) is a reactive alternative to `defaultValues`. Point it at
   `queryData` and the form syncs automatically.
6. **Server error injection.** `setError('field', {type:'server', message})`
   puts a server-side validation result on the exact field, with the
   exact message, using the exact JSX the form already renders.
7. **Accessible forms without writing ARIA.** When combined with
   shadcn's `<FormField>`, `<FormLabel>`, `<FormControl>`, `<FormMessage>`
   primitives, every field gets `aria-invalid`, `aria-describedby`, and
   focus management for free. (`shouldFocusError: true`, default, jumps
   focus to the first invalid field on submit.)

Hidden capabilities most users miss:

- **`form.setFocus('name', { shouldSelect: true })`** — programmatic
  focus + text selection on any registered field.
- **`form.getFieldState('name', form.formState)`** — get the dirty/
  touched/error state for a single field without subscribing the whole
  component to the whole `formState`.
- **`criteriaMode: 'all'`** — collects every error on a field, not just
  the first. Combined with `errors.field.types`, lets you render a
  bullet list of all failing rules.
- **`resetOptions: { keepDirtyValues: true }`** — reset default values
  without clobbering user-edited fields. Essential for background
  refetches.
- **`delayError: 500`** — debounces the *display* of errors while still
  validating in the background. Better UX than `mode: 'onBlur'` for
  some UIs because the error doesn't snap in mid-type.
- **`useFormState({ control, name: 'email' })`** in a disconnected
  component — lets a submit button live anywhere in the tree and read
  the form's validity without being inside `<FormProvider>`.
- **`form.trigger()`** with no args — re-runs the whole resolver on
  demand. Useful after programmatic `setValue` to re-validate without
  waiting for blur.

---

## 15. Operational Behavior and Edge Cases

- **Unmounting a field unregisters it** only if `shouldUnregister: true`
  is set (either at the form or field level). Default is `false` —
  values survive unmount. If you want conditional fields to forget
  themselves, opt in.
- **`defaultValues` is captured by reference at mount.** Mutating the
  object you passed in does NOT update RHF's internal copy. Always pass
  a fresh object or use `reset(newValues)`.
- **`values` prop uses deep equality check** (`deepEqual`) to decide
  whether to trigger a sync. If your React Query data returns a new
  top-level object on every refetch but the contents are unchanged,
  `values` will still sync — but combine with `keepDirtyValues` to
  avoid clobbering in-progress edits.
- **`formState.isValid`** requires an initial validation to be
  meaningful. If `mode: "onSubmit"` (the default), `isValid` stays
  `true` until the first submit attempt. Use `mode: "onChange"` or call
  `trigger()` on mount if you need a live valid/invalid indicator
  (e.g. disabling the submit button).
- **Controller + native input is a footgun.** If you wrap an `<input>`
  in `<Controller>`, RHF manages it as controlled — you lose the perf
  win and you get an extra re-render per keystroke for no reason.
- **Controlled `value={undefined}` warnings.** React will warn
  "uncontrolled → controlled" if you let a field's value be `undefined`
  at any point. Always pass a defined default (`""`, `false`, `[]`,
  `null`).
- **`useFieldArray.fields` is a snapshot, not live.** The `fields`
  array you destructure is captured at render time. Don't read
  ``fields[index].name`` inside an event handler — use
  ``form.getValues(`items.${index}.name`)`` instead.
- **Strict Mode double-invokes `useForm`.** This is fine — `useForm`
  is idempotent. But if you're seeding defaults from a `useRef` or a
  module-level variable, the second invocation will see the first's
  side effects. Keep defaults pure.
- **Safari autofill skips `register`.** Because RHF listens to `change`
  events and Safari autofill doesn't always fire one, autofilled values
  can be missing from `form.getValues()` until the user focuses the
  field. Mitigation: call `trigger()` on blur of the first field, or
  use `form.setValue` from an `onAnimationStart` handler (Safari's
  autofill animation is detectable).

---

## 16. Ecosystem Position and Composition

RHF sits in the **form state** slot of the EOS SaaS frontend:

```
Zod (schema/validation)  ←─┐
                           ├── React Hook Form (form state + submit)
shadcn/ui <Form> (JSX) ────┘            │
                                        ├── React Query (mutation)
                                        │       │
                                        │       ├── onSuccess → reset
                                        │       └── onError → setError
                                        │
                                        └── Express + validate() middleware (server)
                                               │
                                               └── same Zod schema
```

Natural complements:
- **Zod** — schema-first validation. The canonical pairing. Zod's
  `safeParseAsync` drives `zodResolver`; Zod's messages drive
  `<FormMessage>`.
- **shadcn/ui `<Form>`** — thin layer of JSX over RHF's `<FormProvider>`
  + `<Controller>`. Gives you ARIA, focus, and error rendering for free.
- **React Query** — submission lives in `useMutation`. Async defaults
  live in `useQuery` + `values` prop. Cache invalidation post-submit
  lives in `onSuccess`.
- **TypeScript strict** — the form's types flow from `z.input<typeof
  Schema>` through `useForm<T>` to every `register` call.

Forced / problematic integrations:
- **Redux Form / Formik in the same app** — technically possible, never
  a good idea. Pick one, migrate the rest.
- **RHF + React 19 Server Actions raw** — not a drop-in swap. Use the
  bridge pattern (RHF owns client state, Action owns server submission,
  `useActionState` errors feed back via `setError`).
- **RHF + Remix actions** — use `<Form method="post">` from Remix AND
  RHF: Remix handles navigation + progressive enhancement, RHF handles
  validation and complex state. This is a first-class pattern in the
  Remix community.
- **RHF without a resolver** — technically works (use `rules` on
  `register` / `Controller`), but you lose schema-level validation,
  server reuse, and type inference. Never do this in EOS.

---

## 17. Trajectory and Evolution

Where RHF is going:

- **v8 (beta in 2026).** TypeScript performance rework — the deeply
  nested `Path<T>` inference that chokes TS on 100+ field schemas is
  replaced with a compile-time-friendly "lens" abstraction. Also adds
  composable lens operations for working with deeply nested data while
  maintaining type safety. Beta right now; no production EOS usage.
- **React 19 interop.** Bill has been explicit that RHF will NOT
  absorb `useActionState` / Actions into its core. Instead, docs and
  community patterns will show the bridge: RHF for validation/state,
  Actions for submission. This is already the recommended pattern.
- **Devtools.** `@hookform/devtools` gets steady updates. Expect more
  integration with React DevTools via component-tree annotations.
- **Resolvers package** evolves with the validation library ecosystem.
  Zod 4 support is the current focus; Valibot and ArkType are supported.

What's NOT getting investment:
- `shouldUseNativeValidation` mode — still supported, not promoted.
  Native HTML validation gives you less control and worse accessibility.
- `rules` on `register` — still supported for simple cases, but the
  narrative is "use a resolver." Don't build new forms with `rules`.
- `formState.isLoading` (async defaultValues) — superseded by the
  `values` prop + external state management (React Query).

Signals to watch:
- When shadcn/ui publishes a v8-compatible `<Form>`, it's time to plan
  an EOS migration.
- When `@hookform/resolvers` deprecates the Zod 3 code path, we need
  to be on Zod 4 already.
- When `react@19.1` adds `<form>` onSubmit integration with Actions +
  validation, the bridge pattern may shrink to zero code.

---

## 18. Conceptual Model and Solution Recipes

**The mental model in one paragraph:** a form is an uncontrolled DOM
subtree with a subscription layer on top. `register` attaches refs and
says "I care about this input." `useForm`'s returned object is a
Proxy that gives the component access to the parts of form state it
cares about. `handleSubmit` reads every ref, runs them through the
resolver, and hands you a validated, typed object. `<Controller>` is
an escape hatch for when refs aren't available. Everything else is
convenience over those primitives.

### Recipe 1 — Minimal create form with optimistic mutation

```
Schema in src/schemas/lead.ts (LeadCreate)
  ↓
useForm<z.input<typeof LeadCreate>>({
  resolver: zodResolver(LeadCreate),
  defaultValues: { name: "", email: "", source: "inbound" }
})
  ↓
shadcn <Form>, <FormField> for each field
  ↓
const createLead = useMutation({
  mutationFn: postLead,
  onMutate: async (v) => { await qc.cancelQueries(["leads"]);
    const snap = qc.getQueryData(["leads"]);
    qc.setQueryData(["leads"], (o) => [...o, { id: "tmp", ...v }]);
    return { snap }; },
  onError: (err, v, ctx) => { qc.setQueryData(["leads"], ctx.snap);
    form.setError("root.server", { message: err.message }); },
  onSuccess: () => form.reset(),
  onSettled: () => qc.invalidateQueries(["leads"]),
});
  ↓
handleSubmit(v => createLead.mutate(v))
```

### Recipe 2 — Edit form that stays in sync with React Query

```
const { data } = useQuery({ queryKey: ["lead", id], queryFn: ... });
const form = useForm<Values>({
  resolver: zodResolver(LeadSchema),
  defaultValues: emptyLead,
  values: data,                               // reactive
  resetOptions: { keepDirtyValues: true },    // preserve edits on refetch
});
```

### Recipe 3 — Dynamic row editor (array of leads)

```
useFieldArray({ control, name: "leads", keyName: "rhfId" })
  ↓ (rename to rhfId so your DB id survives)
fields.map((field, i) => (
  <Row key={field.id} ... />
))
  ↓
append({ name: "", email: "" })   // button
remove(i)                          // per-row
```

### Recipe 4 — Wizard (multi-step)

```
<FormProvider {...form}>
  {step === 0 && <StepEmail />}
  {step === 1 && <StepProfile />}
  {step === 2 && <StepReview />}
  <button onClick={async () => {
    const ok = await form.trigger(stepFields[step]);
    if (ok) setStep(s => s + 1);
  }}>Next</button>
</FormProvider>

// Child steps use useFormContext()
function StepEmail() {
  const form = useFormContext<Values>();
  return <FormField control={form.control} name="email" ... />;
}
```

### Recipe 5 — Dependent fields via useWatch

```
function CountryState() {
  const { control, setValue } = useFormContext<Values>();
  const country = useWatch({ control, name: "country" });
  // when country changes, clear the state field
  useEffect(() => { setValue("state", ""); }, [country, setValue]);
  const states = useQuery({ queryKey: ["states", country], queryFn: ... });
  return <Select ... options={states.data} />;
}
```

---

## 19. Industry Expert and Cutting-Edge Usage

**TkDodo (Dominik Dorfmeister, TanStack Query maintainer)** writes the
canonical "React Query and Forms" piece. His core recommendation for
EOS-shaped apps:

1. Let React Query own the server state.
2. Let RHF own the form state.
3. Use `defaultValues` set from the *first* successful query result
   only — or use `values` with `keepDirtyValues`.
4. Submission is a `useMutation`; invalidate on `onSettled`.
5. Never try to write form state back into the query cache manually —
   it's a footgun.

**Kent C. Dodds** and **Matt Pocock** (TypeScript) both hammer the
`z.input<typeof Schema>` vs `z.infer<typeof Schema>` distinction. Use
`z.input` for `useForm<T>()` whenever the schema has `.default()` or
`.transform()` — otherwise TS will demand fields that don't exist yet
in the form state.

**Bill Luo's own frontier patterns (bluebill1049 on X):**
- `useFormState({ control, name: [...] })` to scope re-renders as
  tightly as possible in dashboards with many forms.
- `criteriaMode: "all"` + `errors.field.types` for building "password
  strength" style multi-rule UIs.
- `shouldUnregister: true` at the form level for conditional subtrees
  in wizards — makes the final submitted object only contain currently
  mounted fields.

**Markus Oberlehner's React 19 bridge pattern** (cited in SKILL.md
sources) is the published canonical answer to "should I migrate RHF
forms to useActionState?" — short version: no, bridge them.

**Bundle size frontier:** there's an active push in 2026 to replace
`@hookform/resolvers/zod` with a `~200 byte` inline adapter for users
who only need sync validation. Not in EOS yet; watch for the next
resolvers release.

**Frontier pattern seen in production apps (2026):** combining
RHF `useFieldArray` with React Query's `useInfiniteQuery` to build
editable grids that load more rows as the user scrolls, with stable
`field.id` surviving page boundary loads. Requires `replace()` on
each page merge and careful handling of the `keyName` gotcha.

**Anti-frontier** — teams that migrated from RHF to TanStack Form in
2025 and regretted it cite three reasons: (1) bundle size grew (~20kb
vs 9kb), (2) team productivity dropped because the API is more verbose,
(3) shadcn/ui's `<Form>` primitives are RHF-only. The move is only
justified if your forms exceed ~100 deeply nested fields and TS
inference is visibly slow.

---

# Sources

- https://react-hook-form.com — official site
- https://react-hook-form.com/docs/useform — useForm API
- https://react-hook-form.com/docs/usecontroller/controller — Controller
- https://react-hook-form.com/docs/usefieldarray — useFieldArray
- https://react-hook-form.com/docs/useform/seterror — setError
- https://react-hook-form.com/advanced-usage — wizard, async defaults
- https://react-hook-form.com/faqs — FAQ
- https://github.com/react-hook-form/resolvers — zodResolver adapter
- https://github.com/orgs/react-hook-form/discussions/11832 — React 19
- https://ui.shadcn.com/docs/components/form — shadcn Form primitives
- https://tkdodo.eu/blog/react-query-and-forms — TkDodo integration guide
- https://markus.oberlehner.net/blog/using-react-hook-form-with-react-19-use-action-state-and-next-js-15-app-router — RHF + Actions bridge
- https://blog.logrocket.com/whats-new-in-react-hook-form-v7/ — v7 perf model
- https://makersden.io/blog/composable-form-handling-in-2025-react-hook-form-tanstack-form-and-beyond — 2025 comparison
- https://medium.com/@granthgharewal/react-hook-form-usefieldarray-silently-overwrites-your-id — keyName gotcha
