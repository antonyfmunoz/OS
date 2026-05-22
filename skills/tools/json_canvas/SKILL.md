---
name: json_canvas
description: "Use when creating or editing JSON Canvas (.canvas) files — nodes, edges, groups, connections, visual canvases, mind maps, or flowcharts in Obsidian."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://jsoncanvas.org/spec/1.0/"
last_researched: "2026-04-28"
api_version: "JSON Canvas Spec 1.0"
speed_category: "slow"
trigger: both
effort: medium
context: fork
---

# Tool: JSON Canvas

## What This Tool Does

JSON Canvas is an open file format for infinite canvas data, used by Obsidian and other tools. A `.canvas` file is a JSON document containing two top-level arrays: `nodes` (objects placed on the canvas) and `edges` (connections between nodes). The format supports text nodes with Markdown, file embeds, external links, visual groups, and directional edges with labels and colors.

Core capabilities:
- **Text nodes** -- Markdown-formatted content blocks positioned on an infinite 2D plane
- **File nodes** -- Embed files from the vault (images, PDFs, notes) with optional subpath anchors
- **Link nodes** -- Embed external URLs as preview cards
- **Group nodes** -- Visual containers that organize child nodes
- **Edges** -- Directional connections between any two nodes with optional labels, colors, and side anchors
- **Colors** -- Preset palette (`"1"`-`"6"`) or hex values for nodes and edges

## EOS Integration

Canvas files live in the Obsidian vault at `/opt/OS/knowledge/` or `/opt/OS/data/vault/`. They are used for visual planning, architecture diagrams, mind maps, and project boards. The Wiki system treats `.canvas` files as first-class documents alongside `.md` files.

**Agents that use JSON Canvas:** Any agent producing visual plans, architecture maps, or relationship diagrams writes `.canvas` files into the vault.

**Obsidian sync:** Canvas files are picked up by Obsidian automatically. No rebuild or restart needed -- just save the file.

## Quick Reference

### File Structure

```json
{
  "nodes": [],
  "edges": []
}
```

Both arrays are optional. An empty canvas is `{}` or `{"nodes":[],"edges":[]}`.

### ID Generation

All node and edge IDs are **16-character lowercase hexadecimal strings** (64-bit random value):

```
"6f0ad84f44ce9c17"
"a3b2c1d0e9f8a7b6"
```

IDs must be unique across both nodes and edges in the same file.

### Generic Node Attributes (all node types)

| Attribute | Required | Type | Description |
|-----------|----------|------|-------------|
| `id` | Yes | string | Unique 16-char hex identifier |
| `type` | Yes | string | `text`, `file`, `link`, or `group` |
| `x` | Yes | integer | X position in pixels (top-left corner) |
| `y` | Yes | integer | Y position in pixels (top-left corner) |
| `width` | Yes | integer | Width in pixels |
| `height` | Yes | integer | Height in pixels |
| `color` | No | canvasColor | Preset `"1"`-`"6"` or hex (e.g., `"#FF0000"`) |

### Text Nodes

Additional attribute: `text` (required) -- plain text with Markdown syntax.

```json
{
  "id": "6f0ad84f44ce9c17",
  "type": "text",
  "x": 0,
  "y": 0,
  "width": 400,
  "height": 200,
  "text": "# Hello World\n\nThis is **Markdown** content."
}
```

### File Nodes

Additional attributes: `file` (required) -- path to file within the system; `subpath` (optional) -- link to heading or block (starts with `#`).

```json
{
  "id": "a1b2c3d4e5f67890",
  "type": "file",
  "x": 500,
  "y": 0,
  "width": 400,
  "height": 300,
  "file": "Attachments/diagram.png"
}
```

### Link Nodes

Additional attribute: `url` (required) -- external URL.

```json
{
  "id": "c3d4e5f678901234",
  "type": "link",
  "x": 1000,
  "y": 0,
  "width": 400,
  "height": 200,
  "url": "https://obsidian.md"
}
```

### Group Nodes

Groups are visual containers. Position child nodes inside the group's bounds.

Additional attributes: `label` (optional) -- text label; `background` (optional) -- path to background image; `backgroundStyle` (optional) -- `cover`, `ratio`, or `repeat`.

```json
{
  "id": "d4e5f6789012345a",
  "type": "group",
  "x": -50,
  "y": -50,
  "width": 1000,
  "height": 600,
  "label": "Project Overview",
  "color": "4"
}
```

### Edges

Edges connect nodes via `fromNode` and `toNode` IDs.

| Attribute | Required | Type | Default | Description |
|-----------|----------|------|---------|-------------|
| `id` | Yes | string | - | Unique identifier |
| `fromNode` | Yes | string | - | Source node ID |
| `fromSide` | No | string | - | `top`, `right`, `bottom`, or `left` |
| `fromEnd` | No | string | `none` | `none` or `arrow` |
| `toNode` | Yes | string | - | Target node ID |
| `toSide` | No | string | - | `top`, `right`, `bottom`, or `left` |
| `toEnd` | No | string | `arrow` | `none` or `arrow` |
| `color` | No | canvasColor | - | Line color |
| `label` | No | string | - | Text label |

```json
{
  "id": "0123456789abcdef",
  "fromNode": "6f0ad84f44ce9c17",
  "fromSide": "right",
  "toNode": "a1b2c3d4e5f67890",
  "toSide": "left",
  "toEnd": "arrow",
  "label": "leads to"
}
```

### Colors

The `canvasColor` type accepts either a hex string or a preset number:

| Preset | Color |
|--------|-------|
| `"1"` | Red |
| `"2"` | Orange |
| `"3"` | Yellow |
| `"4"` | Green |
| `"5"` | Cyan |
| `"6"` | Purple |

Preset color values are intentionally undefined -- applications use their own brand colors.

### Layout Guidelines

- Coordinates can be negative (canvas extends infinitely)
- `x` increases right, `y` increases down; position is the top-left corner
- Space nodes 50-100px apart; leave 20-50px padding inside groups
- Align to grid (multiples of 10 or 20) for cleaner layouts
- Array order in `nodes` determines z-index: first node = bottom layer, last node = top layer

| Node Type | Suggested Width | Suggested Height |
|-----------|-----------------|------------------|
| Small text | 200-300 | 80-150 |
| Medium text | 300-450 | 150-300 |
| Large text | 400-600 | 300-500 |
| File preview | 300-500 | 200-400 |
| Link preview | 250-400 | 100-200 |

### Common Workflows

**Create a new canvas:**
1. Create a `.canvas` file with `{"nodes": [], "edges": []}`
2. Generate unique 16-character hex IDs for each node
3. Add nodes with required fields: `id`, `type`, `x`, `y`, `width`, `height`
4. Add edges referencing valid node IDs via `fromNode` and `toNode`
5. Validate: parse the JSON, verify all edge references resolve

**Add a node to existing canvas:**
1. Read and parse the existing `.canvas` file
2. Generate a unique ID that does not collide with existing IDs
3. Choose position (`x`, `y`) that avoids overlapping (50-100px spacing)
4. Append node to `nodes` array, optionally add edges
5. Validate: all IDs unique, all edge references resolve

**Connect two nodes:**
1. Generate a unique edge ID
2. Set `fromNode`, `toNode`, optionally `fromSide`/`toSide` and `label`
3. Append edge to `edges` array
4. Validate: both node IDs exist

### Validation Checklist

After creating or editing any canvas file, verify:

1. All `id` values are unique across both nodes and edges
2. Every `fromNode` and `toNode` references an existing node ID
3. Required fields present for each node type (`text` for text nodes, `file` for file nodes, `url` for link nodes)
4. `type` is one of: `text`, `file`, `link`, `group`
5. `fromSide`/`toSide` values are one of: `top`, `right`, `bottom`, `left`
6. `fromEnd`/`toEnd` values are one of: `none`, `arrow`
7. Color presets are `"1"` through `"6"` or valid hex (e.g., `"#FF0000"`)
8. JSON is valid and parseable

## Gotchas

- **Newline pitfall**: Use `\n` for line breaks in JSON text strings. Do **not** use literal `\\n` -- Obsidian renders that as the characters `\` and `n`, not a newline.
- **Duplicate IDs**: IDs must be unique across both nodes AND edges in the same file. A node and an edge cannot share the same ID.
- **Dangling edge references**: If you delete a node, you must also delete all edges that reference it via `fromNode` or `toNode`. Obsidian silently drops edges with invalid references.
- **Group containment is visual only**: Group nodes do not have a `children` array. Child nodes are "inside" a group only by virtue of their `x`/`y`/`width`/`height` falling within the group's bounds. Moving the group in Obsidian moves its visual children, but the JSON has no explicit parent-child link.
- **Z-index is array order**: The first node in the `nodes` array renders at the bottom. Groups should come before their child nodes in the array so children render on top.
- **Color presets are strings, not integers**: Use `"1"` not `1`. Using an integer will not parse correctly.
- **Large canvases**: Obsidian can slow down with 200+ nodes. Keep canvases focused; split into multiple files if needed.

## Complete Examples

See [references/EXAMPLES.md](references/EXAMPLES.md) for full canvas examples including mind maps, project boards, research canvases, and flowcharts.

## References

- [JSON Canvas Spec 1.0](https://jsoncanvas.org/spec/1.0/)
- [JSON Canvas GitHub](https://github.com/obsidianmd/jsoncanvas)
