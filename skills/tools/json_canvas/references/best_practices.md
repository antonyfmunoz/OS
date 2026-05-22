# JSON Canvas Best Practices
Tool: JSON Canvas (jsoncanvas.org spec 1.0)
Last Updated: 2026-04-28
Source: https://jsoncanvas.org/spec/1.0/

---

# Tier 1 -- Technical Mastery

---

## Section 1: Authentication

N/A. JSON Canvas is a file format, not an API service. There are no
authentication tokens, API keys, or OAuth flows. Canvas files are read
and written directly on the filesystem. Access control is governed by
filesystem permissions and, in Obsidian, by vault-level access settings.

In EOS, canvas files live inside the Obsidian vault at `/opt/OS/knowledge/`
or `/opt/OS/data/vault/`. Standard filesystem permissions apply. No
secrets are required to create or read `.canvas` files.

---

## Section 2: Core Operations with Exact Signatures

JSON Canvas is not an SDK with method calls. The "operations" are
structured JSON read/write. Below are the exact data shapes.

### Top-level structure

```json
{
  "nodes": [GenericNodeObject, ...],
  "edges": [EdgeObject, ...]
}
```

Both `nodes` and `edges` are optional. `{}` is a valid canvas.

### GenericNodeObject (all node types inherit these)

```python
{
    "id":     str,   # required -- 16-char lowercase hex
    "type":   str,   # required -- "text" | "file" | "link" | "group"
    "x":      int,   # required -- X position (top-left corner, pixels)
    "y":      int,   # required -- Y position (top-left corner, pixels)
    "width":  int,   # required -- width in pixels
    "height": int,   # required -- height in pixels
    "color":  str    # optional -- "1"-"6" (preset) or "#RRGGBB" hex
}
```

### TextNode (extends GenericNode)

```python
{
    "type": "text",
    "text": str       # required -- Markdown-formatted content
}
```

### FileNode (extends GenericNode)

```python
{
    "type": "file",
    "file": str,      # required -- relative path within vault
    "subpath": str    # optional -- heading/block ref (starts with "#")
}
```

### LinkNode (extends GenericNode)

```python
{
    "type": "link",
    "url": str        # required -- external URL
}
```

### GroupNode (extends GenericNode)

```python
{
    "type": "group",
    "label": str,           # optional -- display label
    "background": str,      # optional -- path to background image
    "backgroundStyle": str  # optional -- "cover" | "ratio" | "repeat"
}
```

### EdgeObject

```python
{
    "id":       str,   # required -- unique identifier
    "fromNode": str,   # required -- source node ID
    "fromSide": str,   # optional -- "top" | "right" | "bottom" | "left"
    "fromEnd":  str,   # optional -- "none" | "arrow" (default: "none")
    "toNode":   str,   # required -- target node ID
    "toSide":   str,   # optional -- "top" | "right" | "bottom" | "left"
    "toEnd":    str,   # optional -- "none" | "arrow" (default: "arrow")
    "color":    str,   # optional -- canvasColor
    "label":    str    # optional -- edge label text
}
```

### Programmatic canvas creation (Python)

```python
import json
import secrets

def gen_id() -> str:
    """Generate a 16-character lowercase hex ID."""
    return secrets.token_hex(8)

def create_canvas(nodes: list[dict], edges: list[dict]) -> str:
    """Serialize a canvas to JSON string."""
    return json.dumps({"nodes": nodes, "edges": edges}, indent=2)

def text_node(x: int, y: int, w: int, h: int, text: str,
              color: str | None = None) -> dict:
    node = {
        "id": gen_id(), "type": "text",
        "x": x, "y": y, "width": w, "height": h,
        "text": text
    }
    if color:
        node["color"] = color
    return node
```

---

## Section 3: Pagination Patterns

N/A. JSON Canvas is a single JSON document per file. There are no
paginated API responses. A canvas is loaded as one atomic unit.

For very large canvases (200+ nodes), the recommendation is to split
into multiple `.canvas` files rather than trying to paginate within
a single document. This is both a performance constraint (Obsidian
rendering) and a conceptual one (focused canvases are more useful
than sprawling ones).

---

## Section 4: Rate Limits

N/A. JSON Canvas is a file format. There are no rate limits, request
quotas, or throttling. The only practical limit is filesystem I/O speed
and the rendering performance of the consuming application (Obsidian).

**Practical limit:** Obsidian begins to lag with canvases containing
200+ nodes. This is not a spec limit but a rendering constraint.
Keep individual canvas files under 150 nodes for smooth interaction.

---

## Section 5: Error Codes and Recovery

JSON Canvas has no error codes -- it is a data format, not a service.
Errors manifest as:

1. **Invalid JSON** -- File fails to parse. Recovery: validate JSON
   syntax before writing. Use `json.loads()` to verify.

2. **Missing required fields** -- Node without `id`, `type`, `x`, `y`,
   `width`, or `height`. Obsidian behavior: may silently drop the node
   or fail to render the canvas entirely.

3. **Dangling edge references** -- Edge references a node ID that does
   not exist. Obsidian behavior: silently drops the edge. No error shown.

4. **Duplicate IDs** -- Two nodes or a node and an edge share the same ID.
   Obsidian behavior: undefined. May render only one, may corrupt on save.

5. **Wrong type values** -- `type` set to something other than `text`,
   `file`, `link`, `group`. Obsidian behavior: ignores the node.

6. **Color as integer** -- Using `1` instead of `"1"` for preset colors.
   Obsidian may not apply the color or may fail to parse the node.

### Recovery strategy

Always validate after writing:

```python
import json

def validate_canvas(filepath: str) -> list[str]:
    """Return a list of validation errors, empty if valid."""
    errors = []
    with open(filepath) as f:
        data = json.load(f)

    node_ids = set()
    edge_ids = set()

    for node in data.get("nodes", []):
        nid = node.get("id")
        if nid in node_ids or nid in edge_ids:
            errors.append(f"Duplicate ID: {nid}")
        node_ids.add(nid)

        for field in ("id", "type", "x", "y", "width", "height"):
            if field not in node:
                errors.append(f"Node {nid} missing required field: {field}")

        ntype = node.get("type")
        if ntype == "text" and "text" not in node:
            errors.append(f"Text node {nid} missing 'text' field")
        elif ntype == "file" and "file" not in node:
            errors.append(f"File node {nid} missing 'file' field")
        elif ntype == "link" and "url" not in node:
            errors.append(f"Link node {nid} missing 'url' field")

    for edge in data.get("edges", []):
        eid = edge.get("id")
        if eid in node_ids or eid in edge_ids:
            errors.append(f"Duplicate ID: {eid}")
        edge_ids.add(eid)

        for ref in ("fromNode", "toNode"):
            target = edge.get(ref)
            if target and target not in node_ids:
                errors.append(f"Edge {eid} references nonexistent {ref}: {target}")

    return errors
```

---

## Section 6: SDK Idioms

There is no official JSON Canvas SDK. The format is designed to be
consumed with standard JSON libraries in any language.

### Python idiom (recommended for EOS)

```python
import json
import secrets
from pathlib import Path

class Canvas:
    """Minimal canvas builder for programmatic creation."""

    def __init__(self):
        self.nodes: list[dict] = []
        self.edges: list[dict] = []
        self._ids: set[str] = set()

    def _gen_id(self) -> str:
        while True:
            new_id = secrets.token_hex(8)
            if new_id not in self._ids:
                self._ids.add(new_id)
                return new_id

    def add_text(self, x: int, y: int, w: int, h: int,
                 text: str, color: str | None = None) -> str:
        nid = self._gen_id()
        node = {"id": nid, "type": "text", "x": x, "y": y,
                "width": w, "height": h, "text": text}
        if color:
            node["color"] = color
        self.nodes.append(node)
        return nid

    def add_file(self, x: int, y: int, w: int, h: int,
                 file: str, subpath: str | None = None) -> str:
        nid = self._gen_id()
        node = {"id": nid, "type": "file", "x": x, "y": y,
                "width": w, "height": h, "file": file}
        if subpath:
            node["subpath"] = subpath
        self.nodes.append(node)
        return nid

    def add_link(self, x: int, y: int, w: int, h: int,
                 url: str) -> str:
        nid = self._gen_id()
        node = {"id": nid, "type": "link", "x": x, "y": y,
                "width": w, "height": h, "url": url}
        self.nodes.append(node)
        return nid

    def add_group(self, x: int, y: int, w: int, h: int,
                  label: str | None = None, color: str | None = None) -> str:
        nid = self._gen_id()
        node = {"id": nid, "type": "group", "x": x, "y": y,
                "width": w, "height": h}
        if label:
            node["label"] = label
        if color:
            node["color"] = color
        self.nodes.append(node)
        return nid

    def connect(self, from_id: str, to_id: str,
                from_side: str | None = None,
                to_side: str | None = None,
                label: str | None = None,
                color: str | None = None) -> str:
        eid = self._gen_id()
        edge = {"id": eid, "fromNode": from_id, "toNode": to_id}
        if from_side:
            edge["fromSide"] = from_side
        if to_side:
            edge["toSide"] = to_side
        if label:
            edge["label"] = label
        if color:
            edge["color"] = color
        self.edges.append(edge)
        return eid

    def save(self, filepath: str | Path) -> None:
        with open(filepath, "w") as f:
            json.dump({"nodes": self.nodes, "edges": self.edges}, f, indent=2)
```

### Loading and modifying an existing canvas

```python
def load_canvas(filepath: str) -> dict:
    with open(filepath) as f:
        return json.load(f)

def save_canvas(filepath: str, data: dict) -> None:
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

# Modify pattern:
canvas = load_canvas("path/to/canvas.canvas")
existing_ids = {n["id"] for n in canvas["nodes"]} | {e["id"] for e in canvas["edges"]}
# ... add nodes/edges, ensuring IDs do not collide with existing_ids
save_canvas("path/to/canvas.canvas", canvas)
```

---

## Section 7: Anti-Patterns

### Anti-Pattern 1: Literal backslash-n in text

```python
# WRONG -- renders as literal \n characters in Obsidian
{"text": "Line one\\nLine two"}

# CORRECT -- JSON newline escape, renders as actual line break
{"text": "Line one\nLine two"}
```

### Anti-Pattern 2: Integer color presets

```python
# WRONG -- integer not parsed correctly
{"color": 1}

# CORRECT -- string preset
{"color": "1"}
```

### Anti-Pattern 3: Explicit children array for groups

```python
# WRONG -- groups do not have a children property
{"type": "group", "children": ["node1", "node2"], ...}

# CORRECT -- containment is purely positional
# Place child nodes so their x/y/width/height fall within the group bounds
```

### Anti-Pattern 4: Using uuid4 for IDs

```python
# WRONG -- Obsidian generates 16-char hex, not UUIDs
import uuid
node_id = str(uuid.uuid4())  # "a3b2c1d0-e9f8-..."

# CORRECT -- 16-character lowercase hex
import secrets
node_id = secrets.token_hex(8)  # "a3b2c1d0e9f8a7b6"
```

### Anti-Pattern 5: Overlapping nodes without groups

```python
# WRONG -- nodes stacked at same position create visual mess
{"x": 0, "y": 0, "width": 300, "height": 200, ...}
{"x": 0, "y": 0, "width": 300, "height": 200, ...}

# CORRECT -- offset by at least width + 50px gap
{"x": 0, "y": 0, "width": 300, "height": 200, ...}
{"x": 350, "y": 0, "width": 300, "height": 200, ...}
```

### Anti-Pattern 6: Group after children in array order

```python
# WRONG -- children render behind group (hidden)
nodes = [child_node, group_node]

# CORRECT -- group first, then children (z-index = array position)
nodes = [group_node, child_node]
```

### Anti-Pattern 7: Dangling edges after node deletion

```python
# WRONG -- removing a node without cleaning up its edges
canvas["nodes"] = [n for n in canvas["nodes"] if n["id"] != target_id]
# Edges referencing target_id still exist -> silently dropped by Obsidian

# CORRECT -- remove node AND its edges
canvas["nodes"] = [n for n in canvas["nodes"] if n["id"] != target_id]
canvas["edges"] = [e for e in canvas["edges"]
                   if e["fromNode"] != target_id and e["toNode"] != target_id]
```

---

## Section 8: Data Model

### Entity hierarchy

```
Canvas (file)
  +-- nodes[] (array of GenericNode)
  |     +-- TextNode    (has: text)
  |     +-- FileNode    (has: file, subpath?)
  |     +-- LinkNode    (has: url)
  |     +-- GroupNode   (has: label?, background?, backgroundStyle?)
  +-- edges[] (array of Edge)
        +-- Edge        (has: fromNode, toNode, fromSide?, toSide?,
                               fromEnd?, toEnd?, color?, label?)
```

### Key relationships

- **Edges reference Nodes** via `fromNode` / `toNode` string IDs.
  This is a loose foreign key -- no referential integrity enforced.
- **Groups contain Nodes** implicitly via spatial overlap.
  No explicit parent-child reference exists in the data model.
- **IDs are shared namespace** -- a node and an edge cannot have the
  same ID. All IDs must be globally unique within one `.canvas` file.
- **File nodes reference vault paths** -- the `file` field is relative
  to the vault root, not the canvas file location.

### Immutable design decisions

- No nesting of canvases (a canvas cannot embed another canvas).
- No animation, timing, or sequencing data -- static layout only.
- No computed positions -- all coordinates are absolute pixels.
- No metadata/frontmatter -- the entire file is a single JSON object.

---

## Section 9: Webhooks and Events

N/A. JSON Canvas is a static file format. There are no webhooks,
event subscriptions, or push notifications.

In Obsidian, the `workspace` event API can detect when a canvas file
is opened or modified, but this is Obsidian plugin territory, not
part of the JSON Canvas spec itself.

For EOS, canvas file changes can be detected via filesystem watchers
(inotifywait, watchdog) if reactive behavior is needed.

---

## Section 10: Limits

### Spec-level limits

The JSON Canvas spec defines no hard limits on node count, edge count,
canvas size, or coordinate ranges. All values are integers (no floats).

### Practical limits (Obsidian rendering)

| Dimension | Practical Limit | Notes |
|-----------|-----------------|-------|
| Nodes per canvas | ~200 | Beyond this, pan/zoom becomes laggy |
| Edges per canvas | ~300 | Dense edge networks slow rendering |
| Text length per node | ~10,000 chars | Longer text overflows visually |
| Canvas file size | ~2 MB | Larger files slow Obsidian load time |
| Coordinate range | -100,000 to +100,000 | Extreme values make navigation difficult |
| Nested group depth | 3-4 levels | Deeper nesting gets confusing visually |
| ID length | 16 chars hex | Convention, not enforced by spec |

### File size considerations

A canvas with 100 text nodes and 100 edges is approximately 15-25 KB.
A canvas with 500 nodes approaches 100+ KB. Files over 500 KB should
be split.

---

## Section 11: Cost Model

N/A. JSON Canvas is an open, free specification. There are no API costs,
per-request charges, or usage quotas. The format is MIT-licensed.

The only cost is storage (negligible -- canvas files are small JSON)
and the compute time for Obsidian to render them (free).

---

## Section 12: Version Pinning

### Current version

JSON Canvas spec **1.0** -- released as the initial and currently only
version. The spec is maintained by the Obsidian team at
https://github.com/obsidianmd/jsoncanvas.

### Versioning approach

The spec does not include a version field in the JSON document itself.
There is no `"version": "1.0"` key. Consuming applications must infer
compatibility from the file extension (`.canvas`) and the presence of
recognized fields.

### Deprecation risk

Low. The spec was designed to be minimal and stable. The Obsidian team
has stated the format is intended to be a long-term standard. No
breaking changes are anticipated. Additional node types or attributes
could be added in future versions as backward-compatible extensions.

### Pinning recommendation

For EOS, no version pinning is needed. If future spec versions add
new node types, existing canvases will continue to work. Unknown
fields should be preserved when reading and rewriting canvases
(do not strip unrecognized keys).

---

# Tier 2 -- Creator Intelligence

---

## Section 13: Design Intent and Tradeoffs

### Why JSON Canvas exists

JSON Canvas was created by the Obsidian team (Shida Li and Erica Xu)
to solve a specific problem: infinite canvas tools all used proprietary
formats, creating lock-in. The design intent was to create the simplest
possible open format that captures spatial arrangement of information
with connections.

### Core design philosophy

1. **Minimal by design** -- The spec intentionally omits styling,
   theming, animation, and advanced layout. The format captures
   *structure and position*, not presentation.

2. **File-first, not API-first** -- JSON Canvas is a file format,
   not a service. This means no vendor dependency, no API versioning
   headaches, and full offline capability.

3. **Spatial thinking as primitive** -- The format treats 2D position
   as a first-class concept. Unlike Markdown (linear) or graph formats
   (topology-only), JSON Canvas preserves the spatial reasoning that
   happens on a whiteboard.

4. **Interoperability over features** -- The spec deliberately stays
   small so that any tool can implement it. This is why there are only
   4 node types and one edge type.

### Conscious tradeoffs

- **No computed layout** -- All positions are absolute. There is no
  auto-layout algorithm in the spec. Trade: manual positioning work
  in exchange for exact control and simplicity.
- **No semantic relationships** -- Edges have labels but no types or
  schemas. Trade: flexibility over structured reasoning.
- **No history/undo** -- The format is a snapshot, not a timeline.
  Trade: simplicity over collaboration features.
- **Groups are spatial, not hierarchical** -- No `children` array.
  Trade: simpler format, but programmatic group management requires
  coordinate math.

### What JSON Canvas is NOT

- Not a graph database format (use JSON-LD, RDF, or Neo4j exports).
- Not a diagramming standard (use Mermaid, PlantUML, or Draw.io XML).
- Not a presentation format (use Reveal.js or PPTX).
- Not a collaborative editing format (use CRDT-based formats).

---

## Section 14: Problem-Solution Map and Hidden Capabilities

### Problems JSON Canvas solves well

1. **Visual thinking capture** -- Brain dumps, mind maps, concept
   exploration where spatial proximity implies relationship.
2. **Architecture documentation** -- System diagrams that live
   alongside the code they document (in the vault).
3. **Project boards** -- Kanban-style boards using groups as columns
   and text nodes as cards.
4. **Research synthesis** -- Connecting papers (file nodes), URLs
   (link nodes), and notes (text nodes) in spatial context.
5. **Decision trees and flowcharts** -- Using edges with labels
   for branching logic.

### Hidden capabilities

1. **Canvas as index** -- A canvas file can serve as a visual table
   of contents by using file nodes to reference every important
   document in a section of the vault. This is more discoverable
   than a markdown index for spatial thinkers.

2. **Layered information architecture** -- Since z-index is array
   order, you can create "background context" nodes (large, muted
   color groups) with "foreground action" nodes on top. This
   creates visual hierarchy without any CSS.

3. **Edge labels as metadata** -- Edge labels are not just decorative.
   Using consistent label vocabulary ("depends on", "blocks",
   "feeds into", "replaces") creates a queryable relationship
   language when canvases are parsed programmatically.

4. **Color as status encoding** -- Preset colors 1-6 can encode
   status (1=red=blocked, 3=yellow=in progress, 4=green=done).
   This turns any canvas into a status dashboard.

5. **Programmatic canvas generation** -- Since the format is plain
   JSON, any script can generate canvases. This enables
   auto-generated architecture diagrams, dependency graphs,
   or CRM relationship maps that stay in sync with live data.

---

## Section 15: Operational Behavior and Edge Cases

### Obsidian-specific behavioral quirks

1. **Save-on-close vs auto-save** -- Obsidian auto-saves canvas
   changes. If you write a `.canvas` file while Obsidian has it
   open, Obsidian may overwrite your changes on its next auto-save.
   Workaround: close the canvas tab in Obsidian before writing
   programmatically, or write to a new file.

2. **File node path resolution** -- The `file` field in file nodes
   is resolved relative to the vault root, NOT relative to the
   canvas file location. If the vault root is `/opt/OS/data/vault/`
   and you want to embed `notes/idea.md`, use `"file": "notes/idea.md"`,
   not `"file": "../notes/idea.md"`.

3. **Canvas drag changes coordinates** -- When a user drags nodes
   in Obsidian, coordinates update in real time. Programmatic
   layouts will be overwritten if the user moves anything. Accept
   that human-edited canvases will drift from generated layouts.

4. **Empty canvas handling** -- Obsidian opens `{}` or
   `{"nodes":[],"edges":[]}` without error but shows a blank canvas.
   Some third-party tools may reject `{}` and require both arrays.
   Always include both arrays for maximum compatibility.

5. **Markdown rendering in text nodes** -- Text nodes support full
   Obsidian Markdown including wikilinks (`[[page]]`), tags
   (`#tag`), callouts, and math blocks. However, complex Markdown
   (tables, long code blocks) renders poorly in small nodes.
   Keep text nodes focused -- use file nodes for complex content.

6. **Concurrent file access** -- If two processes write the same
   `.canvas` file simultaneously, last-write-wins. There is no
   merge or conflict resolution. For EOS scripts that generate
   canvases, always use unique filenames or write to temp files
   and rename atomically.

7. **Floating point coordinates** -- The spec says `integer` but
   Obsidian sometimes writes floating point values after drag
   operations. When reading canvases, accept float and round to
   int when writing.

---

## Section 16: Ecosystem Position and Composition

### Where JSON Canvas sits

```
[Knowledge Sources] -> [Markdown Notes] -> [Canvas (spatial layer)]
                                        -> [Dataview (query layer)]
                                        -> [Graph View (link layer)]
```

JSON Canvas is the **spatial reasoning layer** in a knowledge
management stack. It complements but does not replace:

- **Markdown** -- for linear, detailed content.
- **Dataview** -- for structured queries across notes.
- **Graph View** -- for automated link visualization.

Canvas is manual and intentional. Graph View is automatic and
comprehensive. They serve different cognitive modes.

### Natural complements in EOS

| Tool | How it pairs with Canvas |
|------|--------------------------|
| Obsidian Markdown | File nodes embed .md notes into spatial context |
| Mermaid | For auto-generated diagrams; canvas for hand-curated ones |
| Python scripts | Generate canvases programmatically from data |
| Wiki system | Canvas serves as visual index for wiki sections |
| Memory palace | Room diagrams can be canvas files |

### Integration anti-patterns

- **Don't generate canvases from graph view data** -- Graph view
  already provides automatic spatial layout. Duplicating it in
  canvas format adds maintenance burden with no value.
- **Don't use canvas for data that changes frequently** -- Canvases
  are snapshots. If the underlying data changes daily, the canvas
  goes stale. Use Dataview queries for dynamic content.
- **Don't embed canvases in canvases** -- The spec does not support
  recursive embedding. Use file nodes pointing to other canvases
  for multi-level navigation.

---

## Section 17: Trajectory and Evolution

### Current state (2026)

JSON Canvas spec 1.0 has been stable since its release. No spec
revisions have been published. The format has seen adoption by:

- Obsidian (native support)
- Kinopio (import/export)
- Several community tools on GitHub

### Expected trajectory

The spec is intentionally minimal. Future extensions may include:

- Additional node types (table, embed, canvas-in-canvas)
- Metadata/frontmatter for canvas-level properties
- Constraints or snap-to-grid hints
- Annotation layer (comments, highlights)

### Deprecation risk

Very low. The spec is MIT-licensed and maintained by Obsidian's core
team. The deliberate simplicity means there is little to deprecate.
If Obsidian adds new node types, they will likely be additive and
backward-compatible.

### Build recommendation

Safe to build on. The format is stable enough for production use in
EOS. If the spec evolves, unknown fields will be preserved by any
well-written parser (follow the principle of being liberal in what
you accept).

---

## Section 18: Conceptual Model and Solution Recipes

### Mental model

Think of JSON Canvas as a **programmatic whiteboard**. The primitives are:

- **Nodes** = sticky notes, printouts, and URL bookmarks pinned to a board
- **Edges** = strings connecting pins between sticky notes
- **Groups** = drawn rectangles that visually contain related notes
- **Position** = where you place something matters (proximity = relationship)

The key insight: spatial position IS the data structure. Two nodes
placed near each other communicate "related" without any explicit link.
Edges make relationships explicit and directional.

### Recipe 1: Architecture diagram from module list

```python
# Given: list of Python modules with dependencies
modules = {"core": ["db", "config"], "api": ["core"], "ui": ["api"]}

canvas = Canvas()
col = 0
node_ids = {}
for module, deps in modules.items():
    nid = canvas.add_text(col * 350, 0, 300, 100, f"# {module}")
    node_ids[module] = nid
    col += 1

for module, deps in modules.items():
    for dep in deps:
        if dep in node_ids:
            canvas.connect(node_ids[module], node_ids[dep],
                          from_side="left", to_side="right",
                          label="depends on")

canvas.save("/opt/OS/knowledge/architecture.canvas")
```

### Recipe 2: Kanban board with status groups

```python
canvas = Canvas()
statuses = [("To Do", "1"), ("In Progress", "3"), ("Done", "4")]
group_ids = {}

for i, (label, color) in enumerate(statuses):
    gid = canvas.add_group(i * 350, 0, 300, 600, label=label, color=color)
    group_ids[label] = (gid, i * 350)

# Add task cards inside groups
tasks = [("Task A", "To Do"), ("Task B", "In Progress"), ("Task C", "Done")]
for j, (task, status) in enumerate(tasks):
    gx = group_ids[status][1]
    canvas.add_text(gx + 20, 50 + j * 120, 260, 80, f"## {task}")

canvas.save("/opt/OS/knowledge/board.canvas")
```

### Recipe 3: Research synthesis canvas

```python
canvas = Canvas()
# Central question
center = canvas.add_text(300, 200, 400, 200,
    "# Research Question\n\nHow does X affect Y?", color="5")

# Sources
sources = [
    ("file", "Papers/study_a.pdf", 0, 0),
    ("file", "Notes/meeting.md", 0, 200),
    ("link", "https://example.com/data", 0, 400),
]
for kind, ref, sx, sy in sources:
    if kind == "file":
        sid = canvas.add_file(sx, sy, 250, 150, ref)
    else:
        sid = canvas.add_link(sx, sy, 250, 100, ref)
    canvas.connect(sid, center, from_side="right", to_side="left",
                  label="informs")

canvas.save("/opt/OS/knowledge/research.canvas")
```

### Recipe 4: Decision tree with branching edges

```python
canvas = Canvas()
start = canvas.add_text(200, 0, 200, 60, "**Start: Evaluate Lead**", color="4")
q1 = canvas.add_text(200, 120, 200, 80, "Revenue > $1M?", color="3")
yes1 = canvas.add_text(450, 120, 200, 60, "High Priority")
no1 = canvas.add_text(-50, 120, 200, 60, "Standard Track", color="2")

canvas.connect(start, q1, from_side="bottom", to_side="top")
canvas.connect(q1, yes1, from_side="right", to_side="left",
              label="Yes", color="4")
canvas.connect(q1, no1, from_side="left", to_side="right",
              label="No", color="1")

canvas.save("/opt/OS/knowledge/decision_tree.canvas")
```

### Recipe 5: Auto-generated dependency graph

```python
import ast
from pathlib import Path

canvas = Canvas()
module_dir = Path("/opt/OS/eos_ai")
positions = {}
row = 0

for py_file in sorted(module_dir.glob("*.py")):
    name = py_file.stem
    nid = canvas.add_text(0, row * 120, 250, 80, f"## {name}")
    positions[name] = nid
    row += 1

# Parse imports and create edges
for py_file in sorted(module_dir.glob("*.py")):
    name = py_file.stem
    try:
        tree = ast.parse(py_file.read_text())
    except SyntaxError:
        continue
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            parts = node.module.split(".")
            if len(parts) >= 2 and parts[0] == "eos_ai":
                dep = parts[1]
                if dep in positions and name in positions:
                    canvas.connect(positions[name], positions[dep],
                                  label="imports")

canvas.save("/opt/OS/knowledge/deps.canvas")
```

---

## Section 19: Industry Expert and Cutting-Edge Usage

### Expert patterns observed in the Obsidian community

1. **Canvas as MOC (Map of Content)** -- Power users create one canvas
   per major topic area that serves as a visual MOC. File nodes point
   to the key documents. This is more intuitive for spatial thinkers
   than a markdown list of links.

2. **Daily canvas journaling** -- Some users create a daily canvas
   instead of a daily note, placing thoughts spatially and connecting
   them as the day progresses. This captures associative thinking
   that linear journaling misses.

3. **Canvas-driven project management** -- Teams use shared vaults
   with canvas files as project boards. Groups represent sprints or
   status columns. Color encodes priority. This replaces Trello/Jira
   for small teams.

4. **Programmatic canvas dashboards** -- Scripts generate canvas files
   from live data (GitHub issues, CRM records, financial data) and
   write them into the vault. The canvas auto-updates on a schedule,
   creating a visual dashboard inside Obsidian.

5. **Multi-canvas navigation** -- Large projects use a "root canvas"
   with file nodes pointing to sub-canvases. This creates a zoomable
   hierarchy: root canvas (high level) -> topic canvases (detail) ->
   individual notes (implementation).

### AI-powered patterns

1. **LLM-generated canvases** -- AI agents analyze a codebase or
   document set and produce a canvas showing relationships, clusters,
   and gaps. The AI handles the tedious coordinate math; the human
   does the spatial reasoning on the result.

2. **Canvas as agent output** -- Instead of generating long text
   reports, agents produce canvas files that present findings
   spatially. A code review agent could produce a canvas with
   file nodes (reviewed files), text nodes (findings), and edges
   (dependency chains).

3. **Diff-aware canvas updates** -- Scripts that regenerate canvases
   can diff against the previous version and only update changed
   nodes, preserving any manual repositioning the user has done.
   This requires tracking node IDs across regeneration cycles.

### EOS-specific cutting-edge usage

1. **Memory palace rooms as canvases** -- Each room in the memory
   palace (knowledge/palace/rooms/) could have a companion canvas
   that spatially arranges the room's key files and concepts.

2. **Agent hierarchy visualization** -- Auto-generate a canvas from
   `agent_hierarchy.py` showing the org chart with edges representing
   reporting lines and authority boundaries.

3. **Venture portfolio map** -- A canvas showing all ventures in the
   conglomerate with edges for shared resources, color for stage
   (pre-revenue = red, generating = green), and groups for
   corporate entities.

4. **Build session timeline** -- After a build session, auto-generate
   a canvas showing files modified, in spatial layout by directory,
   with edges showing the order of changes.

---

# EOS Usage Patterns

## Where canvas files live

- **Wiki canvases:** `/opt/OS/knowledge/*.canvas` -- architecture diagrams,
  concept maps, visual indexes for wiki sections.
- **Vault canvases:** `/opt/OS/data/vault/*.canvas` -- personal planning,
  project boards, research synthesis.
- **Generated canvases:** Written by EOS scripts into either location
  depending on whether they document the system (Wiki) or support
  the founder's thinking (vault).

## Naming convention

Canvas files follow EOS naming: lowercase, hyphens, descriptive.

- `architecture-overview.canvas`
- `eos-agent-hierarchy.canvas`
- `2026-04-28-build-session.canvas` (date-prefixed for temporal canvases)

## When to use canvas vs other formats

| Need | Format |
|------|--------|
| Linear documentation | Markdown (.md) |
| Structured data queries | Dataview in .md |
| Automatic link graphs | Obsidian Graph View |
| Spatial reasoning / manual arrangement | Canvas (.canvas) |
| Auto-generated diagrams in docs | Mermaid in .md |
| Interactive visual planning | Canvas (.canvas) |

## Canvas generation in EOS agents

Any EOS agent that produces visual output should:

1. Use the `Canvas` class pattern from Section 6 (or equivalent).
2. Generate unique IDs with `secrets.token_hex(8)`.
3. Validate the output with the checker from Section 5.
4. Write to the appropriate vault location.
5. Log the canvas path so the founder can open it in Obsidian.

---

# Gotchas

1. **Newline encoding in JSON strings** -- Use `\n` (JSON escape) not
   `\\n` (literal backslash-n). The latter renders as visible `\n`
   characters in Obsidian text nodes. This is the single most common
   mistake when generating canvases programmatically.

2. **Group z-order must precede children** -- Groups must appear before
   their contained nodes in the `nodes` array. If a child node appears
   before its group, the group renders on top and hides the child.
   Always insert group nodes first, then their children.

3. **Color presets are strings, never integers** -- `"color": "1"` is
   correct. `"color": 1` breaks color parsing. This applies to both
   node colors and edge colors. The spec explicitly defines canvasColor
   as a string type.

4. **File node paths are vault-relative, not canvas-relative** -- A
   file node's `file` field resolves from the vault root. If your vault
   is at `/opt/OS/data/vault/` and you want to embed `diagrams/arch.png`,
   use `"file": "diagrams/arch.png"`, not a relative path from the
   canvas file's directory.

5. **IDs share a single namespace across nodes AND edges** -- A node ID
   `"abc123"` and an edge ID `"abc123"` would be a collision. Always
   generate IDs from a single pool and check both arrays for uniqueness.
   Using `secrets.token_hex(8)` with collision checking handles this.

6. **Obsidian auto-save can overwrite programmatic changes** -- If a
   canvas is open in Obsidian when a script writes to the same file,
   Obsidian's auto-save may overwrite the script's changes. Always
   close the canvas tab in Obsidian before running generation scripts,
   or write to a new file and let the user open it.

7. **No referential integrity enforcement** -- The spec does not
   prevent dangling edges. If you delete a node, you must manually
   clean up all edges referencing it. Obsidian silently drops broken
   edges without warning, so you may not notice the data loss until
   you inspect the file.

8. **Floating point coordinates from Obsidian** -- After a user drags
   nodes in Obsidian, coordinates may become floating point values
   even though the spec says integer. When reading canvases written
   by Obsidian, accept float values. When writing, always use integers
   for clean grid alignment.

9. **Large canvas performance cliff** -- Canvases with 200+ nodes
   hit a rendering performance cliff in Obsidian. The degradation is
   not gradual -- it goes from smooth to laggy quickly. Plan canvas
   splits before hitting this limit, not after.

10. **Wikilinks in text nodes require vault context** -- Text nodes
    support `[[wikilinks]]` but they only resolve if the canvas is
    opened in Obsidian with the correct vault. If you share the
    `.canvas` file outside the vault, wikilinks become dead text.
