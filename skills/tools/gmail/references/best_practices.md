# Gmail API — Official Best Practices
Source: https://developers.google.com/gmail/api/guides
Last Researched: 2026-04-01

## Rate Limits (per user per day)
- Read: 1,000,000,000 quota units/day (1B)
- Messages.list: 5 quota units per call
- Messages.get: 5 quota units per call
- Messages.send: 100 quota units per call
- Practical limit: ~250 sends/day before hitting daily limits

## Best Practices (Official)
- Use history.list for incremental sync rather than full inbox queries
- Request minimal fields using format=metadata when you don't need full body
- Always handle token expiry — refresh before making calls
- Use batch requests for multiple operations

## Anti-Patterns (Official)
- Don't poll messages.list in a tight loop — use push notifications or history API
- Don't store OAuth tokens in plaintext outside secure storage
- Don't send emails without founder approval — always queue for approval first

## EOS Usage Patterns
- Nightly review: scan unread, classify by type, surface in brief
- Draft pipeline: generate draft → write to orchestrator/approvals/ → founder approves → send
- Signal detection: scan for Calendly confirmations, lead replies, Stripe receipts

## Common Failures and Fixes
- Token expired: re-run gws auth flow — run `nlm login` or re-authorize GWS connector
- Rate limit: add sleep between requests if processing many emails in batch
- Missing scope: ensure gmail.modify scope is in OAuth consent

## Version History
- Gmail API v1 — stable
