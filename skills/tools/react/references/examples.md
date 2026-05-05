# React — EOS-Aligned Examples

Realistic patterns for `/opt/OS/saas` work. React 18 + TS strict,
Vite, Tailwind, shadcn/ui, React Query, React Hook Form, Zod.

---

## 1. Component with typed props, children slot, variants

```tsx
import { type ReactNode } from "react";
import { cn } from "@/lib/utils";

type Variant = "default" | "danger" | "success";

interface StatCardProps {
  label: string;
  value: string | number;
  variant?: Variant;
  footer?: ReactNode;
  className?: string;
}

const variantStyles: Record<Variant, string> = {
  default: "border-border",
  danger: "border-destructive/40 bg-destructive/5",
  success: "border-emerald-500/40 bg-emerald-500/5",
};

export function StatCard({
  label,
  value,
  variant = "default",
  footer,
  className,
}: StatCardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border p-4 flex flex-col gap-1",
        variantStyles[variant],
        className,
      )}
    >
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-2xl font-semibold tabular-nums">{value}</span>
      {footer && <div className="mt-2 text-xs">{footer}</div>}
    </div>
  );
}
```

---

## 2. Custom hook — `useDebouncedValue`

```tsx
import { useEffect, useState } from "react";

export function useDebouncedValue<T>(value: T, delayMs = 250): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(id);
  }, [value, delayMs]);
  return debounced;
}
```

Usage with React Query — debounce search input without a re-render
storm:

```tsx
function LeadSearch() {
  const [q, setQ] = useState("");
  const debounced = useDebouncedValue(q, 300);
  const { data, isFetching } = useQuery({
    queryKey: ["leads", "search", debounced],
    queryFn: () => searchLeads(debounced),
    enabled: debounced.length >= 2,
  });
  return (
    <>
      <Input value={q} onChange={(e) => setQ(e.target.value)} />
      {isFetching && <Spinner />}
      <LeadList leads={data ?? []} />
    </>
  );
}
```

---

## 3. React Query — list + mutation with optimistic update

```tsx
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

const leadsKey = ["leads"] as const;

export function useLeads() {
  return useQuery({
    queryKey: leadsKey,
    queryFn: async (): Promise<Lead[]> => {
      const r = await fetch("/api/leads");
      if (!r.ok) throw new Error(await r.text());
      return r.json();
    },
    staleTime: 30_000,
  });
}

export function useCreateLead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: CreateLeadInput): Promise<Lead> => {
      const r = await fetch("/api/leads", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      });
      if (!r.ok) throw new Error(await r.text());
      return r.json();
    },
    onMutate: async (input) => {
      await qc.cancelQueries({ queryKey: leadsKey });
      const prev = qc.getQueryData<Lead[]>(leadsKey);
      const optimistic: Lead = {
        id: `tmp-${crypto.randomUUID()}`,
        createdAt: new Date().toISOString(),
        ...input,
      };
      qc.setQueryData<Lead[]>(leadsKey, (old) => [optimistic, ...(old ?? [])]);
      return { prev };
    },
    onError: (_err, _input, ctx) => {
      if (ctx?.prev) qc.setQueryData(leadsKey, ctx.prev);
    },
    onSettled: () => qc.invalidateQueries({ queryKey: leadsKey }),
  });
}
```

---

## 4. Form — React Hook Form + Zod + shadcn Form primitives

```tsx
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Form, FormControl, FormField, FormItem, FormLabel, FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

const leadSchema = z.object({
  name: z.string().min(1, "Required").max(80),
  email: z.string().email(),
  company: z.string().optional(),
  notes: z.string().max(1000).optional(),
});
export type LeadFormValues = z.infer<typeof leadSchema>;

export function LeadForm({
  onSubmit,
  defaultValues,
}: {
  onSubmit: (v: LeadFormValues) => Promise<void> | void;
  defaultValues?: Partial<LeadFormValues>;
}) {
  const form = useForm<LeadFormValues>({
    resolver: zodResolver(leadSchema),
    defaultValues: { name: "", email: "", ...defaultValues },
  });

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit)}
        className="flex flex-col gap-4"
      >
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Name</FormLabel>
              <FormControl><Input {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
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
        <Button type="submit" disabled={form.formState.isSubmitting}>
          {form.formState.isSubmitting ? "Saving..." : "Save"}
        </Button>
      </form>
    </Form>
  );
}
```

Wiring the form to React Query:

```tsx
function NewLeadPage() {
  const createLead = useCreateLead();
  return (
    <LeadForm
      onSubmit={async (values) => {
        await createLead.mutateAsync(values);
      }}
    />
  );
}
```

---

## 5. Compound component with Context

```tsx
import { createContext, useContext, useState, type ReactNode } from "react";

interface DisclosureCtx {
  open: boolean;
  toggle: () => void;
}
const Ctx = createContext<DisclosureCtx | null>(null);

function useDisclosureCtx() {
  const v = useContext(Ctx);
  if (!v) throw new Error("Disclosure.* must be used inside <Disclosure>");
  return v;
}

export function Disclosure({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <Ctx.Provider value={{ open, toggle: () => setOpen((o) => !o) }}>
      {children}
    </Ctx.Provider>
  );
}

Disclosure.Button = function DisclosureButton({
  children,
}: { children: ReactNode }) {
  const { toggle, open } = useDisclosureCtx();
  return (
    <button onClick={toggle} aria-expanded={open}>
      {children}
    </button>
  );
};

Disclosure.Panel = function DisclosurePanel({
  children,
}: { children: ReactNode }) {
  const { open } = useDisclosureCtx();
  return open ? <div>{children}</div> : null;
};
```

---

## 6. Error boundary + Suspense

```tsx
import { Suspense } from "react";

export function DashboardShell({ children }: { children: ReactNode }) {
  return (
    <ErrorBoundary fallback={<ErrorState />}>
      <Suspense fallback={<DashboardSkeleton />}>{children}</Suspense>
    </ErrorBoundary>
  );
}
```

---

## 7b. React 19 — Server-bound form with Actions + useActionState

```tsx
import { useActionState } from "react";

type State = { error: string | null; ok: boolean };

async function submitLead(_prev: State, formData: FormData): Promise<State> {
  const res = await fetch("/api/leads", { method: "POST", body: formData });
  if (!res.ok) return { error: await res.text(), ok: false };
  return { error: null, ok: true };
}

export function NewLeadForm() {
  const [state, action, pending] = useActionState(submitLead, {
    error: null, ok: false,
  });
  return (
    <form action={action} className="flex flex-col gap-3">
      <input name="name" required />
      <input name="email" type="email" required />
      <button type="submit" disabled={pending}>
        {pending ? "Saving…" : "Create lead"}
      </button>
      {state.error && <p role="alert">{state.error}</p>}
      {state.ok && <p>Lead created.</p>}
    </form>
  );
}
```

## 7c. React 19 — Optimistic UI with useOptimistic

```tsx
import { useOptimistic, startTransition } from "react";

type Msg = { id: string; text: string; pending?: boolean };

export function Chat({ messages, send }: {
  messages: Msg[];
  send: (text: string) => Promise<void>;
}) {
  const [optimistic, addOptimistic] = useOptimistic<Msg[], string>(
    messages,
    (state, text) => [...state, { id: `tmp-${Date.now()}`, text, pending: true }],
  );

  async function onSubmit(formData: FormData) {
    const text = formData.get("text") as string;
    startTransition(() => addOptimistic(text));
    await send(text); // throw → React auto-rolls back the optimistic item
  }

  return (
    <>
      <ul>{optimistic.map((m) =>
        <li key={m.id} style={{ opacity: m.pending ? 0.5 : 1 }}>{m.text}</li>
      )}</ul>
      <form action={onSubmit}><input name="text" /></form>
    </>
  );
}
```

## 7d. React 19 — use() for reading a cached promise

```tsx
import { use, Suspense } from "react";

// Promise lives OUTSIDE render — created by a loader/cache
const leadsPromise: Promise<Lead[]> = fetch("/api/leads").then((r) => r.json());

function LeadList() {
  const leads = use(leadsPromise); // suspends until resolved
  return <ul>{leads.map((l) => <li key={l.id}>{l.name}</li>)}</ul>;
}

export function LeadsPage() {
  return (
    <Suspense fallback={<Spinner />}>
      <LeadList />
    </Suspense>
  );
}
```

Note: in EOS, prefer `useSuspenseQuery` from TanStack Query over hand-rolling `use()` with raw fetches — Query owns the cache and `use()` composes with it cleanly.

## 7e. React 19 — ref as a normal prop (no forwardRef)

```tsx
// Old (React 18)
const Input18 = forwardRef<HTMLInputElement, InputProps>((props, ref) =>
  <input ref={ref} {...props} />);

// New (React 19)
interface InputProps extends React.ComponentProps<"input"> {
  ref?: React.Ref<HTMLInputElement>;
}
export function Input({ ref, ...rest }: InputProps) {
  return <input ref={ref} {...rest} />;
}
```

---

## 8. Concurrent features — startTransition

```tsx
import { useState, useTransition } from "react";

function FilterableTable({ rows }: { rows: Row[] }) {
  const [query, setQuery] = useState("");
  const [deferredQuery, setDeferredQuery] = useState("");
  const [isPending, startTransition] = useTransition();

  const filtered = rows.filter((r) =>
    r.name.toLowerCase().includes(deferredQuery.toLowerCase()),
  );

  return (
    <>
      <Input
        value={query}
        onChange={(e) => {
          setQuery(e.target.value); // urgent — keeps input snappy
          startTransition(() => setDeferredQuery(e.target.value)); // non-urgent
        }}
      />
      <div className={isPending ? "opacity-50" : undefined}>
        <Table rows={filtered} />
      </div>
    </>
  );
}
```
