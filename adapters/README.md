# adapters/

External system boundaries. Every connection to the outside world
(APIs, models, scrapers, calendars) goes through an adapter.

## Subdirectories

| Path | Purpose |
|------|---------|
| `adapter_engine/` | Adapter lifecycle and contract enforcement |
| `calendar/` | Calendar integrations (Google Calendar, Calendly) |
| `data_source_adapters/` | Data ingestion sources (GWS, local files) |
| `google_workspace/` | Google Workspace API adapter |
| `higgsfield/` | Higgsfield video generation adapter |
| `model_adapters/` | LLM model adapters (cc_sdk, Gemini, Groq, Ollama) |
| `notebooklm/` | NotebookLM adapter |
| `notion/` | Notion API adapter |
| `scrapling/` | Web scraping adapter |

## §24 Reference

Canonical module tree §24: `adapters/` — per-system boundaries with
translate_request / normalize_result / observe_state contract.

## Boundary

Adapters translate and normalize. They do NOT execute (workers do that)
and do NOT make decisions (control plane does that). The Tab 9 contract
(Law 5.9): adapters implement `translate_request`, `normalize_result`,
`observe_state` — never `execute()`.
