# shadcn/ui — Anti-Patterns

Real failure modes observed in shadcn/ui GitHub issues, Stack Overflow,
and the EOS codebase. Every entry is: wrong code → why it fails → fix.

---

## 1. Editing vendored components then re-running `shadcn add`

**Wrong:**
```bash
# You edit src/components/ui/button.tsx to add a "luxury" variant.
# Weeks later you want a new Radix update.
$ npx shadcn@latest add button
# Prompt: "button.tsx exists. Overwrite? (y/N)"
$ y
# Your "luxury" variant is gone.
```

**Why:** the CLI is a code generator, not a merger. It will happily
overwrite.

**Fix:**
```bash
# 1. Always commit first.
git add -A && git commit -m "wip: pre-shadcn-update"

# 2. See the drift before blindly overwriting.
npx shadcn@latest diff button

# 3. Overwrite, then reapply edits from git diff.
npx shadcn@latest add button --overwrite
git diff src/components/ui/button.tsx
# Cherry-pick your edits back in.
```

Better: extend Button in a SEPARATE file (e.g.,
`src/components/ui/brand-button.tsx`) so upstream updates never
touch your branded variants.

---

## 2. Skipping `cn()` in component wrappers

**Wrong:**
```tsx
function Card({ className, ...props }: React.ComponentProps<"div">) {
  return <div className={"rounded-lg border p-4 " + className} {...props} />;
}

// Caller:
<Card className="p-8">...</Card>
// Result: className="rounded-lg border p-4 p-8"
// Both p-4 and p-8 emit CSS rules; actual padding depends on CSS source order.
```

**Why:** string concat does not merge conflicting Tailwind utilities.

**Fix:**
```tsx
import { cn } from "@/lib/utils";

function Card({ className, ...props }: React.ComponentProps<"div">) {
  return <div className={cn("rounded-lg border p-4", className)} {...props} />;
}
// Now p-8 cleanly overrides p-4 (tailwind-merge drops the loser).
```

---

## 3. Forgetting `asChild` on Radix triggers

**Wrong:**
```tsx
<DialogTrigger>
  <Button>Open</Button>
</DialogTrigger>
// Renders: <button type="button"><button>Open</button></button>
// Invalid HTML. Breaks keyboard nav. Fails a11y audits.
```

**Fix:**
```tsx
<DialogTrigger asChild>
  <Button>Open</Button>
</DialogTrigger>
// Renders: <button type="button" ...triggerProps>Open</button>
```

Applies to every Radix trigger: `DialogTrigger`, `PopoverTrigger`,
`DropdownMenuTrigger`, `SelectTrigger`, `TooltipTrigger`, `SheetTrigger`,
`DrawerTrigger`, `HoverCardTrigger`, `CollapsibleTrigger`.

---

## 4. Dialog inside DropdownMenuItem without `preventDefault`

**Wrong:**
```tsx
<DropdownMenu>
  <DropdownMenuTrigger asChild><Button>Menu</Button></DropdownMenuTrigger>
  <DropdownMenuContent>
    <DropdownMenuItem>
      <Dialog>
        <DialogTrigger>Delete</DialogTrigger>
        <DialogContent>...</DialogContent>
      </Dialog>
    </DropdownMenuItem>
  </DropdownMenuContent>
</DropdownMenu>
// Click "Delete": DropdownMenu closes, DialogContent unmounts mid-open, flash.
```

**Fix A (recommended):** lift state out, render Dialog at page level.
```tsx
const [open, setOpen] = useState(false);

<DropdownMenu>
  <DropdownMenuContent>
    <DropdownMenuItem onSelect={() => setOpen(true)}>Delete</DropdownMenuItem>
  </DropdownMenuContent>
</DropdownMenu>
<Dialog open={open} onOpenChange={setOpen}>
  <DialogContent>...</DialogContent>
</Dialog>
```

**Fix B:** prevent the menu from closing.
```tsx
<DropdownMenuItem onSelect={(e) => e.preventDefault()}>
  <Dialog>...</Dialog>
</DropdownMenuItem>
```

---

## 5. Variant explosion — new variant for every one-off

**Wrong:**
```ts
const buttonVariants = cva("...", {
  variants: {
    variant: {
      default: "...", destructive: "...", outline: "...",
      ghost: "...", link: "...",
      luxury: "...", tactical: "...", gradient: "...",
      neon: "...", minimal: "...", brutal: "...",
      // 20 more for one-off pages
    },
    size: { xs: "...", sm: "...", md: "...", lg: "...", xl: "...", "2xl": "..." },
    state: { idle: "...", loading: "...", success: "...", error: "..." },
  },
});
// 20 × 6 × 4 = 480 class permutations JIT-compiles into your bundle.
```

**Fix:** keep `variant` to a small, reusable set. One-off styles go
in a separate component OR via `className` override with `cn()`.
```tsx
<Button className="bg-gradient-to-r from-fuchsia-500 to-cyan-400">
  Weird one-off
</Button>
```

Rule of thumb: if you use a variant in 3+ places, it's a variant.
Otherwise, it's an override.

---

## 6. Mixing Default and New York styles in one repo

**Wrong:**
```bash
# Month 1
$ shadcn init  # pick "default"
$ shadcn add button input

# Month 3
$ # Change components.json: "style": "new-york"
$ shadcn add dialog
# Now button.tsx is Default, dialog.tsx is New York.
# Spacing, icon sizing, corner radii all subtly differ.
```

**Why:** the two styles pull from different registry paths and have
different conventions (New York is denser with stronger shadows).

**Fix:** pick ONE at `init` and commit to it. If you want to switch,
do a full migration: `shadcn add --all --overwrite`, then reapply
your custom edits.

---

## 7. Manually installing `@radix-ui/react-*` packages

**Wrong:**
```bash
$ npm i @radix-ui/react-dialog
$ # write my own wrapper component
```

**Why:** you lose the styling contract. Your wrapper doesn't match
the rest of your UI. You've duplicated work shadcn already did.

**Fix:**
```bash
$ npx shadcn@latest add dialog
# Gets the Radix Dialog + shadcn's styled wrapper + peer deps.
```

The ONLY reason to install Radix manually is if no shadcn wrapper
exists for the primitive you need.

---

## 8. Using legacy `useToast` in new code

**Wrong:**
```tsx
// Old shadcn recipe
import { useToast } from "@/components/ui/use-toast";
const { toast } = useToast();
toast({ title: "Saved", description: "Your changes are live." });
```

**Why:** the legacy `useToast` + `<Toaster>` is being phased out.
shadcn's docs now show sonner in every example.

**Fix:**
```bash
$ npx shadcn@latest add sonner
```
```tsx
import { toast } from "sonner";
toast.success("Saved", { description: "Your changes are live." });

// Even better — toast.promise for async ops
toast.promise(saveLead(data), {
  loading: "Saving...",
  success: "Lead saved",
  error: (e) => `Failed: ${e.message}`,
});
```

---

## 9. Theming by editing component files

**Wrong:** you want a "luxury" brand so you open
`src/components/ui/button.tsx` and rewrite every class to gold and
black. Then you do the same for Card, Dialog, Input...

**Why:** you just made every future `shadcn add` update destructive.
The WHOLE point of CSS variables is to avoid this.

**Fix:** change the variables, not the components.
```css
:root {
  --primary: 45 100% 50%;         /* gold */
  --primary-foreground: 0 0% 0%;  /* black */
  --radius: 0.125rem;             /* tighter corners for "luxury" feel */
}
```
Every component using `bg-primary` / `text-primary-foreground` /
`rounded-lg` now reflects your brand automatically.

---

## 10. Relying on tsconfig `paths` alone (Vite / Rollup)

**Wrong:**
```json
// tsconfig.json
{ "compilerOptions": { "paths": { "@/*": ["./src/*"] } } }
```
```ts
// vite.config.ts — NO resolve.alias
export default defineConfig({ plugins: [react()] });
```

**Symptom:** `npm run dev` works (TS handles paths); `npm run build`
fails: `Could not resolve "@/components/ui/button"`.

**Why:** TypeScript uses `paths` for type checking only. Vite/Rollup
don't read tsconfig at runtime.

**Fix A:** mirror in `vite.config.ts`.
```ts
import path from "node:path";
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
});
```

**Fix B:** use `vite-tsconfig-paths` so tsconfig is the single source.
```bash
npm i -D vite-tsconfig-paths
```
```ts
import tsconfigPaths from "vite-tsconfig-paths";
export default defineConfig({ plugins: [react(), tsconfigPaths()] });
```

Keep `components.json aliases`, `tsconfig paths`, and vite alias in
sync — all three must agree.

---
