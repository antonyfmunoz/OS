# UMH Docker runtime secrets — resolved from 1Password at runtime via dc-up.sh
# This file is safe to commit. It contains vault references and PLACEHOLDERS,
# never one tenant's live data. The active tenant provides real values at
# runtime via env (UMH_OP_VAULT, UMH_BEAST_IP, UMH_ASSISTANT_SESSION, …) and
# op:// resolution — never bake instance identifiers into this template.

# ── Secrets ──────────────────────────────────────────────────────────────────
DATABASE_URL=op://${UMH_OP_VAULT}/Database-Neon/url
ANTHROPIC_API_KEY=op://${UMH_OP_VAULT}/AI-Anthropic/api_key
GEMINI_API_KEY=op://${UMH_OP_VAULT}/AI-Gemini/api_key
GROQ_API_KEY=op://${UMH_OP_VAULT}/AI-Groq/api_key
PERPLEXITY_API_KEY=op://${UMH_OP_VAULT}/AI-Perplexity/api_key
TELEGRAM_BOT_TOKEN=op://${UMH_OP_VAULT}/Telegram-Bot/token
NOTION_API_KEY=op://${UMH_OP_VAULT}/Notion-Integration/api_key
HIGGSFIELD_API_KEY=op://${UMH_OP_VAULT}/Higgsfield/api_key
HIGGSFIELD_API_KEY_SECRET=op://${UMH_OP_VAULT}/Higgsfield/api_key_secret
DISCORD_BRIEF_WEBHOOK=op://${UMH_OP_VAULT}/Discord-Bot/brief_webhook
LIVEKIT_API_KEY=UMHKey1
LIVEKIT_API_SECRET=op://${UMH_OP_VAULT}/LiveKit/api_secret
LIVEKIT_URL=ws://host.docker.internal:7880

# ── Non-secret config (instance identifiers — supply at runtime via env) ──────
EOS_ORG_ID=${EOS_ORG_ID}
EOS_USER_ID=${EOS_USER_ID}
EOS_PORTFOLIO_ID=${EOS_PORTFOLIO_ID}
TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
EOS_TASK_AUTOCLEAR_ENABLED=1

# ── Notion Page / Database IDs (instance identifiers — resolve at runtime) ────
# These are one tenant's Notion workspace IDs. A template holds references, not
# literals — supply via op:// (a Notion section in the tenant vault) or env.
NOTION_ROOT_ID=op://${UMH_OP_VAULT}/Notion/root_id
NOTION_PORTFOLIO_ID=op://${UMH_OP_VAULT}/Notion/portfolio_id
NOTION_MORNING_BRIEF_ID=op://${UMH_OP_VAULT}/Notion/morning_brief_id
NOTION_LYFE_INSTITUTE_ID=op://${UMH_OP_VAULT}/Notion/lyfe_institute_id
NOTION_LYFE_STAGE_ID=op://${UMH_OP_VAULT}/Notion/lyfe_stage_id
NOTION_LYFE_ACTIVITY_ID=op://${UMH_OP_VAULT}/Notion/lyfe_activity_id
NOTION_EMPYREAN_CREATIVE_ID=op://${UMH_OP_VAULT}/Notion/empyrean_creative_id
NOTION_EMPYREAN_STAGE_ID=op://${UMH_OP_VAULT}/Notion/empyrean_stage_id
NOTION_EMPYREAN_ACTIVITY_ID=op://${UMH_OP_VAULT}/Notion/empyrean_activity_id
NOTION_PERSONAL_BRAND_ID=op://${UMH_OP_VAULT}/Notion/personal_brand_id
NOTION_BRAND_STAGE_ID=op://${UMH_OP_VAULT}/Notion/brand_stage_id
NOTION_BRAND_ACTIVITY_ID=op://${UMH_OP_VAULT}/Notion/brand_activity_id
NOTION_AI_COPILOT_ID=op://${UMH_OP_VAULT}/Notion/ai_copilot_id
NOTION_ACTIVITY_ID=op://${UMH_OP_VAULT}/Notion/activity_id
NOTION_LYFE_PIPELINE_ID=op://${UMH_OP_VAULT}/Notion/lyfe_pipeline_id
NOTION_LYFE_TASKS_ID=op://${UMH_OP_VAULT}/Notion/lyfe_tasks_id
NOTION_LYFE_WORKFLOWS_ID=op://${UMH_OP_VAULT}/Notion/lyfe_workflows_id
NOTION_EMPYREAN_WORKFLOWS_ID=op://${UMH_OP_VAULT}/Notion/empyrean_workflows_id
NOTION_BRAND_WORKFLOWS_ID=op://${UMH_OP_VAULT}/Notion/brand_workflows_id
NOTION_EMPYREAN_PIPELINE_ID=op://${UMH_OP_VAULT}/Notion/empyrean_pipeline_id
NOTION_EMPYREAN_TASKS_ID=op://${UMH_OP_VAULT}/Notion/empyrean_tasks_id
NOTION_BRAND_CONTENT_ID=op://${UMH_OP_VAULT}/Notion/brand_content_id
NOTION_MEETINGS_ID=op://${UMH_OP_VAULT}/Notion/meetings_id
NOTION_COMPANIES_ID=op://${UMH_OP_VAULT}/Notion/companies_id
NOTION_YOUR_LIST_LYFE=op://${UMH_OP_VAULT}/Notion/your_list_lyfe
NOTION_YOUR_LIST_EMPYREAN=op://${UMH_OP_VAULT}/Notion/your_list_empyrean
NOTION_YOUR_LIST_BRAND=op://${UMH_OP_VAULT}/Notion/your_list_brand
NOTION_PERSONAL_BRAND_GOALS_OKRS_DB=op://${UMH_OP_VAULT}/Notion/personal_brand_goals_okrs_db
NOTION_PERSONAL_BRAND_TASKS_DB=op://${UMH_OP_VAULT}/Notion/personal_brand_tasks_db
NOTION_PERSONAL_BRAND_MEETINGS_DB=op://${UMH_OP_VAULT}/Notion/personal_brand_meetings_db
NOTION_PERSONAL_BRAND_DOCUMENTS_DB=op://${UMH_OP_VAULT}/Notion/personal_brand_documents_db
NOTION_PERSONAL_BRAND_METRICS_KPIS_DB=op://${UMH_OP_VAULT}/Notion/personal_brand_metrics_kpis_db
NOTION_PERSONAL_BRAND_DECISIONS_DB=op://${UMH_OP_VAULT}/Notion/personal_brand_decisions_db
NOTION_PERSONAL_BRAND_ROLES_DB=op://${UMH_OP_VAULT}/Notion/personal_brand_roles_db
NOTION_PERSONAL_BRAND_TOOLS_DB=op://${UMH_OP_VAULT}/Notion/personal_brand_tools_db
NOTION_PERSONAL_BRAND_SKILLS_DB=op://${UMH_OP_VAULT}/Notion/personal_brand_skills_db
NOTION_PERSONAL_BRAND_WORKFLOWS_DB=op://${UMH_OP_VAULT}/Notion/personal_brand_workflows_db
NOTION_PERSONAL_BRAND_PIPELINE_CRM_DB=op://${UMH_OP_VAULT}/Notion/personal_brand_pipeline_crm_db
NOTION_LYFE_INSTITUTE_GOALS_OKRS_DB=op://${UMH_OP_VAULT}/Notion/lyfe_institute_goals_okrs_db
NOTION_LYFE_INSTITUTE_TASKS_DB=op://${UMH_OP_VAULT}/Notion/lyfe_institute_tasks_db
NOTION_LYFE_INSTITUTE_MEETINGS_DB=op://${UMH_OP_VAULT}/Notion/lyfe_institute_meetings_db
NOTION_LYFE_INSTITUTE_DOCUMENTS_DB=op://${UMH_OP_VAULT}/Notion/lyfe_institute_documents_db
NOTION_LYFE_INSTITUTE_METRICS_KPIS_DB=op://${UMH_OP_VAULT}/Notion/lyfe_institute_metrics_kpis_db
NOTION_LYFE_INSTITUTE_DECISIONS_DB=op://${UMH_OP_VAULT}/Notion/lyfe_institute_decisions_db
NOTION_LYFE_INSTITUTE_ROLES_DB=op://${UMH_OP_VAULT}/Notion/lyfe_institute_roles_db
NOTION_LYFE_INSTITUTE_TOOLS_DB=op://${UMH_OP_VAULT}/Notion/lyfe_institute_tools_db
NOTION_LYFE_INSTITUTE_SKILLS_DB=op://${UMH_OP_VAULT}/Notion/lyfe_institute_skills_db
NOTION_LYFE_INSTITUTE_WORKFLOWS_DB=op://${UMH_OP_VAULT}/Notion/lyfe_institute_workflows_db
NOTION_LYFE_INSTITUTE_PIPELINE_CRM_DB=op://${UMH_OP_VAULT}/Notion/lyfe_institute_pipeline_crm_db
NOTION_EMPYREAN_CREATIVE_GOALS_OKRS_DB=op://${UMH_OP_VAULT}/Notion/empyrean_creative_goals_okrs_db
NOTION_EMPYREAN_CREATIVE_TASKS_DB=op://${UMH_OP_VAULT}/Notion/empyrean_creative_tasks_db
NOTION_EMPYREAN_CREATIVE_MEETINGS_DB=op://${UMH_OP_VAULT}/Notion/empyrean_creative_meetings_db
NOTION_EMPYREAN_CREATIVE_DOCUMENTS_DB=op://${UMH_OP_VAULT}/Notion/empyrean_creative_documents_db
NOTION_EMPYREAN_CREATIVE_METRICS_KPIS_DB=op://${UMH_OP_VAULT}/Notion/empyrean_creative_metrics_kpis_db
NOTION_EMPYREAN_CREATIVE_DECISIONS_DB=op://${UMH_OP_VAULT}/Notion/empyrean_creative_decisions_db
NOTION_EMPYREAN_CREATIVE_ROLES_DB=op://${UMH_OP_VAULT}/Notion/empyrean_creative_roles_db
NOTION_EMPYREAN_CREATIVE_TOOLS_DB=op://${UMH_OP_VAULT}/Notion/empyrean_creative_tools_db
NOTION_EMPYREAN_CREATIVE_SKILLS_DB=op://${UMH_OP_VAULT}/Notion/empyrean_creative_skills_db
NOTION_EMPYREAN_CREATIVE_WORKFLOWS_DB=op://${UMH_OP_VAULT}/Notion/empyrean_creative_workflows_db
NOTION_EMPYREAN_CREATIVE_PIPELINE_CRM_DB=op://${UMH_OP_VAULT}/Notion/empyrean_creative_pipeline_crm_db
NOTION_PORTFOLIO_OVERVIEW_DB=op://${UMH_OP_VAULT}/Notion/portfolio_overview_db

# ── EOS Discord mode routing (instance identifiers — supply at runtime) ───────
EOS_DISCORD_BUILDER_CHANNELS=${EOS_DISCORD_BUILDER_CHANNELS}
EOS_DISCORD_PRODUCT_CHANNELS=${EOS_DISCORD_PRODUCT_CHANNELS}
EOS_DISCORD_BUILDER_SESSION=${UMH_ASSISTANT_SESSION:-assistant_main}
EOS_DISCORD_PRODUCT_SESSION=${UMH_ASSISTANT_SESSION:-assistant_main}
EOS_DISCORD_BUILDER_TARGET=vps
EOS_DISCORD_PRODUCT_TARGET=vps

# ── Local Bridge ────────────────────────────────────────────────────────────
EOS_LOCAL_BRIDGE_IP=${UMH_BEAST_IP}
EOS_LOCAL_BRIDGE_PORT=8766
EOS_LOCAL_BRIDGE_ENABLED=1

# ── Ventures JSON (instance data — supply at runtime; empty placeholder) ──────
# The active tenant's portfolio is loaded from BIS/env at runtime. A template
# never embeds one tenant's live ICP / offer / revenue data.
VENTURES_JSON=[]
