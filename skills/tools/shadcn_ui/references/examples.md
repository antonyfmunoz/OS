# shadcn/ui — EOS-Aligned Examples

Real, executable patterns for /opt/OS/saas. Every snippet assumes
React 18 + TypeScript strict + Vite + Tailwind + the `@/` alias.

---

## 1. components.json for a Vite + TS + Tailwind EOS SaaS app

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": false,
  "tsx": true,
  "tailwind": {
    "config": "tailwind.config.ts",
    "css": "src/index.css",
    "baseColor": "zinc",
    "cssVariables": true,
    "prefix": ""
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  },
  "iconLibrary": "lucide"
}
```

Matching `vite.config.ts` alias (required):

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
});
```

Matching `tsconfig.json`:

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": { "@/*": ["./src/*"] }
  }
}
```

Matching `tailwind.config.ts` (key parts):

```ts
import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{ts,tsx}",
  ],
  theme: {
    container: { center: true, padding: "2rem", screens: { "2xl": "1400px" } },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
} satisfies Config;
```

---

## 2. Theming — CSS variables (HSL triplets) for light + dark

```css
/* src/index.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 240 10% 3.9%;
    --card: 0 0% 100%;
    --card-foreground: 240 10% 3.9%;
    --popover: 0 0% 100%;
    --popover-foreground: 240 10% 3.9%;
    --primary: 240 5.9% 10%;
    --primary-foreground: 0 0% 98%;
    --secondary: 240 4.8% 95.9%;
    --secondary-foreground: 240 5.9% 10%;
    --muted: 240 4.8% 95.9%;
    --muted-foreground: 240 3.8% 46.1%;
    --accent: 240 4.8% 95.9%;
    --accent-foreground: 240 5.9% 10%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 0 0% 98%;
    --border: 240 5.9% 90%;
    --input: 240 5.9% 90%;
    --ring: 240 10% 3.9%;
    --radius: 0.5rem;
  }
  .dark {
    --background: 240 10% 3.9%;
    --foreground: 0 0% 98%;
    --card: 240 10% 3.9%;
    --card-foreground: 0 0% 98%;
    --popover: 240 10% 3.9%;
    --popover-foreground: 0 0% 98%;
    --primary: 0 0% 98%;
    --primary-foreground: 240 5.9% 10%;
    --secondary: 240 3.7% 15.9%;
    --secondary-foreground: 0 0% 98%;
    --muted: 240 3.7% 15.9%;
    --muted-foreground: 240 5% 64.9%;
    --accent: 240 3.7% 15.9%;
    --accent-foreground: 0 0% 98%;
    --destructive: 0 62.8% 30.6%;
    --destructive-foreground: 0 0% 98%;
    --border: 240 3.7% 15.9%;
    --input: 240 3.7% 15.9%;
    --ring: 240 4.9% 83.9%;
  }
}

@layer base {
  * { @apply border-border; }
  body { @apply bg-background text-foreground; }
}
```

---

## 3. Canonical Form — RHF + zodResolver + shadcn Form primitives + React Query

```tsx
// src/components/signup-form.tsx
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Form, FormControl, FormDescription, FormField,
  FormItem, FormLabel, FormMessage,
} from "@/components/ui/form";

const signupSchema = z.object({
  email: z.string().email("Valid email required"),
  password: z.string().min(8, "At least 8 characters"),
  name: z.string().min(2, "Name required"),
});
type SignupValues = z.infer<typeof signupSchema>;

async function signup(values: SignupValues) {
  const res = await fetch("/api/auth/signup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(values),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<{ userId: string }>;
}

export function SignupForm() {
  const form = useForm<SignupValues>({
    resolver: zodResolver(signupSchema),
    defaultValues: { email: "", password: "", name: "" },
  });

  const mutation = useMutation({
    mutationFn: signup,
    onSuccess: () => form.reset(),
  });

  function onSubmit(values: SignupValues) {
    toast.promise(mutation.mutateAsync(values), {
      loading: "Creating your account...",
      success: "Welcome to Initiate Arena",
      error: (err) => `Signup failed: ${err.message}`,
    });
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Full name</FormLabel>
              <FormControl><Input placeholder="Antony Munoz" {...field} /></FormControl>
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
              <FormDescription>We only use this for account recovery.</FormDescription>
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
              <FormControl><Input type="password" {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <Button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "Creating..." : "Create account"}
        </Button>
      </form>
    </Form>
  );
}
```

Mount the sonner `<Toaster>` once at the app root:

```tsx
// src/main.tsx
import { Toaster } from "@/components/ui/sonner";

function App() {
  return (
    <>
      <Routes>{/* ... */}</Routes>
      <Toaster richColors position="top-right" />
    </>
  );
}
```

---

## 4. DataTable with TanStack Table v8

```tsx
// src/components/leads-table.tsx
import {
  ColumnDef, flexRender, getCoreRowModel,
  getPaginationRowModel, getSortedRowModel,
  SortingState, useReactTable,
} from "@tanstack/react-table";
import { useState } from "react";
import { ArrowUpDown, MoreHorizontal } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

type Lead = {
  id: string;
  name: string;
  email: string;
  stage: "cold" | "warm" | "hot";
  createdAt: string;
};

export const columns: ColumnDef<Lead>[] = [
  {
    accessorKey: "name",
    header: ({ column }) => (
      <Button
        variant="ghost"
        onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
      >
        Name <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
  },
  { accessorKey: "email", header: "Email" },
  { accessorKey: "stage", header: "Stage" },
  { accessorKey: "createdAt", header: "Created" },
  {
    id: "actions",
    cell: ({ row }) => (
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon">
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onSelect={() => console.log("edit", row.original.id)}>
            Edit
          </DropdownMenuItem>
          <DropdownMenuItem
            className="text-destructive"
            onSelect={(e) => {
              e.preventDefault(); // keep menu stable while confirm shows
              // open a Dialog controlled by parent state
            }}
          >
            Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    ),
  },
];

export function LeadsTable({ data }: { data: Lead[] }) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const table = useReactTable({
    data, columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: 20 } },
  });

  return (
    <div className="space-y-4">
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((hg) => (
              <TableRow key={hg.id}>
                {hg.headers.map((h) => (
                  <TableHead key={h.id}>
                    {h.isPlaceholder
                      ? null
                      : flexRender(h.column.columnDef.header, h.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id}>
                  {row.getVisibleCells().map((c) => (
                    <TableCell key={c.id}>
                      {flexRender(c.column.columnDef.cell, c.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center">
                  No leads yet.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      <div className="flex items-center justify-end space-x-2">
        <Button variant="outline" size="sm"
          onClick={() => table.previousPage()}
          disabled={!table.getCanPreviousPage()}>Previous</Button>
        <Button variant="outline" size="sm"
          onClick={() => table.nextPage()}
          disabled={!table.getCanNextPage()}>Next</Button>
      </div>
    </div>
  );
}
```

---

## 5. Dialog-in-Dialog (safe pattern)

Confirm deletion via a second Dialog opened from within an edit Dialog.

```tsx
import { useState } from "react";
import {
  Dialog, DialogContent, DialogFooter, DialogHeader,
  DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

export function EditLeadDialog({ lead }: { lead: { id: string; name: string } }) {
  const [editOpen, setEditOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  return (
    <>
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogTrigger asChild>
          <Button variant="outline">Edit</Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader><DialogTitle>Edit {lead.name}</DialogTitle></DialogHeader>
          {/* form fields */}
          <DialogFooter>
            <Button variant="destructive" onClick={() => setConfirmOpen(true)}>
              Delete
            </Button>
            <Button onClick={() => setEditOpen(false)}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Confirm lives at the SAME level — not nested inside EditDialog content */}
      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Delete {lead.name}?</DialogTitle></DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmOpen(false)}>Cancel</Button>
            <Button variant="destructive" onClick={() => {
              setConfirmOpen(false);
              setEditOpen(false);
              // mutation.mutate(lead.id)
            }}>Delete</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
```

Key insight: both Dialogs are siblings, not nested. Nesting them
inside each other's content trees causes focus trap races.

---

## 6. Custom CVA variant — extending the base Button

```tsx
// src/components/ui/brand-button.tsx
import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

const brandVariants = cva("", {
  variants: {
    intent: {
      luxury: "bg-gradient-to-r from-zinc-900 to-zinc-700 text-zinc-50 shadow-lg hover:shadow-xl",
      tactical: "bg-zinc-950 text-emerald-400 border border-emerald-500/30 font-mono uppercase tracking-wider",
      danger: "bg-red-950 text-red-200 border border-red-500/40 hover:bg-red-900",
    },
  },
  defaultVariants: { intent: "luxury" },
});

type BrandButtonProps = React.ComponentProps<typeof Button> &
  VariantProps<typeof brandVariants>;

export function BrandButton({ className, intent, ...props }: BrandButtonProps) {
  return (
    <Button
      {...props}
      className={cn(brandVariants({ intent }), className)}
    />
  );
}
```

Use it: `<BrandButton intent="tactical">Initiate</BrandButton>`.
Note the `cn()` call — it lets callers still pass `className` and
have tailwind-merge resolve any conflicts.

---

## 7. Vite ThemeProvider (dark mode without next-themes)

```tsx
// src/components/theme-provider.tsx
import { createContext, useContext, useEffect, useState } from "react";

type Theme = "dark" | "light" | "system";
type Ctx = { theme: Theme; setTheme: (t: Theme) => void };

const ThemeCtx = createContext<Ctx>({ theme: "system", setTheme: () => {} });

export function ThemeProvider({
  children, defaultTheme = "system", storageKey = "eos-theme",
}: {
  children: React.ReactNode; defaultTheme?: Theme; storageKey?: string;
}) {
  const [theme, setTheme] = useState<Theme>(
    () => (localStorage.getItem(storageKey) as Theme) || defaultTheme,
  );

  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove("light", "dark");
    if (theme === "system") {
      const sys = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
      root.classList.add(sys);
    } else {
      root.classList.add(theme);
    }
  }, [theme]);

  return (
    <ThemeCtx.Provider value={{
      theme,
      setTheme: (t) => { localStorage.setItem(storageKey, t); setTheme(t); },
    }}>
      {children}
    </ThemeCtx.Provider>
  );
}

export const useTheme = () => useContext(ThemeCtx);
```

Wire the toggle with a shadcn DropdownMenu:

```tsx
import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useTheme } from "@/components/theme-provider";

export function ThemeToggle() {
  const { setTheme } = useTheme();
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="icon">
          <Sun className="h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-[1.2rem] w-[1.2rem] rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => setTheme("light")}>Light</DropdownMenuItem>
        <DropdownMenuItem onClick={() => setTheme("dark")}>Dark</DropdownMenuItem>
        <DropdownMenuItem onClick={() => setTheme("system")}>System</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

---
