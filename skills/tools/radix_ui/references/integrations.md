# Radix UI — Integrations with EOS Stack

How Radix Primitives compose with the rest of the SaaS stack.

---

## React 18

Radix is fully React 18 strict-mode compatible. Internal effects clean
up correctly across the StrictMode double-mount, and Radix uses
`useSyncExternalStore` for cross-component state where needed (focus
stack, layer stack, scroll-lock reference counting).

- All Radix primitives can be safely rendered inside React 18
  `Suspense` boundaries.
- Concurrent rendering does not break Radix's focus management — focus
  trap activation runs in a layout effect, after commit.
- React 19 ref-as-prop migration is in progress internally; no
  consumer-facing API change.

---

## TypeScript

Every Radix primitive ships TypeScript types. The idiomatic
`forwardRef` wrapper pattern:

```tsx
const StyledContent = React.forwardRef<
  React.ElementRef<typeof Dialog.Content>,
  React.ComponentPropsWithoutRef<typeof Dialog.Content>
>(({ className, ...props }, ref) => (
  <Dialog.Content
    ref={ref}
    className={cn("...", className)}
    {...props}
  />
));
StyledContent.displayName = Dialog.Content.displayName;
```

`React.ElementRef<typeof X>` and `React.ComponentPropsWithoutRef<typeof X>`
are the canonical types — they pull from Radix's own definitions, so
your wrapper stays in sync across upgrades.

---

## shadcn/ui

shadcn IS Radix + Tailwind + `cn()` glued together. Every shadcn
component file in `components/ui/*.tsx` is a thin wrapper:

```tsx
// components/ui/dialog.tsx (shadcn-generated)
"use client";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { cn } from "@/lib/utils";

const Dialog = DialogPrimitive.Root;
const DialogTrigger = DialogPrimitive.Trigger;
const DialogPortal = DialogPrimitive.Portal;

const DialogOverlay = React.forwardRef<...>(({ className, ...props }, ref) => (
  <DialogPrimitive.Overlay
    ref={ref}
    className={cn("fixed inset-0 z-50 bg-black/80 ...", className)}
    {...props}
  />
));
// ...
```

**Rule:** edit `components/ui/*.tsx` only when changing the Tailwind
classes or adding props. Never edit it to change Radix behavior — go
to the source primitive instead.

When `npx shadcn add dialog` regenerates the file, it overwrites
unless you've made local edits Git tracks.

---

## Tailwind CSS + tailwindcss-animate

Radix exposes `data-state`, `data-side`, `data-align`, `data-orientation`,
`data-disabled`, `data-highlighted`, `data-checked`, `data-motion`.
Style with Tailwind data-attribute selectors:

```tsx
<DialogContent
  className="
    fixed left-[50%] top-[50%] z-50 grid w-full max-w-lg
    translate-x-[-50%] translate-y-[-50%] gap-4
    border bg-background p-6 shadow-lg
    data-[state=open]:animate-in
    data-[state=open]:fade-in-0
    data-[state=open]:zoom-in-95
    data-[state=closed]:animate-out
    data-[state=closed]:fade-out-0
    data-[state=closed]:zoom-out-95
    duration-200
  "
/>
```

`tailwindcss-animate` provides the `animate-in` / `animate-out` /
`fade-in-0` / `zoom-in-95` utilities. Install once at the SaaS root:

```bash
npm i -D tailwindcss-animate
```

```ts
// tailwind.config.ts
import animate from "tailwindcss-animate";
export default { plugins: [animate], ... };
```

---

## React Hook Form + Zod

The canonical EOS form-in-Dialog pattern:

```tsx
const form = useForm<FormValues>({
  resolver: zodResolver(schema),
  defaultValues: { ... },
});

<Dialog open={open} onOpenChange={setOpen}>
  <DialogContent>
    <form onSubmit={form.handleSubmit((v) => mutation.mutate(v))}>
      <Input {...form.register("name")} />
      <Button type="submit">Save</Button>
    </form>
  </DialogContent>
</Dialog>
```

Reset on close (so reopening doesn't show stale data):

```tsx
<Dialog open={open} onOpenChange={(o) => {
  setOpen(o);
  if (!o) form.reset();
}}>
```

---

## Sonner (toasts)

We use Sonner instead of `@radix-ui/react-toast`. Mount once at the
root:

```tsx
// app/layout.tsx
import { Toaster } from "sonner";
<body>
  {children}
  <Toaster position="top-right" richColors closeButton />
</body>
```

Then `import { toast } from "sonner"` anywhere.

**Why not Radix Toast:** Sonner stacks better, smaller bundle,
official shadcn recommendation, and Radix Toast is in maintenance
mode.

---

## TanStack Query

Mutation→close pattern (used in every form Dialog):

```tsx
const mutation = useMutation({
  mutationFn: api.create,
  onSuccess: () => {
    qc.invalidateQueries({ queryKey: ["leads"] });
    setOpen(false);
    toast.success("Lead created");
  },
  onError: (e) => toast.error(e.message),
});
```

Close ONLY on `onSuccess`. Never close optimistically — the user needs
to see errors inside the dialog.

For optimistic UI (rare), use Query's `onMutate` to update the cache,
then `onError` to roll back, but still close on `onSuccess`.

---

## TanStack Table inside a Dialog

Common pattern: pick-one selection from a large list inside a Dialog.

```tsx
<Dialog open={open} onOpenChange={setOpen}>
  <DialogContent className="max-w-3xl">
    <DialogHeader>
      <DialogTitle>Pick a campaign</DialogTitle>
    </DialogHeader>
    <ScrollArea className="h-[400px]">
      <DataTable columns={campaignColumns} data={campaigns}
        onRowClick={(row) => {
          onPick(row.original);
          setOpen(false);
        }}
      />
    </ScrollArea>
  </DialogContent>
</Dialog>
```

`ScrollArea` is `@radix-ui/react-scroll-area` — gives you styled
scrollbars without losing keyboard / screen-reader scrolling.

---

## Next.js App Router

- Mark any component using a Radix `Portal`-based primitive (Dialog,
  Popover, DropdownMenu, Select, Tooltip, AlertDialog, ContextMenu,
  HoverCard, Toast) as `"use client"`.
- Server components can pass children INTO client Dialog wrappers,
  keeping the body server-rendered:

```tsx
// app/leads/[id]/page.tsx (server component)
export default async function LeadPage({ params }) {
  const lead = await getLead(params.id);
  return (
    <LeadDialogClient>
      <LeadDetail lead={lead} />  {/* server-rendered */}
    </LeadDialogClient>
  );
}
```

```tsx
// LeadDialogClient.tsx
"use client";
export function LeadDialogClient({ children }: { children: React.ReactNode }) {
  return (
    <Dialog defaultOpen>
      <DialogContent>{children}</DialogContent>
    </Dialog>
  );
}
```

---

## cmdk (Command palette)

`cmdk` by Paco Coursey is designed to compose with Radix Dialog and
Popover. shadcn's `Command` and `CommandDialog` components are this
composition:

```tsx
import { CommandDialog, CommandInput, CommandList, CommandItem } from "@/components/ui/command";

<CommandDialog open={open} onOpenChange={setOpen}>
  <CommandInput placeholder="Type a command..." />
  <CommandList>
    <CommandItem onSelect={() => navigate("/leads")}>
      Go to Leads
    </CommandItem>
  </CommandList>
</CommandDialog>
```

Under the hood: Radix Dialog provides the modal shell + focus trap;
cmdk provides the keyboard nav + filter engine.

---

## Floating UI (under the hood)

Radix Popover, DropdownMenu, Select, Tooltip, HoverCard, ContextMenu,
NavigationMenu all use `@floating-ui/react-dom` for positioning. You
get its middleware for free via Radix props:

- `side`, `sideOffset`, `align`, `alignOffset` → flip + shift
- `avoidCollisions` (default true) → flip middleware
- `collisionBoundary` → which element bounds the flip
- `collisionPadding` → padding inside the boundary
- `sticky` → stick to a side
- `hideWhenDetached` → hide when reference is offscreen

You should NOT import `@floating-ui/react-dom` directly unless
building a custom positioned primitive.

---

## Compatibility table

| Tool | Version | Compatible | Notes |
|---|---|---|---|
| React | 16.8+ / 17 / 18 / 19 | Yes | EOS uses 18 strict |
| Next.js | 13 / 14 / 15 | Yes | App Router needs `"use client"` |
| TypeScript | 4.7+ | Yes | 5.x recommended |
| Tailwind CSS | 3.x | Yes | Use `tailwindcss-animate` |
| shadcn/ui | latest | Yes | Native composition |
| React Hook Form | 7.x | Yes | Standard form layer |
| Zod | 3.x | Yes | Standard schema layer |
| TanStack Query | 5.x | Yes | Mutation→close pattern |
| TanStack Table | 8.x | Yes | Render inside Dialog |
| Sonner | 1.x | Yes | Replaces Radix Toast |
| cmdk | latest | Yes | Composes with Dialog |
| Framer Motion | 11.x | Yes but unnecessary | Prefer tailwindcss-animate |
| Material UI | any | NO | Focus management conflict |
| Bootstrap modals | any | NO | DOM mutation conflict |
| React Aria | any | NOT in same component | Different focus strategies |
