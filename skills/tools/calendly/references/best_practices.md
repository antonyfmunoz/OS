# Calendly API — Best Practices
Source: https://developer.calendly.com/api-docs
Last Researched: 2026-04-01

## Webhook Events
- invitee.created: fires when a booking is confirmed
- invitee.canceled: fires when a booking is cancelled
- Payload includes: invitee email, name, event time, event type, questions/answers

## Signature Verification
- Every webhook includes Calendly-Webhook-Signature header
- Verify using HMAC-SHA256 with signing key
- ALWAYS verify before processing — reject unverified requests

## Retry Behavior
- Calendly retries failed webhooks up to 7 times with exponential backoff
- Return 2xx within 10 seconds or Calendly considers it failed
- Idempotency: handle duplicate deliveries (same event_uuid may arrive twice)

## Best Practices (Official)
- Return 200 immediately, process async
- Verify signature on every request
- Store event_uuid to deduplicate retries
- Log all webhook events for debugging

## EOS Usage Patterns
- Booking trigger: create lead record → notify DEX → update Notion CRM
- Cancellation: update lead status → notify DEX → remove from calendar
- Pre-call research: booking triggers pre_call_research_brief skill

## Common Failures and Fixes
- Signature mismatch: signing key changed in Calendly dashboard — update services/.env
- Webhook not received: verify os-webhook service is running, port 8080 is accessible
- Duplicate processing: check event_uuid before inserting lead record

## Version History
- Calendly API v2 — stable
