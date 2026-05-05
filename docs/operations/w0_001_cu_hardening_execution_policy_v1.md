# W0-001 CU Hardening Execution Policy v1

## Purpose

Defines when and how CU hardening tests can execute for the W0-001
package set. CU hardening is gated by environment probe results and
governance constraints.

## Environment Requirements

CU hardening requires a Windows desktop with:
1. Visible Chrome browser session (not headless)
2. Chrome accessibility mode enabled
3. Correct Google account signed in
4. Google Drive accessible in browser
5. Google Docs openable from Drive

A Linux VPS cannot execute CU hardening — the CU execution probe
returns NO_VISIBLE_SESSION and blocks all CU work.

## Execution Levels

### Hardening Test (lower bar)
- Visible session available
- UI access available
- Governance safe (no mutation, no credentials, no screenshots)
- Does NOT require account confirmation or extraction proof

### Production Parity Test (higher bar)
- All hardening requirements PLUS:
- Account confirmed as correct Google account
- Drive visible and navigable
- Docs openable
- Extraction available (foreground ownership solved)

## Current State

- Drive CU (W-GDRIVE-CU-001): 100% — all hardening complete
- Docs CU (W-GDOCS-CU-001): 56.2% — 7 gaps, content extraction blocked
- CU Slice: HARDENING_READY (governance passes, not fully mature)

## Governance Constraints (non-negotiable)

- No file creation, modification, or deletion
- No credential capture or storage
- No screenshot-based OCR
- No Playwright, CDP, or browser automation frameworks
- No API key usage in CU path
- Accessibility tree reads only

## Parity Baseline

CU extraction must match API baseline:
- 28 documents
- 321 tabs
- 134 child tabs
- 283,831 words

## Code Reference

- Probe: core/adapter_package_manager/google_cu_execution_probe.py
- Validator: core/adapter_package_manager/google_cu_parity_validator.py
- Slice: core/adapter_package_manager/w0_001_cu_slice_readiness.py
