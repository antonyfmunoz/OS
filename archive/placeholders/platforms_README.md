# platforms/

## Purpose
Product layers consuming substrate intelligence — EOS, CreatorOS, LyfeOS, InvestorOS.

## Status: STAGING
Platform-specific code currently lives in:
- `eos_ai/platforms/eos/` — dormant EOS prototype (12 files)
- `saas/` — TypeScript/React SaaS product (separate build)

## Target Structure
```
platforms/
├── eos/             # EntrepreneurOS
├── creatoros/       # CreatorOS
├── lyfeos/         # LyfeOS
└── investoros/      # InvestorOS
```

## Rules
- Platforms consume substrate through defined contracts
- Platforms must NOT own substrate intelligence
- Platforms must NOT duplicate adapter or memory implementations
- Product-specific branding, feature flags, and workflows belong here

> Created: Phase 96.8BK — 2026-05-09
