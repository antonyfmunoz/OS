# React — Anti-Patterns

Real failure modes that show up in EOS SaaS code. Each entry:
the bad pattern, why it fails, the fix.

---

## 1. Fetching data in `useEffect`

**Bad:**
```tsx
const [leads, setLeads] = useState<Lead[]>([]);
useEffect(() => {
  fetch("/api/leads").then((r) => r.json()).then(setLeads);
}, []);
```

**Why it fails:** no caching, no dedup, no retry, no invalidation,
no loading/error states, races on unmount, double-fetches in Strict
Mode, refetches on every mount.

**Fix:** React Query.
```tsx
const { data: leads = [] } = useQuery({
  queryKey: ["leads"],
  queryFn: () => fetch("/api/leads").then((r) => r.json()),
});
```

---

## 2. Deriving state from props with `useEffect`

**Bad:**
```tsx
const [fullName, setFullName] = useState("");
useEffect(() => {
  setFullName(`${first} ${last}`);
}, [first, last]);
```

**Why it fails:** extra render, stale intermediate state, sync bugs.

**Fix:** compute during render.
```tsx
const fullName = `${first} ${last}`;
```

---

## 3. Copying props into `useState`

**Bad:**
```tsx
function Editor({ initialValue }: { initialValue: string }) {
  const [value, setValue] = useState(initialValue);
  // never updates when initialValue changes later
}
```

**Fix:** if you truly want the child to reset on parent change, use `key`:
```tsx
<Editor key={leadId} initialValue={lead.notes} />
```
Otherwise lift state up or accept `value` + `onChange`.

---

## 4. Array index as `key`

**Bad:**
```tsx
{items.map((item, i) => <Row key={i} item={item} />)}
```

**Why it fails:** on reorder/insert/delete, React reuses DOM for the
wrong item. Focus, input values, animation state attach to the wrong row.

**Fix:** use a stable id.
```tsx
{items.map((item) => <Row key={item.id} item={item} />)}
```

---

## 5. Stale closure in event handler or effect

**Bad:**
```tsx
const [count, setCount] = useState(0);
useEffect(() => {
  const id = setInterval(() => setCount(count + 1), 1000);
  return () => clearInterval(id);
}, []); // count captured at mount — always 0 + 1
```

**Fix:** functional updater.
```tsx
setInterval(() => setCount((c) => c + 1), 1000);
```

---

## 6. Object/array literal in deps or props

**Bad:**
```tsx
useEffect(() => { sync({ id }); }, [{ id }]); // new object every render
<Child options={{ sort: "asc" }} />;           // new reference every render
```

**Fix:** memoize or lift out.
```tsx
const options = useMemo(() => ({ sort: "asc" }), []);
```

---

## 7. Over-memoization

**Bad:**
```tsx
const name = useMemo(() => `${first} ${last}`, [first, last]);
const onClick = useCallback(() => console.log("hi"), []);
```

**Why it fails:** `useMemo`/`useCallback` have their own cost. For
cheap computations and non-memoized children they're net negative.

**Fix:** memoize only when profiling shows a hot path OR when the
value is a dep of another memoized thing.

---

## 8. Huge context values

**Bad:**
```tsx
<AppContext.Provider value={{ user, theme, leads, notifications, ... }}>
```

**Why it fails:** any change to any field re-renders every consumer.

**Fix:** split providers by update frequency, use a selector library
(`use-context-selector`), or move server state to React Query and
keep context for rarely-changing values only.

---

## 9. Defining a component inside another component

**Bad:**
```tsx
function Page() {
  const Row = ({ item }) => <li>{item}</li>; // new component every render
  return <ul>{items.map(Row)}</ul>;
}
```

**Why it fails:** React sees a new component type every render, so it
unmounts and remounts the entire list. State and focus lost. Forms
lose focus on every keystroke.

**Fix:** move the inner component to module scope.

---

## 10. Mutating state

**Bad:**
```tsx
state.items.push(newItem);
setState(state);
```

**Why it fails:** React compares by reference. Mutated state is `===`
the old state, so React skips the re-render.

**Fix:** produce new references.
```tsx
setState({ ...state, items: [...state.items, newItem] });
```

---

## 11. Disabling the exhaustive-deps lint

**Bad:**
```tsx
useEffect(() => {
  doThing(id);
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, []);
```

**Why it fails:** the warning exists to catch stale closures. 95% of
silenced warnings become real bugs.

**Fix:** include the dep, or move the value into a `useRef` if you
truly want "latest without re-running."

---

## 12. `setState` during render

**Bad:**
```tsx
function Component({ value }) {
  const [prev, setPrev] = useState(value);
  if (value !== prev) setPrev(value); // fine ONLY in this exact pattern
  // worse:
  setPrev(computeSomething()); // infinite loop
}
```

**Fix:** update state in event handlers or effects, never unconditionally during render.

---

## 13. Using `useRef` when you need to re-render

**Bad:**
```tsx
const count = useRef(0);
return <button onClick={() => (count.current += 1)}>{count.current}</button>;
```

**Why it fails:** ref mutation doesn't trigger re-render; UI stays at 0.

**Fix:** `useState` for values that affect the UI.

---

## 14. Forgetting cleanup

**Bad:**
```tsx
useEffect(() => {
  window.addEventListener("resize", onResize);
}, []);
```

**Why it fails:** listener leaks on unmount; duplicated on Strict Mode remount.

**Fix:**
```tsx
useEffect(() => {
  window.addEventListener("resize", onResize);
  return () => window.removeEventListener("resize", onResize);
}, [onResize]);
```

---

## 15. (React 19) Creating the promise for `use()` inside render

**Bad:**
```tsx
function Comments() {
  const comments = use(fetch("/api/comments").then((r) => r.json()));
  return <ul>...</ul>;
}
```

**Why it fails:** every render creates a brand-new promise, which
`use()` suspends on, which triggers another render, which creates
another promise. Infinite suspension, never resolves.

**Fix:** the promise must come from a cache owned outside render — a
loader, a parent component, a Server Component, or a query library.

```tsx
const commentsPromise = fetchComments(); // module scope, or from a loader
function Comments() {
  const comments = use(commentsPromise);
  return <ul>...</ul>;
}
```

In EOS, use `useSuspenseQuery` from TanStack Query instead of calling
`use()` with hand-rolled promises.

---

## 16. (React 19) Mixing `forwardRef` and ref-as-prop in the same file

**Bad:**
```tsx
const OldInput = forwardRef<HTMLInputElement, Props>((p, ref) => ...);
function NewInput({ ref, ...rest }: Props & { ref?: Ref<HTMLInputElement> }) { ... }
// Wrapper spreads props AFTER ref:
function Wrapper(props: Props & { ref?: Ref<HTMLInputElement> }) {
  return <OldInput ref={props.ref} {...props} />; // props.ref gets clobbered
}
```

**Why it fails:** `ref` is now a regular prop, so spread order matters.
Also, a `ForwardRef`-wrapped component with a `ref` prop makes its
props referentially unstable, which kills downstream memoization.

**Fix:** run the codemod across the whole file at once. Pick one
convention. Never interleave.

---

## 17. (React 19) Using Actions inside a Server Component boundary

**Bad:**
```tsx
// In a Server Component file
"use server";
export default function Page() {
  const [state, action, pending] = useActionState(...); // hooks forbidden in SC
}
```

**Why it fails:** hooks only run in Client Components. Server
Components cannot call `useActionState` — they define the action and
pass it down to a Client Component that consumes it.

**Fix:** mark the consumer with `"use client"` and pass the server
action down as a prop.

---

## 18. (React 19) Mixing React Compiler with manual memoization

**Bad:**
```tsx
// With reactCompiler: true enabled
function Chart({ data }) {
  const sorted = useMemo(() => data.slice().sort(), [data]); // double memo
  const onClick = useCallback(() => {}, []); // compiler already did this
  return <Canvas data={sorted} onClick={onClick} />;
}
```

**Why it fails:** not broken, just wasteful. The compiler already
inserted memoization; your manual hooks add another layer of
bookkeeping the compiler can't remove.

**Fix:** in a compiled codebase, drop manual `useMemo`/`useCallback`
from new code. Use the `"use no memo"` file directive to opt a
specific file out of the compiler if you need precise control for
profiling.

---

## 19. Mixing controlled and uncontrolled inputs

**Bad:**
```tsx
<input value={value} />         // no onChange — read-only, warns
<input defaultValue={value} onChange={...} />  // switching between undefined and string
```

**Fix:** either fully controlled (`value` + `onChange`) or fully
uncontrolled (`defaultValue` + ref). Never mix. React Hook Form uses
uncontrolled by default — embrace it.
