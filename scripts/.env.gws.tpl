# Google Workspace provider-token op template (WP-P4-PROVIDER-TOKEN-VAULTING-001)
# Consumed by resolve_provider_token_injection('google_workspace') in
# substrate/execution/credential_gate.py — op:// references ONLY, never values.
# Backing item created/rotated by scripts/vault_gws_credentials.py.
GWS_OAUTH_CLIENT_ID=op://${UMH_OP_VAULT}/Google-Workspace-OAuth/client_id
GWS_OAUTH_CLIENT_SECRET=op://${UMH_OP_VAULT}/Google-Workspace-OAuth/client_secret
GWS_OAUTH_REFRESH_TOKEN=op://${UMH_OP_VAULT}/Google-Workspace-OAuth/refresh_token
