# EOS — Cross-Agent Configuration

Read by all AI coding tools.

## Project
EntrepreneurOS — AI OS for entrepreneurs
VPS: 100.77.233.50 | Dir: /opt/OS

## Rules for all agents
1. Verify imports before declaring done
2. Never rebuild Docker unless Dockerfile changed
3. Test: python3 -c "from eos_ai.X import Y"
4. LLM: qwen2.5:3b (Anthropic credits depleted)
5. Primary service: os-discord

## Structure
eos_ai/      — AI brain
services/  — bots and services
agents/   — agent soul docs
skills/   — agent runtime skills
