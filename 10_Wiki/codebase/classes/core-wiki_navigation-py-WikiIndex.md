---
type: codebase-class
file: core/wiki_navigation.py
line: 50
generated: 2026-04-12
---

# WikiIndex

**File:** [[core-wiki_navigation-py]] | **Line:** 50

Bidirectional index between graph nodes and wiki knowledge pages.

Sources:
    1. Summary promoted_to fields (summary → wiki slug → graph nodes)
    2. Wiki page wikilinks (wiki page → referenced graph nodes)
...

## Methods

- [[core-wiki_navigation-py-WikiIndex-__init__]]`() → None` — 
- [[core-wiki_navigation-py-WikiIndex-build]]`(graph) → 'WikiIndex'` — Build the index. Cheap — file scan only, no embeddings.
- [[core-wiki_navigation-py-WikiIndex-_scan_wiki_pages]]`() → None` — Index all wiki knowledge pages and their outgoing wikilinks.
- [[core-wiki_navigation-py-WikiIndex-_scan_summaries]]`() → None` — Parse promoted_to from summary frontmatter.
- [[core-wiki_navigation-py-WikiIndex-_map_nodes_to_wiki]]`(graph) → None` — Map graph node IDs to wiki slugs via deterministic rules.
- [[core-wiki_navigation-py-WikiIndex-_compute_incoming_counts]]`() → None` — Count incoming wikilinks for each wiki slug.
- [[core-wiki_navigation-py-WikiIndex-get_wiki_for_node]]`(node_id) → dict | None` — Return wiki metadata for a graph node, or None.
- [[core-wiki_navigation-py-WikiIndex-get_nodes_for_slug]]`(slug) → list[str]` — Return graph node IDs mapped to a wiki slug.
- [[core-wiki_navigation-py-WikiIndex-is_operational]]`(slug) → bool` — True if this slug is an operational/meta file (no bonus).
