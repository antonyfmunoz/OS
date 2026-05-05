# React Hook Form — Anti-Patterns

Real failure modes we have hit or will hit in `/opt/OS/saas`. Each
entry: the wrong code, why it fails, and the fix.

---

## 1. Re-creating the Zod schema inside the component

**Wrong:**
```tsx
export function MyForm() {
  const schema = z.object({ email: z.string().email() }); // new on every render
  const form = useForm({ resolver: zodResolver(schema) });
}
```

**Why:** a new schema object on every render makes `zodResolver` a new
function on every render, which triggers internal subscription resets
on every render. Validation feels laggy and async refines can fire
twice.

**Fix:** hoist the schema to module scope (or import it from
`src/schemas/`).

```tsx
const Schema = z.object({ email: z.string().email() });

export function MyForm() {
  const form = useForm({ resolver: zodResolver(Schema) });
}
```

---

## 2. Forgetting `defaultValues` on a Controller / shadcn FormField

**Wrong:**
```tsx
const form = useForm<LoginValues>({ resolver: zodResolver(LoginSchema) });
// no defaultValues

<FormField
  control={form.control}
  name="email"
  render={({ field }) => <Input {...field} />}
/>
```

**Why:** `field.value` is `undefined` on first render. The `<Input>`
starts as uncontrolled (`value={undefined}`), then the first keystroke
sets a string, triggering React's "uncontrolled → controlled" warning.
Intermittently, the input loses focus on the first character.

**Fix:** every field in the schema gets an explicit default.

```tsx
const form = useForm<LoginValues>({
  resolver: zodResolver(LoginSchema),
  defaultValues: { email: "", password: "", remember: false },
});
```

Rule of thumb: empty string for strings, `false` for booleans, `[]`
for arrays, `null` for nullable numbers. Never `undefined`.

---

## 3. `watch()` on every field in large forms

**Wrong:**
```tsx
export function BigForm() {
  const { watch, register, handleSubmit } = useForm<Values>({...});
  const values = watch(); // subscribes to ALL fields
  return (
    <form>
      {values.enableAdvanced && <AdvancedSection />}
      {/* ...40 more fields... */}
    </form>
  );
}
```

**Why:** `watch()` with no args returns the whole form and causes the
component holding `useForm` to re-render on every keystroke in any
field. With 40 fields and a rich JSX tree, typing becomes visibly
janky on mobile.

**Fix:** `useWatch({ control, name: 'enableAdvanced' })` in a child
component. Only that child re-renders.

```tsx
function AdvancedGate({ control }: { control: Control<Values> }) {
  const enabled = useWatch({ control, name: "enableAdvanced" });
  return enabled ? <AdvancedSection /> : null;
}

// Parent stays pristine:
export function BigForm() {
  const form = useForm<Values>({...});
  return (
    <form>
      <AdvancedGate control={form.control} />
      {/* ...40 more fields... */}
    </form>
  );
}
```

---

## 4. Mutating `defaultValues` directly

**Wrong:**
```tsx
const defaults = { items: [] as string[] };
const form = useForm({ defaultValues: defaults });

function addItem(v: string) {
  defaults.items.push(v); // NO — RHF has already copied this
  // form still shows empty items
}
```

**Why:** RHF captures `defaultValues` at mount. Mutating the reference
afterward does nothing to the form state. The UI will stay empty while
you swear you just pushed an item.

**Fix:** use `form.setValue` or `useFieldArray.append`.

```tsx
form.setValue("items", [...form.getValues("items"), v]);
// or
append(v);
```

---

## 5. Wrapping a controlled component with `register()`

**Wrong:**
```tsx
// Radix Select doesn't forward a ref to a DOM input
<Select {...register("role")}>
  <SelectTrigger><SelectValue /></SelectTrigger>
  <SelectContent>
    <SelectItem value="admin">Admin</SelectItem>
  </SelectContent>
</Select>
```

**Why:** `register` attaches a `ref`, `onChange`, and `onBlur` to its
target. Radix `<Select>` doesn't forward `ref` to a DOM input and
doesn't fire a DOM `change` event. The spread props go nowhere. On
submit, `role` is `undefined`.

**Fix:** use `<FormField>` + `<Controller>`.

```tsx
<FormField
  control={form.control}
  name="role"
  render={({ field }) => (
    <FormItem>
      <FormLabel>Role</FormLabel>
      <Select value={field.value} onValueChange={field.onChange}>
        <FormControl>
          <SelectTrigger><SelectValue /></SelectTrigger>
        </FormControl>
        <SelectContent>
          <SelectItem value="admin">Admin</SelectItem>
        </SelectContent>
      </Select>
      <FormMessage />
    </FormItem>
  )}
/>
```

---

## 6. Async defaultValues without any reset/values plan

**Wrong:**
```tsx
const { data } = useQuery({ queryKey: ["user"], queryFn: fetchUser });
const form = useForm<User>({
  defaultValues: data, // undefined on first render
});
```

**Why:** `defaultValues` is captured at mount. When `data` resolves,
RHF has already moved on. The form shows empty fields forever.

**Fix A (preferred):** use `values` prop, which is reactive:
```tsx
const form = useForm<User>({
  defaultValues: emptyUser,
  values: data,
  resetOptions: { keepDirtyValues: true },
});
```

**Fix B (legacy):** `useEffect` + `reset`:
```tsx
useEffect(() => {
  if (data) form.reset(data);
}, [data, form]);
```

---

## 7. Checkbox `checked` / `value` mismatch

**Wrong:**
```tsx
<FormField
  control={form.control}
  name="agreed"
  render={({ field }) => (
    <Checkbox {...field} /> // Radix Checkbox doesn't use `value`, it uses `checked`
  )}
/>
```

**Why:** `{...field}` spreads `value`, `onChange`, `onBlur`, `ref`,
`name`. Radix `<Checkbox>` expects `checked` + `onCheckedChange`. The
spread does nothing useful; the checkbox looks uncontrolled.

**Fix:** wire the props explicitly.

```tsx
<Checkbox
  checked={field.value}
  onCheckedChange={field.onChange}
  onBlur={field.onBlur}
  name={field.name}
  ref={field.ref}
/>
```

Same rule applies to every Radix primitive that uses `checked` /
`onCheckedChange`, `open` / `onOpenChange`, `pressed` / `onPressedChange`.

---

## 8. Array index as React key in useFieldArray

**Wrong:**
```tsx
{fields.map((field, index) => (
  <Row key={index} {...register(`items.${index}.name` as const)} />
))}
```

**Why:** when a user removes item 0, React re-uses the DOM node for
index 0 (now the old item 1's data), but RHF's internal state has
already shifted. Input focus and dirty state end up on the wrong row.

**Fix:** use `field.id` — the stable UUID RHF generates.

```tsx
{fields.map((field, index) => (
  <Row key={field.id} {...register(`items.${index}.name` as const)} />
))}
```

Also, remember RHF **overwrites** any existing `id` field in your data.
If your rows have a DB `id`, rename it (`dbId`) or pass
`keyName: "rhfId"` to `useFieldArray`.

---

## 9. Using `getValues()` where `useWatch` is needed

**Wrong:**
```tsx
function AdvancedGate() {
  const form = useFormContext<Values>();
  const enabled = form.getValues("enableAdvanced"); // NOT reactive
  return enabled ? <AdvancedSection /> : null;
}
```

**Why:** `getValues` reads the current value once, at render time. It
does NOT subscribe the component to changes. Toggling the checkbox
does nothing until some other unrelated re-render happens.

**Fix:** `useWatch`.

```tsx
const enabled = useWatch({ control: form.control, name: "enableAdvanced" });
```

Rule: `getValues` is for event handlers (read the latest on click /
submit). `useWatch` is for rendering reactively.

---

## 10. `mode: "onChange"` with async refines

**Wrong:**
```tsx
const Schema = z.object({
  email: z.string().email().refine(async (v) => {
    const res = await fetch(`/api/email-taken?email=${v}`);
    return !(await res.json()).taken;
  }, "Email already taken"),
});

const form = useForm({
  resolver: zodResolver(Schema),
  mode: "onChange", // FIRES PER KEYSTROKE
});
```

**Why:** every keystroke triggers the async refine → network request.
On a mid-range connection, the UI lags behind the user and the server
gets a request storm.

**Fix:** use `mode: "onBlur"` (or the default `"onSubmit"`). If you
need live feedback, debounce the refine in a custom hook and call
`form.trigger("email")` yourself.

```tsx
const form = useForm({
  resolver: zodResolver(Schema),
  mode: "onBlur",
});
```

---

## 11. Forgetting to `clearErrors("root.server")` before retry

**Wrong:**
```tsx
function onSubmit(values) {
  mutation.mutate(values, {
    onError: (err) => form.setError("root.server", { message: err.message }),
  });
}
// User fixes the issue, submits again, succeeds — but the old root
// error is still rendered, because root errors do not auto-clear.
```

**Fix:** clear at the top of every submit.

```tsx
function onSubmit(values) {
  form.clearErrors("root.server"); // <-- crucial
  mutation.mutate(values, { ... });
}
```

Or clear it in `onSuccess` of the mutation. Either works — just be
consistent.

---

## 12. Using `z.infer` instead of `z.input` for forms with defaults

**Wrong:**
```ts
const Schema = z.object({
  remember: z.boolean().default(false),
});
type Values = z.infer<typeof Schema>;  // { remember: boolean }
const form = useForm<Values>({ defaultValues: {} }); // TS error: remember required
```

**Why:** `z.infer` is the OUTPUT type — after defaults and transforms
apply. But the form state exists *before* Zod runs. The form can
legitimately have `remember: undefined` before the resolver fires.

**Fix:** use `z.input`.

```ts
type Values = z.input<typeof Schema>;   // { remember?: boolean }
const form = useForm<Values>({ defaultValues: { remember: false } });
```

See Zod integrations.md for the full story.
