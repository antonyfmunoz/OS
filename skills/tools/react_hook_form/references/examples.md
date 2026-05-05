# React Hook Form — EOS Examples

Every example assumes React 18 + TypeScript strict + shadcn/ui + Zod +
React Query. Import alias `@/` = `src/`.

---

## (a) Login form — shadcn Form + Zod + RHF + React Query (canonical EOS pattern)

```ts
// src/schemas/auth.ts
import { z } from "zod";

export const LoginSchema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(8, "At least 8 characters"),
  remember: z.boolean().default(false),
});
export type LoginValues = z.input<typeof LoginSchema>;
```

```tsx
// src/components/login-form.tsx
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { LoginSchema, type LoginValues } from "@/schemas/auth";
import {
  Form, FormField, FormItem, FormLabel,
  FormControl, FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";

type ServerError = Error & {
  status?: number;
  fieldErrors?: Partial<Record<keyof LoginValues, string>>;
};

async function login(values: LoginValues) {
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(values),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const err: ServerError = Object.assign(
      new Error(body.message ?? "Login failed"),
      { status: res.status, fieldErrors: body.fieldErrors }
    );
    throw err;
  }
  return res.json() as Promise<{ token: string }>;
}

export function LoginForm() {
  const form = useForm<LoginValues>({
    resolver: zodResolver(LoginSchema),
    defaultValues: { email: "", password: "", remember: false },
    mode: "onBlur",
  });

  const mutation = useMutation({
    mutationFn: login,
    onSuccess: () => form.reset(),
    onError: (err: ServerError) => {
      if (err.fieldErrors) {
        for (const [name, message] of Object.entries(err.fieldErrors)) {
          form.setError(name as keyof LoginValues, {
            type: "server",
            message: message as string,
          });
        }
        return;
      }
      form.setError("root.server", {
        type: String(err.status ?? 500),
        message: err.message,
      });
    },
  });

  function onSubmit(values: LoginValues) {
    form.clearErrors("root.server"); // critical — root errors persist otherwise
    mutation.mutate(values);
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl>
                <Input type="email" autoComplete="email" {...field} />
              </FormControl>
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
              <FormControl>
                <Input type="password" autoComplete="current-password" {...field} />
              </FormControl>
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
                <Checkbox
                  checked={field.value}
                  onCheckedChange={field.onChange}
                />
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

---

## (b) Dynamic field array — multiple leads

```tsx
// src/components/leads-bulk-form.tsx
import { useForm, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Form, FormField, FormItem, FormLabel,
  FormControl, FormMessage,
} from "@/components/ui/form";

const LeadRow = z.object({
  // Critical: if your DB has an `id`, rename it here. useFieldArray
  // injects its own `id` and would clobber yours.
  dbId: z.string().uuid().optional(),
  name: z.string().min(1, "Required"),
  email: z.string().email("Valid email required"),
});
const BulkSchema = z.object({
  leads: z.array(LeadRow).min(1, "Add at least one lead"),
});
type BulkValues = z.input<typeof BulkSchema>;

export function LeadsBulkForm() {
  const form = useForm<BulkValues>({
    resolver: zodResolver(BulkSchema),
    defaultValues: { leads: [{ name: "", email: "" }] },
  });
  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: "leads",
    // belt-and-suspenders: if we ever add an `id` field, rename the RHF one
    keyName: "rhfId" as any,
  });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(console.log)} className="space-y-4">
        {fields.map((field, index) => (
          // IMPORTANT: field.id (stable UUID from RHF), never index
          <div key={field.id} className="flex items-start gap-2">
            <FormField
              control={form.control}
              name={`leads.${index}.name` as const}
              render={({ field }) => (
                <FormItem className="flex-1">
                  <FormLabel className={index === 0 ? "" : "sr-only"}>Name</FormLabel>
                  <FormControl><Input {...field} /></FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name={`leads.${index}.email` as const}
              render={({ field }) => (
                <FormItem className="flex-1">
                  <FormLabel className={index === 0 ? "" : "sr-only"}>Email</FormLabel>
                  <FormControl><Input type="email" {...field} /></FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              disabled={fields.length === 1}
              onClick={() => remove(index)}
              aria-label={`Remove row ${index + 1}`}
            >×</Button>
          </div>
        ))}
        <Button type="button" variant="outline" onClick={() => append({ name: "", email: "" })}>
          Add another lead
        </Button>
        <Button type="submit">Submit all</Button>
      </form>
    </Form>
  );
}
```

Key insights:
- `key={field.id}` is what keeps React DOM stable across reorders.
- `append({ name: "", email: "" })` — pass a complete object, not a
  partial. Missing fields become `undefined` → controlled warnings.
- `disabled={fields.length === 1}` enforces `.min(1)` in UI.

---

## (c) Async defaultValues from React Query — the `values` prop pattern

```tsx
// src/components/edit-lead-form.tsx
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { LeadSchema, type LeadValues } from "@/schemas/lead";

const emptyLead: LeadValues = {
  name: "", email: "", phone: "", notes: "", stage: "cold",
};

export function EditLeadForm({ id }: { id: string }) {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["lead", id],
    queryFn: async () => {
      const res = await fetch(`/api/leads/${id}`);
      return LeadSchema.parse(await res.json());
    },
  });

  const form = useForm<LeadValues>({
    resolver: zodResolver(LeadSchema),
    defaultValues: emptyLead,   // renders immediately with empty shell
    values: data,               // reactive — syncs whenever React Query refetches
    resetOptions: {
      keepDirtyValues: true,    // don't clobber in-progress edits on refetch
      keepErrors: false,
    },
  });

  const mutation = useMutation({
    mutationFn: async (values: LeadValues) => {
      const res = await fetch(`/api/leads/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
      });
      if (!res.ok) throw new Error(await res.text());
      return LeadSchema.parse(await res.json());
    },
    onSuccess: (saved) => {
      qc.setQueryData(["lead", id], saved);
      // reset to the newly-saved values so isDirty = false
      form.reset(saved);
    },
  });

  if (isLoading) return <div>Loading…</div>;

  return (
    /* ...shadcn <Form> JSX as in example (a)... */
    null as any
  );
}
```

Why this beats the `useEffect + reset` pattern:
- No effect hook, no dep array to mess up.
- `values` is deep-compared internally — noop if React Query
  returns the same data.
- `keepDirtyValues: true` means if the user is mid-edit when a
  background refetch lands, their typing survives.

---

## (d) Reset after successful mutation (simple create form)

```tsx
const form = useForm<LeadValues>({
  resolver: zodResolver(LeadSchema),
  defaultValues: emptyLead,
});

const mutation = useMutation({
  mutationFn: createLead,
  onSuccess: (created) => {
    // Option A: clear the form back to the original defaults
    form.reset();

    // Option B: clear AND update the "baseline" so isDirty comparisons
    // work against the newly-saved state (useful if you stay on the page)
    // form.reset(emptyLead);

    // Option C: keep the values but clear errors + submit state
    // form.reset(form.getValues(), { keepValues: true, keepDirty: false });

    toast.success(`Lead ${created.name} created`);
  },
});
```

The three options above map to three UX decisions. Pick one deliberately.

---

## (e) Dependent fields via useWatch (country → state)

```tsx
import { useWatch, useFormContext } from "react-hook-form";
import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";

type Values = { country: string; state: string };

export function CountryStateFields() {
  const form = useFormContext<Values>();
  // subscribe ONLY to `country` — this component re-renders when country
  // changes; the parent form does not.
  const country = useWatch({ control: form.control, name: "country" });

  // When country changes, blank the state field.
  useEffect(() => {
    form.setValue("state", "", { shouldValidate: false, shouldDirty: true });
  }, [country, form]);

  const states = useQuery({
    queryKey: ["states", country],
    queryFn: () => fetch(`/api/states?country=${country}`).then(r => r.json()),
    enabled: !!country,
  });

  return (
    <>
      <FormField
        control={form.control}
        name="country"
        render={({ field }) => (
          <FormItem>
            <FormLabel>Country</FormLabel>
            <FormControl>
              <select {...field}>
                <option value="">Select…</option>
                <option value="US">United States</option>
                <option value="CA">Canada</option>
              </select>
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
      <FormField
        control={form.control}
        name="state"
        render={({ field }) => (
          <FormItem>
            <FormLabel>State</FormLabel>
            <FormControl>
              <select {...field} disabled={!country || states.isLoading}>
                <option value="">Select…</option>
                {states.data?.map((s: { code: string; name: string }) => (
                  <option key={s.code} value={s.code}>{s.name}</option>
                ))}
              </select>
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
    </>
  );
}
```

Why `useWatch` and not `form.watch("country")`? `useWatch` isolates the
re-render to this child component. `form.watch` would re-render the
parent holding `useForm` — every keystroke in any other field.

---

## (f) Controller + custom date picker (react-day-picker)

```tsx
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { DayPicker } from "react-day-picker";
import { format } from "date-fns";
import {
  Popover, PopoverContent, PopoverTrigger,
} from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { CalendarIcon } from "lucide-react";

const Schema = z.object({
  dueDate: z.date({ required_error: "Pick a date" }),
});
type Values = z.input<typeof Schema>;

export function TaskForm() {
  const { control, handleSubmit, formState: { errors } } = useForm<Values>({
    resolver: zodResolver(Schema),
    defaultValues: { dueDate: undefined as unknown as Date },
  });

  return (
    <form onSubmit={handleSubmit(console.log)}>
      <Controller
        control={control}
        name="dueDate"
        render={({ field }) => (
          <Popover>
            <PopoverTrigger asChild>
              <Button variant="outline">
                <CalendarIcon className="mr-2 h-4 w-4" />
                {field.value ? format(field.value, "PPP") : "Pick a date"}
              </Button>
            </PopoverTrigger>
            <PopoverContent>
              <DayPicker
                mode="single"
                selected={field.value}
                onSelect={field.onChange}   // field.onChange is RHF's setValue for this field
                onDayBlur={field.onBlur}    // wire onBlur for "touched" state
              />
            </PopoverContent>
          </Popover>
        )}
      />
      {errors.dueDate && <p className="text-destructive">{errors.dueDate.message}</p>}
      <Button type="submit">Save</Button>
    </form>
  );
}
```

Why `Controller` here: `<DayPicker>` doesn't expose a DOM ref to an
input — it's a fully controlled component. `register` can't attach
anything to it. `Controller` bridges by calling `field.onChange` when
the picker fires its own change event.

---

## (g) Multi-step wizard with partial schemas + trigger()

```tsx
import { useState } from "react";
import { useForm, FormProvider, useFormContext } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

const Step1 = z.object({
  email: z.string().email(),
});
const Step2 = z.object({
  name: z.string().min(1),
  bio: z.string().max(280),
});
const Step3 = z.object({
  acceptTos: z.literal(true, {
    errorMap: () => ({ message: "You must accept the terms" }),
  }),
});
const FullSchema = Step1.merge(Step2).merge(Step3);
type Values = z.input<typeof FullSchema>;

const stepFields: (keyof Values)[][] = [
  ["email"],
  ["name", "bio"],
  ["acceptTos"],
];

export function SignupWizard() {
  const form = useForm<Values>({
    resolver: zodResolver(FullSchema),
    defaultValues: { email: "", name: "", bio: "", acceptTos: false as any },
    mode: "onBlur",
  });
  const [step, setStep] = useState(0);

  async function next() {
    const ok = await form.trigger(stepFields[step]);
    if (ok) setStep((s) => s + 1);
  }

  function onSubmit(values: Values) {
    // final values, fully validated
    console.log(values);
  }

  return (
    <FormProvider {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)}>
        {step === 0 && <StepEmail />}
        {step === 1 && <StepProfile />}
        {step === 2 && <StepReview />}
        <div className="flex justify-between">
          {step > 0 && (
            <button type="button" onClick={() => setStep((s) => s - 1)}>Back</button>
          )}
          {step < 2 && (
            <button type="button" onClick={next}>Next</button>
          )}
          {step === 2 && <button type="submit">Create account</button>}
        </div>
      </form>
    </FormProvider>
  );
}

function StepEmail() {
  const form = useFormContext<Values>();
  return (
    <FormField
      control={form.control}
      name="email"
      render={({ field }) => (
        <FormItem>
          <FormLabel>Email</FormLabel>
          <FormControl><Input type="email" {...field} /></FormControl>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}
// StepProfile, StepReview similar...
```

Key insights:
- ONE `useForm` at the top. Steps are just UI.
- `form.trigger(stepFields[step])` validates only the current step's
  fields before advancing. `handleSubmit` at the end validates the whole
  schema.
- `<FormProvider>` + `useFormContext` avoids prop-drilling `form` into
  every step component.

---

## (h) Server error injection — per-field + global

```tsx
function onSubmit(values: LeadValues) {
  // ALWAYS clear previous root errors first — they persist otherwise.
  form.clearErrors("root.server");

  mutation.mutate(values, {
    onError: (err: any) => {
      // 1) Per-field server validation (Express validate() middleware shape)
      if (err.status === 400 && err.body?.errors) {
        for (const [name, messages] of Object.entries<string[]>(err.body.errors)) {
          form.setError(name as keyof LeadValues, {
            type: "server",
            message: messages[0],
          });
        }
        // focus the first invalid field
        const firstField = Object.keys(err.body.errors)[0] as keyof LeadValues;
        form.setFocus(firstField);
        return;
      }

      // 2) Global server error (5xx, timeout, unknown 4xx)
      form.setError("root.server", {
        type: String(err.status ?? "network"),
        message: err.message ?? "Something went wrong. Try again.",
      });
    },
  });
}

// In JSX — render the global error once, above the submit button:
{form.formState.errors.root?.server && (
  <div
    role="alert"
    className="rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive"
  >
    {form.formState.errors.root.server.message}
  </div>
)}
```

Shape contract with the Express side (see Zod integrations.md):

```ts
// server/middleware/validate.ts already returns this shape on 400:
// { errors: { email: ["Email already taken"], password: ["Too short"] } }
```

The field names in `body.errors` MUST match the RHF field paths, which
MUST match the Zod schema keys. One schema, three places, one shape.
