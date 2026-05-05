# W-GWS-API-001 Governance Policy

**Version:** v1
**Date:** 2026-05-05
**Policy ID:** w_gws_api_001_governance_policy

## Core Principle

The API tab-aware extraction path is **read-only by default**.
No mutation, no credential capture, no memory promotion,
no global canon writes.

## Allowed Actions

| Action | Description |
|--------|-------------|
| read_metadata | Read Drive/Docs metadata |
| read_document_content_through_authorized_api | Read document content via authenticated API |
| read_tabs_content_for_in_scope_docs | Read tab content for authorized documents |
| emit_local_canonical_records | Emit CanonicalSourceRecord locally |
| validate_coverage | Validate extraction coverage |
| generate_local_reports | Generate local maturity/coverage reports |
| build_source_graph | Build source graph from extracted records |

## Blocked Actions

### Mutation
- edit_documents
- delete_documents
- move_documents
- mutate_source_files

### Permissions
- share_documents
- change_permissions
- change_drive_permissions

### Credential Capture
- capture_credentials
- capture_tokens
- capture_api_keys
- capture_cookies
- capture_secrets

### Scope Violations
- switch_accounts
- open_gmail
- promote_memory
- write_global_canon

### Export/Download
- export_files_without_approval
- download_files_without_approval

## Governance Flags

| Flag | Value |
|------|-------|
| read_only | true |
| instance_scoped | true |
| global_canon_default | false |
| export_requires_approval | true |
| auth_token_opaque | true |

## Verification Functions

| Function | What It Checks |
|----------|---------------|
| governance_is_read_only | read_only flag is true |
| governance_blocks_mutation | edit/delete/move in blocked_actions |
| governance_blocks_credential_capture | all 5 capture actions blocked |
| governance_blocks_permission_changes | change_permissions + share_documents blocked |
| governance_blocks_memory_promotion | promote_memory blocked |
| governance_requires_export_approval | export_requires_approval flag is true |
| governance_preserves_instance_scope | instance_scoped=true AND global_canon_default=false |

## Module

`core/adapter_package_manager/google_workspace_api_governance.py`
