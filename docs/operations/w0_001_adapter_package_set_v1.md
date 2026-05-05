# W0-001 Adapter Package Set

**Version:** v1
**Date:** 2026-05-05
**Package Set ID:** W0-001

## Purpose

Composed operational bundle for the W0-001 triple-test.
Selects packages from the Google Workspace Adapter Family
that are required for the Drive/Docs ingestion validation test.

## Required Members

| Package ID | Role | Service | Maturity |
|-----------|------|---------|----------|
| W-GWS-CORE-001 | Core Foundation | Google Workspace | 100% |
| W-GDRIVE-API-001 | Service API | Google Drive | 100% |
| W-GDOCS-API-001 | Service API | Google Docs | 100% |
| W-GDRIVE-CU-001 | Service CU | Google Drive | 0% |
| W-GDOCS-CU-001 | Service CU | Google Docs | 0% |

## Excluded Future Candidates

These services do **NOT** block W0-001:
- Gmail
- Google Sheets
- Google Slides
- Google Calendar
- Google Forms
- Google Meet
- Google Admin

## Readiness Rules

| Slice | Ready When |
|-------|-----------|
| API slice | Core + Drive API + Docs API all at 100% |
| CU slice | Drive CU + Docs CU all at 100% |
| Full triple-test | API slice + CU slice both ready |
| Memory activation | Requires separate founder review |

## Current Status

- **API slice:** READY (Core, Drive API, Docs API all at 100%)
- **CU slice:** NOT READY (Drive CU 0%, Docs CU 0%)
- **Full triple-test:** NOT READY (CU slice blocks)
- **Memory activation:** NOT READY (requires founder review)
- **Overall status:** API_READY

## Module

`core/adapter_package_manager/w0_001_package_set.py`
