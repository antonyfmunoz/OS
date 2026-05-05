# TanStack Query — EOS Examples

Concrete, paste-ready patterns shaped to the EOS SaaS stack:
React 18 + TS strict + Vite + Zod + RHF + shadcn/ui + Express/Drizzle.

---

## (a) QueryClient with EOS defaults

```ts
// src/lib/query-client.ts
import { QueryClient, QueryCache, MutationCache } from "@tanstack/react-query";
import { toast } from "sonner";

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public fieldErrors?: Record<string, string[]>,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error, query) => {
      // Only toast for background refetch failures (initial fetches
      // are handled by the component that owns the query).
      if (query.state.data !== undefined) {
        toast.error(
          (query.meta?.errorMessage as string) ??
            `Failed to refresh: ${error.message}`,
        );
      }
    },
  }),
  mutationCache: new MutationCache({
    onError: (error, _vars, _ctx, mutation) => {
      // Mutations without their own onError fall through here.
      const message =
        (mutation.meta?.errorMessage as string) ??
        (error instanceof Error ? error.message : "Action failed");
      toast.error(message);
    },
  }),
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      gcTime: 5 * 60_000,
      retry: (failureCount, error) => {
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
          return false; // don't retry 4xx
        }
        return failureCount < 1;
      },
      refetchOnWindowFocus: "always",
      refetchOnReconnect: true,
    },
    mutations: {
      retry: 0,
    },
  },
});

export { ApiError };
```

```tsx
// src/main.tsx
import { createRoot } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { queryClient } from "./lib/query-client";
import { Toaster } from "@/components/ui/sonner";
import App from "./App";

createRoot(document.getElementById("root")!).render(
  <QueryClientProvider client={queryClient}>
    <App />
    <Toaster richColors position="top-right" />
    {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
  </QueryClientProvider>,
);
```

---

## (b) Query key factory for a feature

```ts
// src/features/leads/queries.ts
import { queryOptions, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { ApiError } from "@/lib/query-client";

// Zod schema — single source of truth for shape
export const LeadSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  email: z.string().email(),
  status: z.enum(["new", "contacted", "qualified", "lost", "won"]),
  owner_id: z.string().uuid(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
});
export type Lead = z.infer<typeof LeadSchema>;

export const LeadListSchema = z.object({
  items: z.array(LeadSchema),
  nextCursor: z.string().nullable(),
  total: z.number(),
});

export type LeadFilters = {
  status?: Lead["status"];
  q?: string;
  sort?: "created_at" | "name";
};

// Query key factory — hierarchical, colocated
export const leadKeys = {
  all: ["leads"] as const,
  lists: () => [...leadKeys.all, "list"] as const,
  list: (filters: LeadFilters) =>
    [...leadKeys.lists(), filters] as const,
  infinites: () => [...leadKeys.all, "infinite"] as const,
  infinite: (filters: LeadFilters) =>
    [...leadKeys.infinites(), filters] as const,
  details: () => [...leadKeys.all, "detail"] as const,
  detail: (id: string) => [...leadKeys.details(), id] as const,
};

// Generic fetch helper
async function apiFetch<T>(
  url: string,
  schema: z.ZodSchema<T>,
  init?: RequestInit & { signal?: AbortSignal },
): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    credentials: "include",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(
      body.message ?? res.statusText,
      res.status,
      body.errors,
    );
  }
  return schema.parse(await res.json());
}

// queryOptions — reusable across useQuery, prefetchQuery, setQueryData
export function leadDetailOptions(id: string) {
  return queryOptions({
    queryKey: leadKeys.detail(id),
    queryFn: ({ signal }) =>
      apiFetch(`/api/leads/${id}`, LeadSchema, { signal }),
    staleTime: 30_000,
    meta: { errorMessage: "Failed to load lead" },
  });
}

export function leadListOptions(filters: LeadFilters) {
  return queryOptions({
    queryKey: leadKeys.list(filters),
    queryFn: ({ signal }) => {
      const params = new URLSearchParams();
      if (filters.status) params.set("status", filters.status);
      if (filters.q) params.set("q", filters.q);
      if (filters.sort) params.set("sort", filters.sort);
      return apiFetch(
        `/api/leads?${params}`,
        LeadListSchema,
        { signal },
      );
    },
    staleTime: 20_000,
    placeholderData: (prev) => prev, // keepPreviousData behavior
    meta: { errorMessage: "Failed to load leads" },
  });
}

// Custom hooks — the only thing components import
export function useLead(id: string) {
  return useQuery(leadDetailOptions(id));
}

export function useLeadList(filters: LeadFilters) {
  return useQuery(leadListOptions(filters));
}
```

---

## (c) `useQuery` with `select` for render transforms

```ts
// Only this component re-renders when the lead's email changes,
// not when any other field changes — because it selects down to
// a single string.
export function useLeadEmail(id: string) {
  return useQuery({
    ...leadDetailOptions(id),
    select: (lead) => lead.email,
  });
}

// Project a list into a view model without caching the transform:
export function useLeadOptions() {
  return useQuery({
    ...leadListOptions({}),
    select: (res) => res.items.map((l) => ({ value: l.id, label: l.name })),
  });
}
```

`select` runs on every render, but is memoized by referential equality
of the query data. Because of `structuralSharing`, unchanged fields
keep their references, so `select` output is stable when nothing
relevant changed.

---

## (d) `useMutation` with `onSuccess` invalidation

```ts
// src/features/leads/mutations.ts
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { LeadSchema, type Lead, leadKeys } from "./queries";
import { apiFetch } from "./queries";

export function useCreateLead() {
  const qc = useQueryClient();
  return useMutation({
    mutationKey: ["leads", "create"],
    mutationFn: (input: Omit<Lead, "id" | "created_at" | "updated_at">) =>
      apiFetch("/api/leads", LeadSchema, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: (lead) => {
      // Prime the detail cache so the detail page loads instantly.
      qc.setQueryData(leadKeys.detail(lead.id), lead);
      // Return the promise so isPending stays true until the refetch lands.
      return qc.invalidateQueries({ queryKey: leadKeys.lists() });
    },
    meta: { errorMessage: "Failed to create lead" },
  });
}

export function useDeleteLead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/api/leads/${id}`, z.object({ id: z.string() }), {
        method: "DELETE",
      }),
    onSuccess: (_, id) => {
      qc.removeQueries({ queryKey: leadKeys.detail(id) });
      return qc.invalidateQueries({ queryKey: leadKeys.lists() });
    },
  });
}
```

---

## (e) Optimistic update with rollback

```ts
// src/features/leads/mutations.ts
export function useUpdateLead(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (patch: Partial<Lead>) =>
      apiFetch(`/api/leads/${id}`, LeadSchema, {
        method: "PATCH",
        body: JSON.stringify(patch),
      }),
    onMutate: async (patch) => {
      // 1. Cancel any in-flight refetches so they don't clobber our optimism.
      await qc.cancelQueries({ queryKey: leadKeys.detail(id) });

      // 2. Snapshot.
      const previous = qc.getQueryData<Lead>(leadKeys.detail(id));

      // 3. Optimistically update.
      qc.setQueryData<Lead>(leadKeys.detail(id), (old) =>
        old ? { ...old, ...patch, updated_at: new Date().toISOString() } : old,
      );

      // 4. Return context for rollback.
      return { previous };
    },
    onError: (_err, _patch, ctx) => {
      if (ctx?.previous) {
        qc.setQueryData(leadKeys.detail(id), ctx.previous);
      }
    },
    onSettled: () => {
      // Refetch to get the server's version regardless of outcome.
      return qc.invalidateQueries({ queryKey: leadKeys.detail(id) });
    },
  });
}
```

---

## (f) `useSuspenseQuery` + `<ErrorBoundary>` page

```tsx
// src/pages/LeadDetailPage.tsx
import { Suspense } from "react";
import { ErrorBoundary } from "react-error-boundary";
import { useSuspenseQuery, useQueryErrorResetBoundary } from "@tanstack/react-query";
import { leadDetailOptions } from "@/features/leads/queries";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";

function LeadDetail({ id }: { id: string }) {
  const { data: lead } = useSuspenseQuery(leadDetailOptions(id));
  // data is guaranteed non-null — no loading/error branches here
  return (
    <article>
      <h1>{lead.name}</h1>
      <p>{lead.email}</p>
      <span className="badge">{lead.status}</span>
    </article>
  );
}

function LeadSkeleton() {
  return (
    <div className="space-y-3">
      <Skeleton className="h-8 w-64" />
      <Skeleton className="h-4 w-48" />
      <Skeleton className="h-6 w-24" />
    </div>
  );
}

export function LeadDetailPage({ id }: { id: string }) {
  const { reset } = useQueryErrorResetBoundary();
  return (
    <ErrorBoundary
      onReset={reset}
      fallbackRender={({ error, resetErrorBoundary }) => (
        <div className="rounded border border-destructive p-4">
          <p>Couldn't load lead: {error.message}</p>
          <Button onClick={resetErrorBoundary}>Try again</Button>
        </div>
      )}
    >
      <Suspense fallback={<LeadSkeleton />}>
        <LeadDetail id={id} />
      </Suspense>
    </ErrorBoundary>
  );
}
```

---

## (g) `useInfiniteQuery` for paginated lead list

```ts
import { useInfiniteQuery } from "@tanstack/react-query";
import { leadKeys, LeadListSchema, apiFetch, type LeadFilters } from "./queries";

export function useInfiniteLeads(filters: LeadFilters) {
  return useInfiniteQuery({
    queryKey: leadKeys.infinite(filters),
    queryFn: ({ pageParam, signal }) => {
      const params = new URLSearchParams();
      if (pageParam) params.set("cursor", pageParam);
      if (filters.status) params.set("status", filters.status);
      if (filters.q) params.set("q", filters.q);
      return apiFetch(
        `/api/leads?${params}`,
        LeadListSchema,
        { signal },
      );
    },
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.nextCursor,
    maxPages: 20, // cap memory
    staleTime: 20_000,
  });
}
```

```tsx
function LeadListInfinite({ filters }: { filters: LeadFilters }) {
  const q = useInfiniteLeads(filters);
  const rows = q.data?.pages.flatMap((p) => p.items) ?? [];

  if (q.isPending) return <LeadSkeleton />;
  if (q.isError) return <ErrorCard error={q.error} />;

  return (
    <>
      <ul>
        {rows.map((lead) => (
          <li key={lead.id}>{lead.name}</li>
        ))}
      </ul>
      {q.hasNextPage && (
        <Button
          onClick={() => q.fetchNextPage()}
          disabled={q.isFetchingNextPage}
        >
          {q.isFetchingNextPage ? "Loading..." : "Load more"}
        </Button>
      )}
    </>
  );
}
```

---

## (h) RHF + RQ mutation with server-side 400 errors

```tsx
// src/features/leads/LeadEditForm.tsx
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Form, FormField, FormItem, FormLabel, FormControl, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useLead } from "./queries";
import { useUpdateLead } from "./mutations";
import { ApiError } from "@/lib/query-client";

const LeadFormSchema = z.object({
  name: z.string().min(1, "Name required"),
  email: z.string().email("Enter a valid email"),
  status: z.enum(["new", "contacted", "qualified", "lost", "won"]),
});
type LeadFormValues = z.input<typeof LeadFormSchema>;

export function LeadEditForm({ id }: { id: string }) {
  const leadQuery = useLead(id);
  const update = useUpdateLead(id);

  const form = useForm<LeadFormValues>({
    resolver: zodResolver(LeadFormSchema),
    defaultValues: { name: "", email: "", status: "new" },
    values: leadQuery.data, // sync with server state
    resetOptions: { keepDirtyValues: true },
    mode: "onBlur",
  });

  function onSubmit(values: LeadFormValues) {
    form.clearErrors("root.server");
    update.mutate(values, {
      onSuccess: (saved) => {
        // update.onSuccess already primes cache + invalidates lists.
        form.reset(saved); // baseline so isDirty=false
      },
      onError: (err) => {
        if (err instanceof ApiError && err.fieldErrors) {
          for (const [name, messages] of Object.entries(err.fieldErrors)) {
            form.setError(name as keyof LeadFormValues, {
              type: "server",
              message: messages[0],
            });
          }
        } else {
          form.setError("root.server", {
            type: "server",
            message: err instanceof Error ? err.message : "Save failed",
          });
        }
      },
    });
  }

  if (leadQuery.isPending) return <LeadSkeleton />;
  if (leadQuery.isError) return <p>Failed to load.</p>;

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
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
        {form.formState.errors.root?.server && (
          <p className="text-destructive text-sm">
            {form.formState.errors.root.server.message}
          </p>
        )}
        <Button type="submit" disabled={update.isPending}>
          {update.isPending ? "Saving..." : "Save"}
        </Button>
      </form>
    </Form>
  );
}
```

---

## (i) Dependent queries with `enabled` (and `skipToken` in v5.25+)

```ts
import { skipToken, useQuery } from "@tanstack/react-query";

// Legacy pattern — works, but `userId` can be undefined inside queryFn
// and TS doesn't help you.
function useUserPosts(userId: string | undefined) {
  return useQuery({
    queryKey: ["posts", userId],
    queryFn: () => fetchPosts(userId!),   // non-null assertion, ugh
    enabled: !!userId,
  });
}

// Preferred (v5.25+): skipToken keeps types honest.
function useUserPostsBetter(userId: string | undefined) {
  return useQuery({
    queryKey: ["posts", userId],
    queryFn: userId ? () => fetchPosts(userId) : skipToken,
    // no `enabled` needed — skipToken disables the query
  });
}
```

---

## (j) Prefetch on hover for instant detail navigation

```tsx
import { useQueryClient } from "@tanstack/react-query";
import { Link } from "wouter";
import { leadDetailOptions } from "@/features/leads/queries";

function LeadRow({ lead }: { lead: Lead }) {
  const qc = useQueryClient();

  return (
    <Link
      href={`/leads/${lead.id}`}
      onMouseEnter={() => {
        // Fire and forget — prefetchQuery dedupes and caches
        qc.prefetchQuery(leadDetailOptions(lead.id));
      }}
      onFocus={() => qc.prefetchQuery(leadDetailOptions(lead.id))}
    >
      {lead.name}
    </Link>
  );
}
```

By the time the user clicks, the detail query is already cached and
the detail page renders instantly. Combine with `useSuspenseQuery` in
the detail page for zero-spinner navigation.
