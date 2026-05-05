# Google Workspace Core Foundation Package (W-GWS-CORE-001)

**Version:** v1
**Date:** 2026-05-05
**Package ID:** W-GWS-CORE-001
**Status:** Mature (W0-001 scope)

## Purpose

Shared foundation for all Google Workspace service adapter packages.
Provides auth, governance, no-secret policy, and rate limit doctrine
that all service packages inherit.

## Shared Auth Models

| Auth Model | Status |
|-----------|--------|
| OAUTH_USER_CONSENT_OPAQUE_TOKEN_CACHE | Active (W0-001) |
| BROWSER_PROFILE_SESSION_AUTH_CANDIDATE | Candidate (CU) |
| SERVICE_ACCOUNT_DOMAIN_WIDE_DELEGATION_FUTURE | Future |

## No-Secret Policy

- No credential capture
- No token reading
- No cookie reading
- No API key capture
- No secret logging
- Auth token opaque

## Shared Governance Defaults

- Read-only default
- No mutation unless approved
- No export unless approved
- No download unless approved
- No permission changes
- No account switching unless approved
- Instance scope preservation
- No memory promotion
- No global canon write

## Rate Limit Doctrine

- Respect Google API quota
- Exponential backoff on 429
- Per-service rate awareness
- No bulk scraping

## Scope Limitation

This core package is mature for the W0-001 shared Drive/Docs foundation.
It does **NOT** imply:
- Gmail maturity
- Sheets maturity
- Slides maturity
- Calendar maturity

## Module

`core/adapter_package_manager/google_workspace_core_package.py`
