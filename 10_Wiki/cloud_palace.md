---
type: palace-rules
generated: 2026-04-10
authority: mandatory
---

# Cloud Palace — Memory Palace Usage Rules

The memory palace at `10_Wiki/palace/` is a navigable, room-based view
of the codebase. This file tells AI agents how to use it.

## Structure

```
10_Wiki/palace/
  index.md            ← entry point. Lists wings and rooms.
  wings/              ← one page per top-level module (eos_ai, services, scripts, core)
  rooms/              ← one page per functional cluster (intelligence_core, substrate, ...)
```

Key navigational links: [[palace/index|Palace Index]], [[retrieval_rules|Retrieval Rules]].

Each **room** page contains:

- **Purpose** — one sentence naming the concern the room owns.
- **Core Loci** — ranked table of the highest-value files for that concern.
- **Traversal** — links back to the wing, palace, and retrieval rules.
- **Raw Paths** — plaintext file paths for grepping or direct reads.

## The four layers

- **Palace** — the whole system. One index page.
- **Wing** — a top-level module. 4 wings total.
- **Room** — a functional cluster inside a wing. 7 rooms today.
- **Locus** — a single file promoted into a room because it scored high on
  centrality, criticality, or entry-point status.

## How AI should use it

1. Translate the user's question into a **concern**.
   ("memory writes" → memory & persistence. "discord intent routing" → transports.)

2. Open the matching **room** page.

3. Read the **purpose** line — does this room actually own the concern?
   If no, walk to a neighbor room via the wing page.

4. Look at the **core loci** table. These are your files.
   Rank is `inbound*2 + outbound + critical*10 + entry*3`.

5. Follow a locus wikilink to its [[cloud|codebase graph]] page under `data/codebase_pages/files/`.

6. Only open the real source file when the graph page does not answer.

## How it stays current

The palace is **regenerated from the graph every time** `scripts/build_palace.py`
runs. Room definitions live in `ROOM_DEFS` at the top of that script.
Add or re-cluster rooms there; re-run; the palace updates deterministically.

## Extending the palace

To add a new room:

1. Edit `scripts/build_palace.py` → `ROOM_DEFS`
2. Provide `id`, `name`, `wing`, `purpose`, `prefixes`.
3. Run `python3 scripts/build_palace.py`.
4. New room page appears at `10_Wiki/palace/rooms/<id>.md`.

To retune locus promotion weights: edit `score_file()` in the same script.

## Invariants

- Palace never stores truth — it is a view over the graph.
- Loci are wikilinks, never duplicated content.
- Every room links back to its wing and to `retrieval_rules.md`.
- The palace build is idempotent: same graph → same palace.
