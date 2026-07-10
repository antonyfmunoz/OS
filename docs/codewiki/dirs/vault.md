---
type: codewiki-dir
dir: vault
---

# `vault/` — long-term conversation memory: session logs and extracted summaries

**2,929 files · ~15.8 MB · [Full file inventory](../inventory/vault.md)**

*(Counts as of the manifest's `generated_at` 2026-07-10T20:18Z, git SHA `a5f09e48e`. Grows one file per Claude Code session plus occasional hand-authored summaries.)*

## Purpose
`vault/` is UMH's conversation-memory store, governed by `knowledge/WIKI_RULES.md` ("Conversation Memory", §162). It holds a per-session lifecycle log for every Claude Code session and a smaller set of compressed summaries that distill reusable insight from those sessions. It is the raw input to the memory pipeline `conversation → summary → CANON`: sessions land here automatically, the durable knowledge is later promoted into `knowledge/` CANON pages, and CANON — not these logs — is the source of truth.

## How it fits
`vault/` is a data sink, not code — it imports nothing and is imported by nothing. It is written by the Claude Code session hooks (`scripts/user_prompt_capture.py`, `scripts/wiki_stop_hook.py`) via the SessionStart/Stop hook lifecycle, and read by memory-recall and knowledge-promotion tooling. It sits alongside `knowledge/` (the wiki CANON) as the pre-CANON tier of the same knowledge system.

## Structure
Everything lives under `vault/memory/`:

| Path | Files | Role |
|---|---|---|
| `memory/conversations/` | 2,717 | One file per Claude Code session, named by `session_id` (UUID). Lifecycle metadata (session start, response completions) — **metadata logs, not full transcripts.** Created by the SessionStart hook, appended by the Stop hook. |
| `memory/summaries/` | 212 | Compressed knowledge extracted from conversations. Created when a session produces reusable insight; filename form `summary_<hash>_YYYY-MM-DD_<topic>.md`. Should link into CANON pages via wikilinks. |

Per WIKI_RULES there is also an `index.md` convention indexing sessions and summaries.

## Key components
- `vault/memory/conversations/<session_id>.md` — the atomic unit. Each is a lightweight lifecycle record for one session, not a transcript dump; the actual reusable knowledge is meant to be lifted into a summary and then CANON.
- `vault/memory/summaries/summary_*.md` — the promotion tier. These are the files that carry insight forward and wikilink into `knowledge/` CANON. There are far fewer summaries (212) than conversations (2,717), reflecting that most sessions are routine and never promoted.

## Data & state
Pure file storage (markdown). Writers are the session hooks; no Neon dependency. Growth is bounded by session cadence (one conversation file per CC session) plus the trickle of hand-authored summaries. The generated-filename convention (`YYYY-MM-DD` in summary names) follows the universal rule that generated files carry a date.

## Gotchas
- **This is the top-level `vault/`, NOT `data/vault/`.** They are two separate directories. The gitignore rules `data/vault/memory/conversations/` and `data/vault/memory/summaries/` (`.gitignore` lines 63–64) apply only to the copy under `data/`. The top-level `vault/` here is simply untracked — `git ls-files vault/` returns zero — so it is neither committed nor explicitly ignored. Don't confuse the two when reasoning about what's in git. See [`data/`](data.md).
- **Conversations are metadata, not transcripts** (WIKI_RULES §169). Do not treat a `conversations/<id>.md` file as a full record of what was said; the reusable content only exists once someone writes a summary.
- **Summaries are created manually, not automatically.** The pipeline only advances if a summary is authored; unpromoted sessions leave no durable trace beyond the lifecycle log. This is by design (CANON is curated), but it means `vault/memory/summaries/` is not an exhaustive index of everything valuable that happened.
- **CANON is the source of truth, not the vault** (WIKI_RULES §188). When answering from memory, prefer `knowledge/` CANON over raw vault files — the vault is the pre-CANON, lossy tier.

## See also
- [`knowledge/`](knowledge.md) — the CANON wiki that vault summaries promote into
- [`data/`](data.md) — hosts a separate, gitignored `data/vault/memory/` copy
- [`scripts/`](scripts.md) — `user_prompt_capture.py`, `wiki_stop_hook.py` (the hook writers)
- [Data flow](../data-flow.md) · [Conventions](../conventions.md)
