# W-GDRIVE-API-001: Google Drive API Adapter Package

**Version:** v1
**Date:** 2026-05-05
**Package ID:** W-GDRIVE-API-001
**Status:** 100% Mature

## Purpose

Drive inventory and metadata extraction for W0-001.
Derived from W-GWS-API-001 where applicable.

## Capabilities

| Capability | Description |
|-----------|-------------|
| google_drive_inventory | Enumerate Drive files |
| google_drive_metadata_extraction | Extract file metadata |
| folder_file_identification | Identify folders vs files |
| mime_type_detection | Detect MIME types |
| modified_time_extraction | Extract modification timestamps |
| owner_metadata_extraction | Extract owner metadata |
| source_provenance | Track extraction source |
| in_scope_file_listing | List in-scope files |

## Governance

- Read-only
- No permission changes
- No edits/deletes/moves/shares
- No export/download unless approved
- No credential capture

## Legacy Provenance

Derived from W-GWS-API-001. The original monolithic Google Workspace
API adapter path has been split into Drive API + Docs API service
packages. This package inherits the Drive-related capabilities.

## Module

`core/adapter_package_manager/google_drive_api_package.py`
