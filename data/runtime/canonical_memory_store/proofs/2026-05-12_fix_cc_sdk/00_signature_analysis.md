# Phase 0 — Error Signature Analysis

> Date: 2026-05-12

## Mechanism Confirmed

Line 169 of `runtime/cc_sdk.py` matches the diagnostic exactly:

```python
# lines 155-176
async def _stream() -> None:
    nonlocal model_used, result_session_id
    try:
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                model_used = getattr(message, "model", "")
                for block in message.content:
                    if isinstance(block, TextBlock):
                        output_parts.append(block.text)  # ← auth error text lands here
            elif isinstance(message, ResultMessage):
                if message.session_id:
                    result_session_id = message.session_id
                if message.result:
                    output_parts.append(message.result)
    except Exception as e:  # ← catches ProcessError after error text streamed
        logger.debug(...)
```

The Claude Agent SDK (v0.1.55) raises `ProcessError` when CLI
exits non-zero. Auth errors arrive as `AssistantMessage` with
`TextBlock` content BEFORE `ProcessError` propagates. The
catch-all suppresses the exception, and `output_parts` contains
the error message text.

## Error Text Shapes (from Anthropic API)

### Shape 1: Authentication / Credit Error (OBSERVED)

```
Failed to authenticate with the API. Your API key may be invalid,
expired, or revoked. Please check your API key and try again. If
you continue to experience issues, please contact
support@anthropic.com.

Error details:
  Type: authentication_error
  Status: 401
  Message: Your credit balance is too low to access the Anthropic
  API. Please go to Plans & Billing to upgrade or purchase credits.
```

~373 chars. Contains: "authentication_error", "credit balance",
"Failed to authenticate", "invalid".

### Shape 2: Rate Limit (429)

```
Rate limit exceeded. Please retry after X seconds.

Error details:
  Type: rate_limit_error
  Status: 429
```

Contains: "rate_limit_error", "Rate limit".

### Shape 3: Overloaded (529)

```
Anthropic API is temporarily overloaded.

Error details:
  Type: overloaded_error
  Status: 529
```

Contains: "overloaded_error".

### Shape 4: Invalid Request

```
Error details:
  Type: invalid_request_error
  Status: 400
```

Contains: "invalid_request_error".

## Legitimate Partial-Output Case (MUST NOT FLAG)

MCP server shutdown: CLI exits with code 1 after MCP server
disconnects, but valid LLM response was already streamed. The
`output_parts` contain the real model response (structured JSON,
analysis text, etc.) and NO error signatures. The catch-all
exists specifically for this case.

Distinguishing feature: legitimate partial output does NOT contain
Anthropic error type strings ("authentication_error",
"rate_limit_error", "overloaded_error", "invalid_request_error"),
does NOT start with "Failed to authenticate", and does NOT
contain "credit balance".

## Candidate Signatures

| # | Pattern | Confidence | Rationale |
|---|---------|-----------|-----------|
| 1 | `"authentication_error"` in text | **HIGH** | Anthropic error type enum. Never appears in valid LLM output. Exact match from model_router.py:571. |
| 2 | `"rate_limit_error"` in text | **HIGH** | Anthropic error type enum. Never in valid output. |
| 3 | `"overloaded_error"` in text | **HIGH** | Anthropic error type enum. Never in valid output. |
| 4 | `"invalid_request_error"` in text | **HIGH** | Anthropic error type enum. Never in valid output. |
| 5 | `"credit balance"` in text (case-insensitive) | **HIGH** | Specific Anthropic billing phrase. Matches model_router.py:569-570. |
| 6 | `"invalid x-api-key"` in text (case-insensitive) | **HIGH** | Anthropic key validation. Matches model_router.py:572. |
| 7 | text starts with `"Failed to authenticate"` | MEDIUM | Common but could theoretically appear as LLM analysis of auth systems. Lowered to MEDIUM because it's a natural English phrase. |
| 8 | `"Error details:\n  Type:"` in text | MEDIUM | Structured error format. Could appear if LLM quotes error formats. |

## V1 Signatures (HIGH confidence only)

Six signatures, all based on Anthropic API error type enums and
billing-specific phrases. These strings are machine-generated
identifiers that will never appear in valid LLM analysis output:

```python
_ERROR_SIGNATURES = (
    "authentication_error",
    "rate_limit_error",
    "overloaded_error",
    "invalid_request_error",
    "credit balance",
    "invalid x-api-key",
)
```

Match: case-insensitive substring search on the joined
`output_parts` text.

False positive risk: **negligible**. These are Anthropic API
error type enum values (snake_case identifiers) and specific
billing phrases. A legitimate LLM response analyzing auth
systems would use natural language ("authentication error",
not "authentication_error") and would not include
"credit balance" or "invalid x-api-key" verbatim.

False negative risk: **acceptable**. If Anthropic introduces
a new error type not in this list, cc_sdk will still leak it.
The fix is to add the new type. This is expected behavior for
a conservative allowlist.

## STOP Condition Check

- ✓ Line 169 matches diagnostic exactly
- ✓ 6 HIGH-confidence signatures defined
- ✓ Legitimate partial-output case will NOT be flagged

No STOP conditions triggered. Proceeding to Phase 1.
