# Radix UI — Anti-Patterns

Real failure modes from production React apps. Each entry has the
broken code, why it breaks, and the fix.

---

## 1. Wrapping Trigger in `<button>` instead of using `asChild`

```tsx
// WRONG — button-in-button, invalid HTML, double click events
<button className="my-button">
  <Dialog.Trigger>Open</Dialog.Trigger>
</button>
```

`Dialog.Trigger` already renders a `<button>`. Nesting it inside
another `<button>` is invalid HTML, breaks browser focus management,
and fires `onClick` twice.

```tsx
// RIGHT
<Dialog.Trigger asChild>
  <Button className="my-button">Open</Button>
</Dialog.Trigger>
```

Radix's Slot clones your `Button` and merges the trigger's props,
ARIA, and click handler onto it. One DOM element, all the behavior.

---

## 2. `asChild` with multiple children

```tsx
// WRONG — Slot uses React.Children.only
<DropdownMenu.Trigger asChild>
  <Icon />
  Menu
</DropdownMenu.Trigger>
```

Throws "React.Children.only expected to receive a single React
element child."

```tsx
// RIGHT
<DropdownMenu.Trigger asChild>
  <Button>
    <Icon /> Menu
  </Button>
</DropdownMenu.Trigger>
```

---

## 3. `asChild` with a child that doesn't `forwardRef`

```tsx
// WRONG — ref doesn't reach DOM, positioning + focus break
function Pill({ children, ...props }: any) {
  return <span {...props}>{children}</span>;
}

<Tooltip.Trigger asChild>
  <Pill>Hover me</Pill>
</Tooltip.Trigger>
```

Radix can't measure the trigger position because it can't get a ref.

```tsx
// RIGHT
const Pill = React.forwardRef<HTMLSpanElement, React.HTMLAttributes<HTMLSpanElement>>(
  ({ children, ...props }, ref) => (
    <span ref={ref} {...props}>{children}</span>
  ),
);
```

---

## 4. Closing the Dialog before the mutation finishes

```tsx
// WRONG — race condition; user sees empty list flash
const onSubmit = (values) => {
  setOpen(false);
  mutate(values);
};
```

```tsx
// RIGHT
const mutation = useMutation({
  mutationFn: api.create,
  onSuccess: () => {
    qc.invalidateQueries({ queryKey: ["leads"] });
    setOpen(false);
  },
});
```

---

## 5. `Select.Item value=""`

```tsx
// WRONG — runtime crash
<Select.Item value="">All</Select.Item>
```

```tsx
// RIGHT — sentinel
<Select.Item value="all">All</Select.Item>
// then in handler: const filter = v === "all" ? undefined : v;
```

---

## 6. `Dialog.Content` without `Dialog.Title`

```tsx
// WRONG — dev console warning, screen readers unannounced
<Dialog.Content>
  <p>Are you sure?</p>
</Dialog.Content>
```

```tsx
// RIGHT — visible title
<Dialog.Content>
  <Dialog.Title>Confirm</Dialog.Title>
  <p>Are you sure?</p>
</Dialog.Content>

// OR visually hidden title
<Dialog.Content>
  <VisuallyHidden><Dialog.Title>Confirm</Dialog.Title></VisuallyHidden>
  <p>Are you sure?</p>
</Dialog.Content>
```

---

## 7. Conditionally mounting the Dialog from the parent

```tsx
// WRONG — unmount races scroll-lock cleanup, body stays locked
{showDialog && (
  <Dialog open={true} onOpenChange={(o) => !o && setShowDialog(false)}>
    ...
  </Dialog>
)}
```

```tsx
// RIGHT — always mount, control via open
<Dialog open={showDialog} onOpenChange={setShowDialog}>...</Dialog>
```

---

## 8. Async / debounced `onOpenChange`

```tsx
// WRONG — pointer-events stuck on body
<Dialog
  open={open}
  onOpenChange={(o) => setTimeout(() => setOpen(o), 100)}
>
```

```tsx
// RIGHT — synchronous
<Dialog open={open} onOpenChange={setOpen}>
```

---

## 9. CheckboxItem closing the menu on every toggle

```tsx
// WRONG — menu closes; user can't toggle multiple
<DropdownMenu.CheckboxItem checked={a} onCheckedChange={setA}>
```

```tsx
// RIGHT — preventDefault keeps menu open
<DropdownMenu.CheckboxItem
  checked={a}
  onCheckedChange={setA}
  onSelect={(e) => e.preventDefault()}
>
```

---

## 10. Forgetting `TooltipProvider`

```tsx
// WRONG — tooltips silently no-op
<Tooltip>
  <TooltipTrigger asChild><Button /></TooltipTrigger>
  <TooltipContent>Hint</TooltipContent>
</Tooltip>
```

```tsx
// RIGHT — Provider once at app root
// app/layout.tsx
<TooltipProvider delayDuration={200}>
  {children}
</TooltipProvider>
```

---

## 11. Manually setting ARIA on Radix parts

```tsx
// WRONG — overrides Radix's wiring, breaks accessibility
<Dialog.Content role="dialog" aria-labelledby="my-title">
  <h2 id="my-title">Title</h2>
</Dialog.Content>
```

```tsx
// RIGHT — let Radix wire it via Title
<Dialog.Content>
  <Dialog.Title>Title</Dialog.Title>
</Dialog.Content>
```

---

## 12. Two versions of the same Radix primitive in one bundle

```bash
# WRONG — context collisions, mysterious "Dialog must be inside Root" errors
$ npm ls @radix-ui/react-dialog
├── @radix-ui/react-dialog@1.0.5
└─┬ some-other-lib@2.1.0
  └── @radix-ui/react-dialog@1.1.2
```

```bash
# RIGHT — dedupe
$ npm dedupe
$ npm ls @radix-ui/react-dialog  # only one entry
```

---

## 13. Putting Dialog inside a server component without `"use client"`

```tsx
// WRONG (Next.js App Router) — hydration mismatch from Portal
// app/leads/page.tsx
export default function LeadsPage() {
  return <CreateLeadDialog />;  // Dialog uses Portal → document.body
}
```

```tsx
// RIGHT
"use client";
// or render the dialog inside a child marked "use client"
```

---

## 14. Stacking custom z-index on top of shadcn defaults

```tsx
// WRONG — fights shadcn's z-50, hard to debug
<DialogContent style={{ zIndex: 9999 }}>
```

```tsx
// RIGHT — extend Tailwind's z scale once, use semantic tokens
// tailwind.config.ts
extend: { zIndex: { modal: "50", popover: "60", toast: "70" } }
// then className="z-popover" etc.
```
