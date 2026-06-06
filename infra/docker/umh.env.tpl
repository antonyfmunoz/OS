# UMH Docker runtime secrets — resolved from 1Password at runtime via dc-up.sh
# This file is safe to commit. It contains vault references, not actual values.

# ── Secrets ──────────────────────────────────────────────────────────────────
DATABASE_URL=op://UMH-Production/Database-Neon/url
ANTHROPIC_API_KEY=op://UMH-Production/AI-Anthropic/api_key
GEMINI_API_KEY=op://UMH-Production/AI-Gemini/api_key
GROQ_API_KEY=op://UMH-Production/AI-Groq/api_key
PERPLEXITY_API_KEY=op://UMH-Production/AI-Perplexity/api_key
TELEGRAM_BOT_TOKEN=op://UMH-Production/Telegram-Bot/token
NOTION_API_KEY=op://UMH-Production/Notion-Integration/api_key
HIGGSFIELD_API_KEY=op://UMH-Production/Higgsfield/api_key
HIGGSFIELD_API_KEY_SECRET=op://UMH-Production/Higgsfield/api_key_secret
DISCORD_BRIEF_WEBHOOK=op://UMH-Production/Discord-Bot/brief_webhook

# ── Non-secret config (inline — not worth a separate file for Docker) ───────
EOS_ORG_ID=72727be3-e24d-48f2-bcea-de760ecb4c23
EOS_USER_ID=115fb623-e856-42e3-9af7-25eb578fb9bd
EOS_PORTFOLIO_ID=317a3af0-047e-4d0b-94ec-c163c5c767f9
TELEGRAM_CHAT_ID=8095332965
EOS_TASK_AUTOCLEAR_ENABLED=1

# ── Notion Page IDs (non-secret identifiers) ────────────────────────────────
NOTION_ROOT_ID=32eda8b9-6e4f-8071-b299-fef02dcb1b8c
NOTION_PORTFOLIO_ID=32eda8b9-6e4f-81eb-b253-f2e50bbd298a
NOTION_MORNING_BRIEF_ID=32eda8b9-6e4f-818c-a136-c78a1ce79c17
NOTION_LYFE_INSTITUTE_ID=32eda8b9-6e4f-817f-a314-fc66aa831cc3
NOTION_LYFE_STAGE_ID=32eda8b9-6e4f-815a-8699-ce612973badd
NOTION_LYFE_ACTIVITY_ID=32eda8b9-6e4f-811f-afba-f51ed7a285b8
NOTION_EMPYREAN_CREATIVE_ID=32eda8b9-6e4f-81c7-8872-e5a768ea9faf
NOTION_EMPYREAN_STAGE_ID=32eda8b9-6e4f-812d-b3a6-e184dd9f03a0
NOTION_EMPYREAN_ACTIVITY_ID=32eda8b9-6e4f-81d7-867a-d1a2fa4dcf4f
NOTION_PERSONAL_BRAND_ID=32eda8b9-6e4f-812b-888c-df30298aa856
NOTION_BRAND_STAGE_ID=32eda8b9-6e4f-812f-be75-e8baa4e806d6
NOTION_BRAND_ACTIVITY_ID=32eda8b9-6e4f-81ad-a50e-e80d57c4a6d3
NOTION_AI_COPILOT_ID=32eda8b9-6e4f-81a0-a374-ecd077d09b6a
NOTION_ACTIVITY_ID=32eda8b9-6e4f-8121-9cae-e31327db0459
NOTION_LYFE_PIPELINE_ID=7f090170-8e41-4857-989d-9c5be51bea03
NOTION_LYFE_TASKS_ID=9759dba9-544a-4653-9656-5de637cba081
NOTION_LYFE_WORKFLOWS_ID=7e5b58e2-0a5c-46a8-af73-a52539ef6d69
NOTION_EMPYREAN_WORKFLOWS_ID=357d09b2-deb9-446a-acc7-a7975353fcca
NOTION_BRAND_WORKFLOWS_ID=94f5f7ee-083b-42b2-baa4-f61201356d07
NOTION_EMPYREAN_PIPELINE_ID=3381905e-50e0-4792-8bc2-1ce48bded8db
NOTION_EMPYREAN_TASKS_ID=d5afbe6b-768f-4094-99ae-7a14f6f7dbdc
NOTION_BRAND_CONTENT_ID=513a621a-5b99-4eca-9287-f0742edea66a
NOTION_MEETINGS_ID=333da8b9-6e4f-81bc-ac06-ee87e7d13fa7
NOTION_COMPANIES_ID=32eda8b9-6e4f-81ca-b4e0-cc2c3aeeddb8
NOTION_YOUR_LIST_LYFE=8990bb84-273f-4590-ac64-b7cf9321ce8c
NOTION_YOUR_LIST_EMPYREAN=c6f06702-f1f9-4109-8da9-2cf7a094fd1b
NOTION_YOUR_LIST_BRAND=4ef5362b-6062-4412-bb91-68457ffba5bf
NOTION_PERSONAL_BRAND_GOALS_OKRS_DB=335da8b9-6e4f-81fa-968d-fccde4b8b25f
NOTION_PERSONAL_BRAND_TASKS_DB=335da8b9-6e4f-8100-8b15-dc1507508f61
NOTION_PERSONAL_BRAND_MEETINGS_DB=335da8b9-6e4f-81eb-b27d-c944ade421ec
NOTION_PERSONAL_BRAND_DOCUMENTS_DB=335da8b9-6e4f-812c-a394-e7cbe379316f
NOTION_PERSONAL_BRAND_METRICS_KPIS_DB=335da8b9-6e4f-81a5-a9b0-e9cda479caa8
NOTION_PERSONAL_BRAND_DECISIONS_DB=335da8b9-6e4f-819a-8e7a-e6e4c9b86913
NOTION_PERSONAL_BRAND_ROLES_DB=335da8b9-6e4f-8124-bb3c-eb4442c6cf99
NOTION_PERSONAL_BRAND_TOOLS_DB=335da8b9-6e4f-81a2-948b-f8e41b266bb3
NOTION_PERSONAL_BRAND_SKILLS_DB=335da8b9-6e4f-81ba-9131-d2aaaccc0fad
NOTION_PERSONAL_BRAND_WORKFLOWS_DB=335da8b9-6e4f-8132-a1f1-fe7dda860929
NOTION_PERSONAL_BRAND_PIPELINE_CRM_DB=335da8b9-6e4f-81f5-8512-c26f669db0d4
NOTION_LYFE_INSTITUTE_GOALS_OKRS_DB=335da8b9-6e4f-8140-8b46-ff76c033cca0
NOTION_LYFE_INSTITUTE_TASKS_DB=335da8b9-6e4f-8117-a13f-ee7f3993dda9
NOTION_LYFE_INSTITUTE_MEETINGS_DB=335da8b9-6e4f-81db-a64b-f4828dd8c48f
NOTION_LYFE_INSTITUTE_DOCUMENTS_DB=335da8b9-6e4f-81bd-9ab2-f2f3c982c5ab
NOTION_LYFE_INSTITUTE_METRICS_KPIS_DB=335da8b9-6e4f-8144-972a-d8dfbf1e04e3
NOTION_LYFE_INSTITUTE_DECISIONS_DB=335da8b9-6e4f-81ac-9fbf-c92fa2cef6cb
NOTION_LYFE_INSTITUTE_ROLES_DB=335da8b9-6e4f-81a6-b784-d1dee5bcbd3a
NOTION_LYFE_INSTITUTE_TOOLS_DB=335da8b9-6e4f-81e3-af7f-c5f72d2178b5
NOTION_LYFE_INSTITUTE_SKILLS_DB=335da8b9-6e4f-81b9-a1cc-ed4c294dbbb2
NOTION_LYFE_INSTITUTE_WORKFLOWS_DB=335da8b9-6e4f-815e-b5ee-eb3c771d6554
NOTION_LYFE_INSTITUTE_PIPELINE_CRM_DB=335da8b9-6e4f-8192-b3f9-c203c4317d2e
NOTION_EMPYREAN_CREATIVE_GOALS_OKRS_DB=335da8b9-6e4f-8192-9a38-ec55e49f5e64
NOTION_EMPYREAN_CREATIVE_TASKS_DB=335da8b9-6e4f-81a8-8444-c9a508beb032
NOTION_EMPYREAN_CREATIVE_MEETINGS_DB=335da8b9-6e4f-81fb-84a4-c1c2e4bbcfd7
NOTION_EMPYREAN_CREATIVE_DOCUMENTS_DB=335da8b9-6e4f-813d-ac5e-e399a84722ce
NOTION_EMPYREAN_CREATIVE_METRICS_KPIS_DB=335da8b9-6e4f-8144-9985-c8ed65636ee3
NOTION_EMPYREAN_CREATIVE_DECISIONS_DB=335da8b9-6e4f-8174-a53a-d9a825033d7a
NOTION_EMPYREAN_CREATIVE_ROLES_DB=335da8b9-6e4f-818f-8f13-d0c2910449d2
NOTION_EMPYREAN_CREATIVE_TOOLS_DB=335da8b9-6e4f-81c1-a56b-c3cb6f3be1ef
NOTION_EMPYREAN_CREATIVE_SKILLS_DB=335da8b9-6e4f-81c0-b4e8-c1b23853ac8c
NOTION_EMPYREAN_CREATIVE_WORKFLOWS_DB=335da8b9-6e4f-813a-985c-f9a48b2b55a7
NOTION_EMPYREAN_CREATIVE_PIPELINE_CRM_DB=335da8b9-6e4f-81cd-a1ae-f7ce821ad55a
NOTION_PORTFOLIO_OVERVIEW_DB=335da8b9-6e4f-815a-90a4-c54cf9114427

# ── EOS Discord mode routing ────────────────────────────────────────────────
EOS_DISCORD_BUILDER_CHANNELS=1491648663221567499
EOS_DISCORD_PRODUCT_CHANNELS=1491648664202903572
EOS_DISCORD_BUILDER_SESSION=dex_builder_main
EOS_DISCORD_PRODUCT_SESSION=dex_product_main
EOS_DISCORD_BUILDER_TARGET=vps
EOS_DISCORD_PRODUCT_TARGET=vps

# ── Local Bridge ────────────────────────────────────────────────────────────
EOS_LOCAL_BRIDGE_IP=100.74.199.102
EOS_LOCAL_BRIDGE_PORT=8766
EOS_LOCAL_BRIDGE_ENABLED=1

# ── Ventures JSON ───────────────────────────────────────────────────────────
VENTURES_JSON=[{"id": "personal_brand", "name": "Personal Brand", "notion_goals_okrs_db": "335da8b9-6e4f-81fa-968d-fccde4b8b25f", "notion_tasks_db": "335da8b9-6e4f-8100-8b15-dc1507508f61", "notion_meetings_db": "335da8b9-6e4f-81eb-b27d-c944ade421ec", "notion_documents_db": "335da8b9-6e4f-812c-a394-e7cbe379316f", "notion_metrics_kpis_db": "335da8b9-6e4f-81a5-a9b0-e9cda479caa8", "notion_decisions_db": "335da8b9-6e4f-819a-8e7a-e6e4c9b86913", "notion_roles_db": "335da8b9-6e4f-8124-bb3c-eb4442c6cf99", "notion_tools_db": "335da8b9-6e4f-81a2-948b-f8e41b266bb3", "notion_skills_db": "335da8b9-6e4f-81ba-9131-d2aaaccc0fad", "notion_workflows_db": "335da8b9-6e4f-8132-a1f1-fe7dda860929", "notion_pipeline_crm_db": "335da8b9-6e4f-81f5-8512-c26f669db0d4", "business_model": "content", "benchmarks": {"dms_per_week": 10, "reply_rate_pct": 20, "call_rate_pct": 15, "close_rate_pct": 10, "cac_payback_days": 0, "ltv_cac_ratio": 0}, "stage": "validation", "icp": "Founders and entrepreneurs who want to build an AI-native business but do not know how. Follow The Vigilante Architect for the blueprint.", "offer": "Content and education — The Vigilante Architect. Building in public. Audience growth leads to EOS productization.", "north_star": "10K engaged followers who are potential EOS customers", "binding_constraint": "content output — not posting consistently", "primary_channel": "instagram_content", "revenue": 0, "current_mrr": 0, "validation_milestone": "1K engaged followers", "proof_needed": "consistent content producing inbound leads", "stage_gates": {"to_stage_2": "10K followers with measurable inbound"}}, {"id": "lyfe_institute", "name": "Lyfe Institute", "notion_goals_okrs_db": "335da8b9-6e4f-8140-8b46-ff76c033cca0", "notion_tasks_db": "335da8b9-6e4f-8117-a13f-ee7f3993dda9", "notion_meetings_db": "335da8b9-6e4f-81db-a64b-f4828dd8c48f", "notion_documents_db": "335da8b9-6e4f-81bd-9ab2-f2f3c982c5ab", "notion_metrics_kpis_db": "335da8b9-6e4f-8144-972a-d8dfbf1e04e3", "notion_decisions_db": "335da8b9-6e4f-81ac-9fbf-c92fa2cef6cb", "notion_roles_db": "335da8b9-6e4f-81a6-b784-d1dee5bcbd3a", "notion_tools_db": "335da8b9-6e4f-81e3-af7f-c5f72d2178b5", "notion_skills_db": "335da8b9-6e4f-81b9-a1cc-ed4c294dbbb2", "notion_workflows_db": "335da8b9-6e4f-815e-b5ee-eb3c771d6554", "notion_pipeline_crm_db": "335da8b9-6e4f-8192-b3f9-c203c4317d2e", "business_model": "b2c_coaching", "benchmarks": {"dms_per_week": 50, "reply_rate_pct": 15, "call_rate_pct": 30, "close_rate_pct": 20, "cac_payback_days": 30, "ltv_cac_ratio": 3.0}, "stage": "validation", "icp": "Men 18-25, interested in fitness and self-improvement, lack structure and discipline, have tried and quit before, want someone to hold them accountable", "offer": "Initiate Arena — 90-day discipline and execution coaching program. $750 one-time. Men who want to build the habits and identity of someone who executes.", "north_star": "$10K/month net profit", "binding_constraint": "leads — no qualified leads in pipeline", "primary_channel": "instagram_dms", "revenue": 0, "current_mrr": 0, "validation_milestone": "first $750 sale", "proof_needed": "close 1 sale via Instagram DM to call to close sequence", "stage_gates": {"to_stage_2": "consistent $10K/month for 2 months"}}, {"id": "empyrean_creative", "name": "Empyrean Creative", "notion_goals_okrs_db": "335da8b9-6e4f-8192-9a38-ec55e49f5e64", "notion_tasks_db": "335da8b9-6e4f-81a8-8444-c9a508beb032", "notion_meetings_db": "335da8b9-6e4f-81fb-84a4-c1c2e4bbcfd7", "notion_documents_db": "335da8b9-6e4f-813d-ac5e-e399a84722ce", "notion_metrics_kpis_db": "335da8b9-6e4f-8144-9985-c8ed65636ee3", "notion_decisions_db": "335da8b9-6e4f-8174-a53a-d9a825033d7a", "notion_roles_db": "335da8b9-6e4f-818f-8f13-d0c2910449d2", "notion_tools_db": "335da8b9-6e4f-81c1-a56b-c3cb6f3be1ef", "notion_skills_db": "335da8b9-6e4f-81c0-b4e8-c1b23853ac8c", "notion_workflows_db": "335da8b9-6e4f-813a-985c-f9a48b2b55a7", "notion_pipeline_crm_db": "335da8b9-6e4f-81cd-a1ae-f7ce821ad55a", "business_model": "b2b_saas", "benchmarks": {"dms_per_week": 20, "reply_rate_pct": 10, "call_rate_pct": 25, "close_rate_pct": 15, "cac_payback_days": 90, "ltv_cac_ratio": 5.0}, "stage": "validation", "icp": "B2B — small to mid-size businesses that need AI infrastructure but lack technical expertise to build it themselves", "offer": "AI infrastructure buildout — custom AI systems, automations, and agents for business operations. Retainer-based.", "north_star": "$10K/month net profit", "binding_constraint": "first client — no paying clients yet", "primary_channel": "direct_outreach", "revenue": 0, "current_mrr": 0, "validation_milestone": "first retainer client", "proof_needed": "close 1 retainer client at $2K+/month", "stage_gates": {"to_stage_2": "3 retainer clients at $3K+/month each"}}]
