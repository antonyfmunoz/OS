# Sonner — EOS Recipes

Real, compilable React 18 + TypeScript. Drop into `/opt/OS/saas/*`.

## 1. Root mount (shadcn pattern)

```tsx
// src/components/ui/sonner.tsx
"use client";
import { useTheme } from "next-themes";
import { Toaster as SonnerToaster, type ToasterProps } from "sonner";

export function Toaster(props: ToasterProps) {
  const { theme = "system" } = useTheme();
  return (
    <SonnerToaster
      theme={theme as ToasterProps["theme"]}
      richColors
      closeButton
      position="bottom-right"
      visibleToasts={4}
      {...props}
    />
  );
}
```

## 2. Every toast variant in one file

```tsx
import { toast } from "sonner";

export function ToastShowcase() {
  return (
    <div className="flex flex-col gap-2">
      <button onClick={() => toast("Default message")}>Default</button>
      <button onClick={() => toast.success("Saved")}>Success</button>
      <button onClick={() => toast.error("Failed", { description: "Network error" })}>
        Error
      </button>
      <button onClick={() => toast.info("Heads up")}>Info</button>
      <button onClick={() => toast.warning("Disk almost full")}>Warning</button>
      <button onClick={() => toast.loading("Working...")}>Loading</button>
      <button
        onClick={() =>
          toast("Lead archived", {
            action: { label: "Undo", onClick: () => console.log("undo") },
          })
        }
      >
        With action
      </button>
      <button
        onClick={() =>
          toast.custom((id) => (
            <div className="rounded-md border bg-background p-4 shadow">
              <div className="font-medium">Custom JSX toast</div>
              <button onClick={() => toast.dismiss(id)}>Close</button>
            </div>
          ))
        }
      >
        Custom
      </button>
    </div>
  );
}
```

## 3. `toast.promise` wrapping a `useMutation`

```tsx
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

type Lead = { id: string; name: string };
type LeadInput = { name: string; email: string };

async function createLead(input: LeadInput): Promise<Lead> {
  const res = await fetch("/api/leads", {
    method: "POST",
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export function useCreateLead() {
  const qc = useQueryClient();
  const mutation = useMutation({
    mutationFn: createLead,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["leads"] }),
  });

  function submit(values: LeadInput) {
    toast.promise(mutation.mutateAsync(values), {
      loading: "Creating lead...",
      success: (lead) => `Created ${lead.name}`,
      error: (err: Error) => `Failed: ${err.message}`,
    });
  }

  return { submit, mutation };
}
```

## 4. React Query global error toast (MutationCache)

```tsx
// src/lib/query-client.ts
import {
  QueryClient,
  QueryCache,
  MutationCache,
} from "@tanstack/react-query";
import { toast } from "sonner";

export const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
  queryCache: new QueryCache({
    onError: (err, query) => {
      // Skip background refetch errors
      if (query.state.data !== undefined) return;
      toast.error("Failed to load", {
        description: err instanceof Error ? err.message : String(err),
      });
    },
  }),
  mutationCache: new MutationCache({
    onError: (err) => {
      toast.error("Action failed", {
        description: err instanceof Error ? err.message : String(err),
      });
    },
  }),
});
```

## 5. Form submit with optimistic toast and rollback

```tsx
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

const schema = z.object({ note: z.string().min(1) });
type FormValues = z.infer<typeof schema>;

type Lead = { id: string; note?: string };

export function NoteForm({ leadId }: { leadId: string }) {
  const qc = useQueryClient();
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { note: "" },
  });

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      const res = await fetch(`/api/leads/${leadId}`, {
        method: "PATCH",
        body: JSON.stringify(values),
      });
      if (!res.ok) throw new Error("Save failed");
      return res.json() as Promise<Lead>;
    },
    onMutate: async (values) => {
      await qc.cancelQueries({ queryKey: ["lead", leadId] });
      const prev = qc.getQueryData<Lead>(["lead", leadId]);
      qc.setQueryData<Lead>(["lead", leadId], (old) =>
        old ? { ...old, note: values.note } : old,
      );
      return { prev };
    },
    onError: (err, _values, ctx) => {
      if (ctx?.prev) qc.setQueryData(["lead", leadId], ctx.prev);
      toast.error("Save failed — restored", {
        description: err instanceof Error ? err.message : String(err),
      });
    },
    onSuccess: () => {
      toast.success("Note saved");
      form.reset();
    },
  });

  return (
    <form onSubmit={form.handleSubmit((v) => mutation.mutate(v))}>
      <textarea {...form.register("note")} />
      <button type="submit" disabled={mutation.isPending}>
        Save
      </button>
    </form>
  );
}
```

## 6. Long-running job with manual id updates

```tsx
import { toast } from "sonner";

export async function uploadWithProgress(file: File) {
  const id = toast.loading(`Uploading ${file.name} (0%)`);
  try {
    await uploadInChunks(file, {
      onProgress: (pct) => {
        toast.loading(`Uploading ${file.name} (${pct}%)`, { id });
      },
    });
    toast.success(`Uploaded ${file.name}`, { id });
  } catch (err) {
    toast.error(`Failed: ${file.name}`, {
      id,
      description: err instanceof Error ? err.message : String(err),
      duration: Infinity,
      closeButton: true,
    });
  }
}

async function uploadInChunks(
  file: File,
  opts: { onProgress: (pct: number) => void },
): Promise<void> {
  for (let pct = 0; pct <= 100; pct += 10) {
    await new Promise((r) => setTimeout(r, 100));
    opts.onProgress(pct);
  }
}
```

## 7. AlertDialog confirm + toast feedback

```tsx
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { useMutation } from "@tanstack/react-query";

export function DeleteLeadButton({ leadId }: { leadId: string }) {
  const mutation = useMutation({
    mutationFn: async () => {
      const res = await fetch(`/api/leads/${leadId}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Delete failed");
    },
  });

  function confirm() {
    toast.promise(mutation.mutateAsync(), {
      loading: "Deleting...",
      success: "Lead deleted",
      error: (err: Error) => `Failed: ${err.message}`,
    });
  }

  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button variant="destructive">Delete</Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete this lead?</AlertDialogTitle>
          <AlertDialogDescription>
            This action cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction onClick={confirm}>Delete</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
```

## 8. Network status indicator with stable id

```tsx
import * as React from "react";
import { toast } from "sonner";

export function NetworkStatusWatcher() {
  React.useEffect(() => {
    const onOffline = () => {
      toast.error("You're offline", {
        id: "net-status",
        duration: Infinity,
        description: "Changes will sync when reconnected",
      });
    };
    const onOnline = () => {
      toast.success("Back online", { id: "net-status", duration: 2000 });
    };
    window.addEventListener("offline", onOffline);
    window.addEventListener("online", onOnline);
    return () => {
      window.removeEventListener("offline", onOffline);
      window.removeEventListener("online", onOnline);
    };
  }, []);
  return null;
}
```
