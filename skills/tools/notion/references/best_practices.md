# Notion API — Official Best Practices
Source: https://developers.notion.com/
Last Researched: 2026-04-01

## Rate Limits
- 3 requests/second per integration
- Burst allowed but sustained rate must stay under limit
- 429 response means rate-limited — implement exponential backoff

## Best Practices (Official)
- Use database queries with filters rather than retrieving all pages
- Paginate with cursor — databases can have thousands of entries
- Cache page IDs — don't re-query for IDs you already have
- Use batch operations where possible
- Property names are case-sensitive in API calls

## Anti-Patterns (Official)
- Don't poll Notion for changes — use webhooks (or cron at reasonable intervals)
- Don't store secrets in Notion page content
- Don't create more integrations than needed — scope one integration per use case

## EOS Usage Patterns
- Daily brief: query tasks DB filtered by due_date = today
- CEO objective write: create page in tasks DB with status=active
- Pipeline update: update page properties on lead stage change

## Common Failures and Fixes
- 401 Unauthorized: NOTION_TOKEN missing or expired — check services/.env
- 404 on DB query: integration not added to that database in Notion UI
- Property not found: property name case mismatch — check exact DB schema

## Version History
- Notion API v1 — stable, no major breaking changes since 2022
