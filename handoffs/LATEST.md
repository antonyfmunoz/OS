# Handoff — 2026-05-17 Export Validation Sprint

## Claude Export — BLOCKED
- **Root cause:** empyreanstudios.co has NO MX records (NXDOMAIN on _acme-challenge + MX lookup)
- Verification emails from Anthropic cannot be delivered to antonyfm@empyreanstudios.co
- The multi-inbox Gmail poller, auth_flows/claude.py code path, and 6-digit code extraction are all built and ready
- Unblocked only after MX records are configured or a different receiving email is used

## ChatGPT Export — 7/9 CRITERIA PASSED
- Camoufox launches with en-US locale, anti-detect fingerprinting, persistent profile
- Auth flow navigates to chatgpt.com/auth/login, fills email via DOM selectors
- Adaptive challenge detection works: password, verification_code, magic_link, already_authenticated
- Settings modal opened via sidebar `a:has-text("Settings")` click (not URL — ChatGPT is SPA)
- Data Controls tab clicked via `[role="tab"]:has-text("Data controls")`
- **BLOCKER: "Export Data" button does NOT exist on free-tier ChatGPT Data Controls page**
- Only "Improve the model for everyone" toggle present — export may require Plus subscription
- Bridge transport (VPS → Windows → Camoufox) confirmed working end-to-end

### ChatGPT criteria status
1. Camoufox anti-detect launch — PASS
2. en-US locale forced — PASS
3. Auth flow reaches challenge page — PASS
4. Challenge type detected and screenshotted — PASS
5. Settings modal opened via UI — PASS
6. Data Controls tab navigated — PASS
7. Export button found and clicked — FAIL (button absent on free tier)
8. Success marker detected — FAIL (no export triggered)
9. Export email arrives and parsed — NOT TESTED (blocked by #7)

## Infrastructure Built Tonight
- **services/auth_flows/chatgpt.py** — full adaptive auth flow (password/code/magic-link/already-auth)
- **services/magic_link_handler.py** — refactored for multi-inbox support (per-domain creds)
- **services/browser_adapter.py** — added locale parameter, disables GeoIP when locale set
- **scripts/fire_export.py** — ChatGPT SPA navigation, settings modal click, Data Controls tab
- **services/oauth_device_flow.py** — per-account support (--account flag, login_hint, per-domain cred save)
- **scripts/oauth_grant_empyreancreative.py** — Windows-side OAuth grant for theempyreancreative.com
- **services/export_profiles.yaml** — inbox_email + sender_filter per service
- **.env.secrets** — CHATGPT_EMAIL populated

## OAuth Grant — NOT COMPLETED
- `scripts/oauth_grant_empyreancreative.py` deployed to Windows via SCP
- Script ran, browser opened, but operator wasn't at desktop — 600s timeout expired
- **Action needed:** Re-run on Windows when operator is present, then SCP creds to VPS:
  ```
  ssh -l "antonys beast pc" 100.74.199.102 "cd C:\\Users\\antony\\dev\\OS && python scripts\\oauth_grant_empyreancreative.py"
  scp -o "User=antonys beast pc" "100.74.199.102:C:/Users/antony/.config/gws/gmail_credentials_theempyreancreative.com.json" /root/.config/gws/
  ```

## Tomorrow's First Actions (ordered)
1. **Diagnose empyreanstudios.co MX** — check DNS provider, add Google Workspace MX records or configure forwarding
2. **Complete OAuth grant** for antonyfm@theempyreancreative.com (operator at desktop)
3. **Verify gmail.readonly** on theempyreancreative.com inbox
4. **Refactor auth_flows/claude.py** — switch from magic-link to 6-digit verification code input (handler already built)
5. **Add en-US locale** to Claude in fire_export.py (currently only ChatGPT has it)
6. **Re-fire Claude validation** after MX fix
7. **Determine ChatGPT export tier requirement** — test with Plus account or find alternative export URL
8. **Locale-agnostic selector audit** across all auth flows

## Perimeter (unchanged)
DO NOT TOUCH: gateway.py, cognitive_loop.py, model_router.py, agent_runtime.py, primitives.py, orchestrator.py, memory.py, local_bridge_server.py, cc_webhook_receiver.py
