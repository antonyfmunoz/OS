# Postmortem — agent_runtime._call_with_retry
**Date:** 2026-03-25
**Component:** agent_runtime._call_with_retry

---

**Failure:** API call exhausted all 4 retries

---

## Timeline

1. **T-0s**: agent_runtime._call_with_retry initiates API call with current authentication credentials
2. **T-1s**: First attempt fails with 401 authentication_error (request_id: req_011CZNMQSKDWFCuzY)
3. **T-2s through T-8s**: Retry loop executes 3 additional attempts with identical credentials; all 4 requests fail with 401
4. **T-9s**: Retry budget exhausted; exception propagates up; operation fails

The retry mechanism correctly identified a non-transient error (authentication) and attempted recovery via retry, but the underlying credential state was invalid for all attempts.

## Root Cause

API credentials in the runtime environment are expired, revoked, or incorrectly configured. The agent loaded stale/invalid credentials at startup and reused them across all 4 retry attempts without refresh or validation. This is a credential *staleness* issue, not a transient network failure—retrying with the same invalid token cannot succeed.

## Fix

Add credential refresh before retry exhaustion in `agent_runtime._call_with_retry`:

```python
def _call_with_retry(self, api_call, max_retries=4):
    for attempt in range(max_retries):
        try:
            return api_call()
        except APIError as e:
            if e.status_code == 401 and attempt == 0:
                # First 401: refresh credentials and retry once
                self.auth_manager.refresh_credentials()
                continue
            elif e.status_code == 401:
                # Second 401 after refresh: credential issue is real, fail fast
                raise AuthenticationError(f"Invalid credentials after refresh: {e.message}")
            elif attempt < max_retries - 1:
                continue
            else:
                raise
```

Immediately restart the runtime to load fresh credentials from your credential store (environment, vault, or IAM service).

## Prevention

**Add: Credential expiration monitoring and auto-refresh gate**

Implement a pre-flight credential validation check that runs on agent startup and every 30 minutes during idle time:

```python
class CredentialHealthCheck:
    def validate_and_refresh(self):
        """Check if credentials are valid; refresh if near expiration."""
        token_ttl = self.auth_manager.get_token_ttl()
        if token_ttl < 300:  # Less than 5 minutes remaining
            self.auth_manager.refresh_credentials()
            return True
        return False
```

Gate agent readiness on this check returning True. Log any 401s with credential metadata (expiration time, issuer) to a dedicated auth_failures metric. Alert when 401 error rate exceeds 1% in a 5-minute window.