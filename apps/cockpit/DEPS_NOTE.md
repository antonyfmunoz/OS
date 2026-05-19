# Dependency Pins — 2026-05-20

Three packages pinned to stable versions because their latest majors
ship broken or missing type declarations under `moduleResolution: "bundler"`.

| Package | Pinned | Bleeding-edge | Issue |
|---------|--------|---------------|-------|
| `vite` | `^7.3.3` | 8.x | Vite 8 stripped `types` from `exports["."]` — no `.d.ts` in tarball |
| `@vitejs/plugin-react` | `^5.2.0` | 6.x | Matched to Vite 7; 6.x ships no types in exports |
| `lucide-react` | `^0.472.0` | 1.x | `typings` field points to nonexistent file; no `exports` map |

## When to unpin

Bump back when upstream ships proper `exports.types` conditions:
- Vite 8: track https://github.com/vitejs/vite/issues — look for "types" in release notes
- lucide-react: track https://github.com/lucide-icons/lucide/issues — `exports` map addition

<!-- TODO(2026-05-20): check quarterly if upstream has fixed type exports -->
