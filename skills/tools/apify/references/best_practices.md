# Apify — Best Practices
Source: https://docs.apify.com/api/v2
Last Researched: 2026-04-01

## Compute Unit Credits
- Each actor run consumes compute units
- RESIDENTIAL proxy group has separate credit pool
- Monitor credit balance — 403 errors indicate depletion

## Best Practices (Official)
- Use dataset.iterate_items() for large results (streaming vs. bulk load)
- Set maxItems in run_input to avoid runaway scrapes
- Use actor versioning — pin to a specific version for stability
- Schedule runs via Apify scheduler rather than cron when possible

## Anti-Patterns (Official)
- Don't run actors in tight loops without checking credit balance
- Don't ignore run failures — check run status before accessing dataset
- Don't use shared API tokens across multiple services

## EOS Usage Patterns
- Comment scraping: run on cron, store signals in Neon signals table
- Proxy: enable only when direct access fails (INSTAGRAM_USE_PROXY=true)
- Result processing: iterate items → classify → insert to Neon

## Common Failures and Fixes
- 403 from proxy: RESIDENTIAL credits depleted — set INSTAGRAM_USE_PROXY=false
- Actor timeout: increase maxConcurrency or reduce batch size
- Empty dataset: target page changed structure — check actor version notes

## Version History
- 2026-03-XX: RESIDENTIAL 403 issue documented when credits depleted
