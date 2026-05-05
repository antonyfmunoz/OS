# Radix UI — EOS Recipes

Real, compilable React 18 + TypeScript. Every example assumes
shadcn-style imports from `@/components/ui/*` (which wrap the
matching `@radix-ui/react-*` package).

---

## 1. Controlled Dialog + RHF + Zod + TanStack Query mutation

```tsx
"use client";
import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const LeadSchema = z.object({
  name: z.string().min(1, "Required"),
  email: z.string().email(),
  source: z.enum(["instagram", "referral", "cold"]),
});
type LeadValues = z.infer<typeof LeadSchema>;

export function CreateLeadDialog() {
  const [open, setOpen] = React.useState(false);
  const qc = useQueryClient();

  const form = useForm<LeadValues>({
    resolver: zodResolver(LeadSchema),
    defaultValues: { name: "", email: "", source: "instagram" },
  });

  const create = useMutation({
    mutationFn: async (values: LeadValues) => {
      const res = await fetch("/api/leads", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(values),
      });
      if (!res.ok) throw new Error("Failed");
      return res.json();
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["leads"] });
      toast.success("Lead created");
      setOpen(false);
      form.reset();
    },
    onError: (e) => toast.error(e.message),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>New lead</Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={form.handleSubmit((v) => create.mutate(v))}>
          <DialogHeader>
            <DialogTitle>Create lead</DialogTitle>
            <DialogDescription>
              Add a new lead to the Initiate Arena pipeline.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="name">Name</Label>
              <Input id="name" {...form.register("name")} />
              {form.formState.errors.name && (
                <p className="text-sm text-destructive">
                  {form.formState.errors.name.message}
                </p>
              )}
            </div>
            <div className="grid gap-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" {...form.register("email")} />
            </div>
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="ghost"
              onClick={() => setOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Saving..." : "Save"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
```

---

## 2. Popover with Floating UI collision avoidance

```tsx
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";

export function DatePickerButton({
  value,
  onChange,
}: {
  value: Date | undefined;
  onChange: (d: Date | undefined) => void;
}) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="outline">
          {value ? value.toLocaleDateString() : "Pick a date"}
        </Button>
      </PopoverTrigger>
      <PopoverContent
        className="w-auto p-0"
        align="start"
        sideOffset={8}
        collisionPadding={16}
      >
        <Calendar mode="single" selected={value} onSelect={onChange} />
      </PopoverContent>
    </Popover>
  );
}
```

---

## 3. DropdownMenu with sub-menu and checkbox items (multi-filter)

```tsx
import * as React from "react";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";

type Status = "new" | "contacted" | "qualified" | "won" | "lost";

export function LeadFilters({
  selected,
  onChange,
}: {
  selected: Set<Status>;
  onChange: (next: Set<Status>) => void;
}) {
  const toggle = (s: Status) => {
    const next = new Set(selected);
    next.has(s) ? next.delete(s) : next.add(s);
    onChange(next);
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline">Filters ({selected.size})</Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>Status</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {(["new", "contacted", "qualified", "won", "lost"] as Status[]).map(
          (s) => (
            <DropdownMenuCheckboxItem
              key={s}
              checked={selected.has(s)}
              onCheckedChange={() => toggle(s)}
              onSelect={(e) => e.preventDefault()}
            >
              {s}
            </DropdownMenuCheckboxItem>
          ),
        )}
        <DropdownMenuSeparator />
        <DropdownMenuSub>
          <DropdownMenuSubTrigger>More</DropdownMenuSubTrigger>
          <DropdownMenuSubContent>
            <DropdownMenuCheckboxItem
              onSelect={(e) => e.preventDefault()}
            >
              Has email
            </DropdownMenuCheckboxItem>
          </DropdownMenuSubContent>
        </DropdownMenuSub>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

---

## 4. Tooltip on icon button (with required Provider at root)

```tsx
// app/layout.tsx
import { TooltipProvider } from "@/components/ui/tooltip";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <TooltipProvider delayDuration={200}>{children}</TooltipProvider>
      </body>
    </html>
  );
}
```

```tsx
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Button } from "@/components/ui/button";
import { Trash } from "lucide-react";

export function DeleteIconButton({ onClick }: { onClick: () => void }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button size="icon" variant="ghost" onClick={onClick}>
          <Trash className="h-4 w-4" />
        </Button>
      </TooltipTrigger>
      <TooltipContent side="top">Delete lead</TooltipContent>
    </Tooltip>
  );
}
```

---

## 5. Sonner toast vs Radix Toast — choose Sonner

```tsx
// app/layout.tsx
import { Toaster } from "sonner";
// ...
<body>
  {children}
  <Toaster position="top-right" richColors closeButton />
</body>
```

```tsx
// anywhere
import { toast } from "sonner";
toast.success("Lead created");
toast.error("Save failed");
toast.promise(saveLead(values), {
  loading: "Saving...",
  success: "Saved",
  error: "Failed",
});
```

We do NOT use `@radix-ui/react-toast` because Sonner stacks multiple
toasts more cleanly, ships smaller, and integrates with shadcn out of
the box.

---

## 6. Select with non-empty sentinel value

```tsx
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export function SourceFilter({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="w-[180px]">
        <SelectValue placeholder="Source" />
      </SelectTrigger>
      <SelectContent>
        {/* sentinel — Radix forbids value="" */}
        <SelectItem value="all">All sources</SelectItem>
        <SelectItem value="instagram">Instagram</SelectItem>
        <SelectItem value="referral">Referral</SelectItem>
        <SelectItem value="cold">Cold</SelectItem>
      </SelectContent>
    </Select>
  );
}
```

---

## 7. Tabs synced to URL via nuqs

```tsx
"use client";
import { useQueryState } from "nuqs";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export function VenturesTabs() {
  const [tab, setTab] = useQueryState("tab", { defaultValue: "active" });
  return (
    <Tabs value={tab} onValueChange={setTab}>
      <TabsList>
        <TabsTrigger value="active">Active</TabsTrigger>
        <TabsTrigger value="paused">Paused</TabsTrigger>
        <TabsTrigger value="archived">Archived</TabsTrigger>
      </TabsList>
      <TabsContent value="active">…</TabsContent>
      <TabsContent value="paused">…</TabsContent>
      <TabsContent value="archived">…</TabsContent>
    </Tabs>
  );
}
```

---

## 8. AlertDialog for destructive confirmation (mutation gates close)

```tsx
import * as React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
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

export function DeleteCampaignButton({ id }: { id: string }) {
  const [open, setOpen] = React.useState(false);
  const qc = useQueryClient();
  const del = useMutation({
    mutationFn: () =>
      fetch(`/api/campaigns/${id}`, { method: "DELETE" }).then((r) => {
        if (!r.ok) throw new Error("Delete failed");
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["campaigns"] });
      toast.success("Campaign deleted");
      setOpen(false);
    },
    onError: (e) => toast.error(e.message),
  });

  return (
    <AlertDialog open={open} onOpenChange={setOpen}>
      <AlertDialogTrigger asChild>
        <Button variant="destructive">Delete</Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete this campaign?</AlertDialogTitle>
          <AlertDialogDescription>
            All attached leads will be unlinked. This cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={(e) => {
              e.preventDefault(); // prevent auto-close
              del.mutate();
            }}
          >
            {del.isPending ? "Deleting..." : "Delete"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
```

---

## 9. asChild composition with Next.js Link

```tsx
import Link from "next/link";
import {
  NavigationMenu,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
} from "@/components/ui/navigation-menu";

export function MainNav() {
  return (
    <NavigationMenu>
      <NavigationMenuList>
        <NavigationMenuItem>
          <NavigationMenuLink asChild>
            <Link href="/dashboard">Dashboard</Link>
          </NavigationMenuLink>
        </NavigationMenuItem>
        <NavigationMenuItem>
          <NavigationMenuLink asChild>
            <Link href="/leads">Leads</Link>
          </NavigationMenuLink>
        </NavigationMenuItem>
      </NavigationMenuList>
    </NavigationMenu>
  );
}
```

---

## 10. VisuallyHidden title for icon-only Dialog

```tsx
import * as VisuallyHidden from "@radix-ui/react-visually-hidden";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

export function ImagePreviewDialog({ src }: { src: string }) {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <button>
          <img src={src} className="h-12 w-12 rounded" alt="" />
        </button>
      </DialogTrigger>
      <DialogContent className="max-w-3xl p-0">
        <VisuallyHidden.Root>
          <DialogTitle>Image preview</DialogTitle>
        </VisuallyHidden.Root>
        <img src={src} className="h-full w-full" alt="" />
      </DialogContent>
    </Dialog>
  );
}
```
