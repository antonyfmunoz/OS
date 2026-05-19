# Three-State Discipline

Every UI element representing an operation or data fetch MUST handle
three explicit states:

1. **Loading** — the operation is in progress
2. **Failure** — the operation failed (with reason)
3. **Success** — the operation completed (with data)

Anything less is a broken interface.

## Enforcement

Components consume `UMHViewState<T>` from `apps/cockpit/src/lib/state.ts`.
This discriminated union makes it impossible to render data without first
handling loading and failure — the TypeScript compiler enforces it.

```typescript
type UMHViewState<T> =
  | { status: 'loading' }
  | { status: 'error'; error: string }
  | { status: 'ready'; data: T }
```

## Patterns

### Correct
```tsx
function MyView({ state }: { state: UMHViewState<Dashboard> }) {
  if (state.status === 'loading') return <Spinner />
  if (state.status === 'error') return <ErrorBanner message={state.error} />
  return <DashboardView data={state.data} />
}
```

### Incorrect
```tsx
// BROKEN: no loading state, no error state
function MyView({ data }: { data: Dashboard | null }) {
  if (!data) return null  // silent failure
  return <DashboardView data={data} />
}
```

## Scope

- Enforced on all new components from this point forward
- Existing components get retrofitted in Phase 2
- Design system tokens: `bg-surface` for loading shimmer,
  `text-danger` for error messages, standard layout preserved on failure

## Design Tokens

| State | Background | Text | Border |
|-------|-----------|------|--------|
| Loading | `bg-surface` shimmer | `text-text-tertiary` | `border-border` |
| Failure | `bg-surface` | `text-danger` | `border-danger/30` |
| Success | `bg-surface` | `text-text-primary` | `border-border` |
