# C24 Session 20: Build Test

Latency: 63154.6ms

The build actually **succeeded** â€” both Vite (client) and esbuild (server) completed without errors. The exit code 1 is just from a bash path-handling quirk with the space in "antonys beast pc", not from the build itself.

**Build output summary:**
- **Vite client build:** 3410 modules transformed, built in 10.64s
  - `index.html` â€” 5.85 kB
  - `assets/index-DGX3Ogwy.css` â€” 152.91 kB
  - `assets/index-D5vmNRqj.js` â€” 420.22 kB
- **esbuild server build:** `dist/index.js` â€” 549.9 kB, done in 26ms

No TypeScript errors. The only warning is that `caniuse-lite` browserslist data is 20 months old (cosmetic, not a build error).