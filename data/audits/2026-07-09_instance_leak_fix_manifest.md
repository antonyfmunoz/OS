# Instance-Leak Fix Manifest — 2026-07-09

100% instance-leak elimination for multi-tenancy. Every hardcoded tenant value →
tenant-scoped runtime resolution, neutral fallback when unset. Sourced from 6
parallel classification audits + independent services recheck.

## Canonical resolvers — route EVERY fix through these (do not invent per-site lookups)
All in `substrate/state/business/business_instance.py`:
- `get_ai_name(ctx=None, venture_id='')` → AI name; neutral `''` when unset. Never "DEX".
- `get_founder_name(ctx=None, venture_id='', default='')` → founder; pass a neutral
  `default='the founder'` for prose. Never "Antony"/"Munoz".
- `get_github_repo(default='')` → `owner/repo` from env. Never "antonyfmunoz/OS".
- `get_active_venture_id(ctx=None, default='')` → active venture slug. Never "lyfe_institute".
- `get_ventures(ctx=None)` → `[{'id','name'},...]` tenant roster; `[]` when unset.
  Use for competitor tables / world-pulse queries / agent hierarchies / folder maps
  that currently hardcode a venture list.
BIS prompt seam (already exists): `BusinessInstanceManager(ctx).get_context_for_agents(venture_id)`
and `.get_bis(venture_id)` expose offer_name/offer_price/offer_type/icp_description/
north_star/founder_name/name/primary_channel/ai_name — use for EOS agent/workflow prompts.

Infra hosts (VPS/Beast IP literals): read from env with EMPTY default (skip provider
/ disable feature on empty), or from `infra/device_registry.json`. Never hardcode
`100.77.233.50` / `100.74.199.102` even as a fallback.

## Rule for EVERY fix
1. Replace the literal with the resolver call, tenant-scoped (thread ctx where available).
2. Neutral fallback ONLY — `''`, `'the founder'`, `'the venture'`, `[]`, or skip.
   A named tenant default is the exact multi-tenant bug being removed.
3. `python3 -m py_compile <file>` must pass; import-smoke the module.
4. Keep code identifiers (class/func/var names like DexConversation, dex_response,
   _call_dex_converse) — those are symbols, not tenant values. Do NOT rename them.

## MACHINE BOUNDARY (do not violate)
Only UMH substrate/control-plane lives in /opt/OS. Fix files IN this checkout only.
`projections/eos/agents/*` + `workflows/*` are EOS app-body binding logic that is
git-tracked here — de-leak in place, but pull NOTHING from the Beast. EOS app body
on the Beast is a separate pass.

---

## substrate/ — 35 sites, 9 files (all venture_slug)
- `substrate/control_plane/events/event_bus.py` — L194,234,270,301,345,381,413: `payload.get("venture_id","lyfe_institute")` → `get_active_venture_id(self.ctx)` (or ctx.active_venture_id), no literal.
- `substrate/control_plane/proactive/proactive_engine.py` — L199 `get_bis('lyfe_institute')`→`get_bis(get_active_venture_id(self.ctx))`; L245 `venture_id='lyfe_institute'`→active venture.
- `substrate/control_plane/agents/ceo_agent.py` — L135,288,334,367: drop `or 'lyfe_institute'` literal fallback; require ctx/BIS.
- `substrate/control_plane/agents/agent_hierarchy.py` — L135,161,172,193,202,229,255,280: build hierarchy from `get_ventures(ctx)`, not literal slugs.
- `substrate/control_plane/scheduling/daily_sync.py` — L353,354: key venture→NOTION-env map off `get_ventures(ctx)` (self_model.instance.ventures already loaded L349-352 — use it), not literal keys.
- `substrate/state/lifecycle/stage_manager.py` — L196,197,198: build stage_page_map from `get_ventures(ctx)` + per-venture env, not literal slugs.
- `substrate/understanding/intelligence/competitive_intel.py` — L18,23,28: COMPETITORS dict keyed on slugs → load competitor data per venture from BIS/projection config at runtime.
- `substrate/understanding/world_pulse/world_pulse.py` — L49,58,67,76,85,97: PERPLEXITY_QUERIES venture entries → load per-venture queries from BIS at runtime.
- (docstring/`__main__`/comment slug mentions are LEGITIMATE — leave, or neutralize to "venture_slug" placeholder so the file can exit the allowlist.)

## adapters/ — 66 sites, 12 files
- `adapters/google_workspace/email_gps.py` — L28 ANTONY enum→role; L56/62/63 DEX_TEMPLATE→get_ai_name()+get_founder_name(); L104-173 folder-def strings→runtime; L476-479 founder-context fallback→BIS; L484-487; L516-544 classify prompt→get_ai_name()+founder; L576-590 draft prompt; L751 `getattr(ctx,'venture_id','lyfe_institute')`→get_active_venture_id(ctx).
- `adapters/google_workspace/doc_creator.py` — L23 audience default; L48 "DEX"→get_ai_name(); L69-70 conglomerate+venture list→get_ventures(ctx); L323,357,364 founder→get_founder_name().
- `adapters/google_workspace/gws_scanner.py` — L225-229,233,259-266,272-276,517-520,537-587,628,664: founder+venture roster+DEX username → BIS venture registry + get_ai_name()/get_founder_name().
- `adapters/google_workspace/document_filer.py` — L53 venture enum in prompt schema → venture ids from registry.
- `adapters/calendar/meetings.py` — L183/190/199/200,632 DEX+founder→resolvers; L539,542 per-venture branch→registry; L671,681 founder.
- `adapters/calendar/travel_manager.py` — L95,96,169,202: use existing `{_traveler}` ctx pattern + get_ai_name(); founder from ctx.
- `adapters/notebooklm/notebooklm_sync.py` — L49-53 notebooks dict keyed on slugs→get_ventures(ctx); L82 param default; L302 literal loop→registry.
- `adapters/notion/notion_sync.py` — L29-31 `_PREFIXES` venture KEYS→registry (env-var VALUES are fine).
- `adapters/notion/notion_publisher.py` — L38-40 `_VENTURE_PREFIXES` keys→registry; L282,297,298,319,389,427,462 `_get_db_id("lyfe_institute"/"personal_brand",...)`→active venture from ctx.
- `adapters/models/agent_runtime.py` — L243,252 `venture_id or "lyfe_institute"`→get_active_venture_id(ctx).
- `adapters/models/model_router.py` — L463 Beast IP fallback→env empty/registry; L927 `"100.74.199.102" in base_url` node check→device_registry role check.
- `adapters/github/github_operations.py` — L35 `repo="antonyfmunoz/OS"` default→`get_github_repo()`.

## transports/ — 12 sites, 9 files
- `transports/discord/discord_utils.py` — L91 `username='DEX'`→get_ai_name() fallback 'Assistant'.
- `transports/api/webhooks/calendly_webhook.py` — L26,277 venture_id literal→active venture; L57/60/334 venture display→registry; L376 username 'DEX'→get_ai_name(); L418/425/426 founder+DEX in email→get_founder_name()+get_ai_name().
- `transports/api/signal_factory.py` — L18 `organization_id="munoz-holdings"`→ctx.org_id / UMH_ORG_ID env, no literal.
- `transports/api/cockpit_core_routes.py` — L1245-1247 `/profile` returns hardcoded "Antony F. Munoz"/"Munoz Conglomerate"/venture list → read all from BIS (founder_name, org, get_ventures(ctx)).
- `transports/presence/handlers/cc_command_handler.py` — L235 `else "empyrean_creative"`→get_active_venture_id(ctx). (L118,329 DEX prose = optional parity, interpolate get_ai_name().)
- `transports/api/app.py` — L468,470 CORS hardcodes VPS IP → env-driven origins list.
- `transports/api/operator.py` — L50 CORS VPS IP → env-driven.
- `transports/api/cockpit_workspace_routes.py` — L491 `"antonys beast pc@100.74.199.102"`→device_registry executor node.
- `transports/api/cockpit_presence_routes.py` — L380,435 KOKORO_TTS_URL fallback Beast IP → empty default.

## services/ — 46 lines, 14 files (independent recheck)
Fix AI-name/founder/venture/IP literals; keep code identifiers.
- `services/discord_message_handlers.py` — DONE (conversation_id derived from channel_id; media wired).
- `services/discord_bot_commands.py` — "Antony" prose (L702,809,823,828,1165,1690), DEX in labels (L1096,1302,1349,1733), venture literals (L2433,2595) → get_founder_name()/get_ai_name()/get_active_venture_id().
- `services/discord_bot.py` — L2,10 DEX brand comments; L205 DEFAULT_VENTURE_ID "lyfe_institute"→env/BIS; L765 "Initiate Arena $750"→BIS offer; L937 agent_id="dex" (identifier-ish, verify); L1035 DEX comment.
- `services/bridge_health.py` — L46,47,59,67,206 Beast IP + "antonys beast pc" paths→device_registry/env; L184,224 username "DEX-WATCHDOG"→get_ai_name()+"-watchdog".
- `services/oauth_device_flow.py` L39; `services/export_bridge_handler.py` L34; `services/local_bridge_client.py` L2,4,39; `services/trigger_export.py` L43; `services/auth_flows/claude.py` L154; `services/auth_flows/chatgpt.py` L332,383; `services/local_bridge_server.py` L2 — IP-literal env fallbacks → empty/registry default; "Antony" prose in docstrings → neutral.
- `services/cc_webhook_receiver.py` L140,143,328 `dex_main` session key → derive from get_ai_name() prefix.
- `services/overnight_scrape.py` L202 venture_id "lyfe_institute"→active venture.
- `services/icp_scorer.py` — audit line; verify + fix any founder/venture literal.

## projections/eos/ — 17 sites, 9 files (fix IN /opt/OS shell; Beast body separate)
- `projections/eos/agents/legal.py` — L161,166,167 entity list→BIS legal_entities; L235,236 trademark items→get_ventures(ctx); state "Oregon"→BIS field.
- `projections/eos/agents/ceo.py` — L67 product+ICP→BIS offer_name+icp_description; L68,100 north_star value→bis.north_star.
- `projections/eos/agents/product.py` — L156 "Initiate Arena"→bis.offer_name.
- `projections/eos/agents/customer_success.py` — L166 default "Initiate Arena"→bis.offer_name; L234 brand→bis.offer_name.
- `projections/eos/workflows/content.py` — L129 brand→bis brand/venture; L132 ICP "men 18-25"→bis.icp_description.
- `projections/eos/workflows/daily.py` — L165 "Initiate Arena pipeline"→active venture name.
- `projections/eos/workflows/outreach.py` — L154 "Initiate Arena"→bis.offer_name.
- `projections/eos/workflows/github.py` — L28 `repo="antonyfmunoz/OS"`→get_github_repo().
- `projections/eos/workflows/document.py` — L167 `audience or "Antony"`→get_founder_name(default='').

## scripts/ — 2 hard (rest OPS_CONFIG, fix under 100% too)
- `scripts/agent_task_executor.py` — L218 `or 'lyfe_institute'`→get_active_venture_id(ctx).
- `scripts/orchestrator.py` — L925-928 "Initiate Arena" content baked in Job→build prompt from BIS offer/icp.
- (Ops loops morning_intel/eod_sync/notion_seed* etc: fix DEX/founder/venture literals via resolvers under the 100% ruling — second pass, eyeball after runtime diff.)

## CC agents — 4 files (de-brand + rename, task #18)
`.claude/agents/eos-{researcher,code-reviewer,verifier,simplifier}.md` → `umh-*`;
strip "for EOS"/"means for EOS" from name+description+body (capability is UMH,
domain injected at runtime); update CLAUDE.md + .claude/rules references.

## Seam enforcement (maintain, not just clean)
Widen `scripts/check_instance_leak.py` to scan adapters/, transports/, services/,
projections/ (today: substrate only). Empty LEGACY_INSTANCE_LEAKS as files go green.
