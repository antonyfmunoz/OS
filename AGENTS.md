# UMH — Cross-Agent Configuration

Read by all AI coding tools.

## Project
UMH (Universal Mastery Hierarchy) — AI intelligence substrate
VPS: 100.77.233.50 | Dir: /opt/OS

## Rules for all agents
1. Verify imports before declaring done
2. Never rebuild Docker unless Dockerfile changed
3. Test: python3 -c "from substrate.X import Y"
4. LLM routing: cc_sdk → Gemini 2.5 Flash → Groq → Ollama
5. Primary service: os-discord

## Structure
substrate/    — UMH brain (types, control plane, execution, governance, state)
adapters/     — external system adapters (models, GWS, browser)
transports/   — I/O surfaces (discord, API, presence, node mesh)
projections/  — application projections (EOS)
services/     — deployment entrypoints (discord_bot.py, operator_api.py)
agents/       — agent soul docs
skills/       — agent runtime skills
