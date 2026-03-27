# NotebookLM — Best Practices

## When to use
When DEX needs zero-hallucination answers from documents you've uploaded.
When researching competitors or topics grounded in real sources.

## Setup
MCP: jacob-bd/notebooklm-mcp-cli v0.5.9
Installed via: nlm setup add claude-code
Connected: ✓ (verified 2026-03-26)

## Key commands in Claude Code
@notebooklm-mcp to toggle on/off
(35 tools — disable when not using to preserve context window)

## Usage patterns
List notebooks: nlm notebook list
Query: nlm notebook query <id> "question"
Add source: nlm source add <notebook> --url <url>
Add file: nlm source add <notebook> --file <path>

## EOS notebooks to create
1. "Lyfe Institute Research"
   - Competitor analysis (Hormozi, Gadzhi, Morgan)
   - ICP research (men 18-25)
   - Curriculum research

2. "Empyrean Creative Research"
   - AI services market
   - B2B outreach research
   - Case studies

3. "Personal Brand Research"
   - Content strategy
   - Creator economy
   - Competitor content

## Integration with world pulse
World pulse can query NotebookLM notebooks for grounded market intelligence
instead of hallucinating market data. Use alongside Perplexity — Perplexity
for real-time web, NotebookLM for uploaded document synthesis.

## Auth
Run once interactively: nlm login
Uses Chrome profile — headless after first login.
Use a dedicated Google account, not primary.

## CRITICAL
Always toggle off when not in use: @notebooklm-mcp
35 tools consume significant context window.
