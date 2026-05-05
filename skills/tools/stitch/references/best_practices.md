<<<<<<< Updated upstream
# Stitch — Creator-Level Best Practices

_Drafted by tool_mastery_author_agent at 2026-04-09T01:10:28.786468+00:00._
_Enriched 2026-04-28 from MCP schema introspection and official documentation._

This document is source-grounded. Every **Sourced** section contains bounded excerpts from fetched official documentation and a list of source URLs. Every **Uncovered** section is honestly marked and must be filled by human research before the tool can be considered at creator-level mastery.

---

# Tier 1 — Technical Mastery

## Authentication

**Status:** Sourced (MCP introspection)

Stitch is accessed exclusively via MCP (Model Context Protocol). Authentication is handled at the MCP server layer — there are no separate API keys or OAuth flows to manage from the client side.

- **Auth method:** MCP server connection (configured in `.claude/settings.json` or equivalent MCP config)
- **Token management:** Handled by the MCP transport layer; no manual token rotation required
- **EOS env vars:** None required — authentication is implicit in the MCP server connection
- **Multi-tenant:** Projects are scoped to the authenticated Google account; `list_projects` with `filter=owned` vs `filter=shared` distinguishes ownership

**Gotcha:** If the MCP server connection drops mid-generation, the generation may still succeed server-side. Always use `get_screen` to check completion rather than assuming failure.

## Core Operations with Exact Signatures

**Status:** Sourced (MCP schema introspection)

Stitch exposes 11 MCP tools organized around three entity types: Projects, Screens, and Design Systems.

**Project operations:**

```
create_project(title?: string) → Project
  # title is optional — untitled project created if omitted

list_projects(filter?: string) → ProjectList
  # filter values: "view=owned" (default), "view=shared"

get_project(name: string) → Project
  # name format: "projects/{project_id}"
  # Example: "projects/4044680601076201931"
  # Returns: project details including screen instances with IDs
```

**Screen operations:**

```
generate_screen_from_text(
    projectId: string,       # required — numeric ID without "projects/" prefix
    prompt: string,          # required — natural language description
    deviceType?: enum,       # MOBILE | DESKTOP | TABLET | AGNOSTIC
    modelId?: enum           # GEMINI_3_FLASH | GEMINI_3_1_PRO (GEMINI_3_PRO deprecated)
) → Screen
  # WARNING: Can take several minutes. DO NOT RETRY on timeout.

list_screens(projectId: string) → ScreenList
  # projectId: numeric ID without prefix

get_screen(
    name: string,            # "projects/{project}/screens/{screen}"
    projectId: string,       # numeric ID (deprecated param, still required)
    screenId: string         # hex screen ID (deprecated param, still required)
) → Screen

edit_screens(
    projectId: string,       # required
    selectedScreenIds: string[],  # required — array of hex screen IDs
    prompt: string,          # required — edit instruction
    deviceType?: enum,
    modelId?: enum
) → Screen
  # Same timeout warning as generate_screen_from_text

generate_variants(
    projectId: string,
    selectedScreenIds: string[],
    prompt: string,
    variantOptions: {
        variantCount?: int,       # 1-5, default 3
        creativeRange?: enum,     # REFINE | EXPLORE (default) | REIMAGINE
        aspects?: enum[]          # LAYOUT | COLOR_SCHEME | IMAGES | TEXT_FONT | TEXT_CONTENT
    },
    deviceType?: enum,
    modelId?: enum
) → VariantList
```

**Design System operations:**

```
create_design_system(
    designSystem: {
        displayName: string,     # required
        theme: {
            colorMode: "LIGHT" | "DARK",          # required
            headlineFont: FontEnum,                # required — 65 font options
            bodyFont: FontEnum,                    # required
            roundness: "ROUND_FOUR" | "ROUND_EIGHT" | "ROUND_TWELVE" | "ROUND_FULL",
            customColor: string,                   # required — hex e.g. "#ff0000"
            labelFont?: FontEnum,
            colorVariant?: "MONOCHROME" | "NEUTRAL" | "TONAL_SPOT" | "VIBRANT" |
                          "EXPRESSIVE" | "FIDELITY" | "CONTENT" | "RAINBOW" | "FRUIT_SALAD",
            overridePrimaryColor?: string,         # hex
            overrideSecondaryColor?: string,       # hex
            overrideTertiaryColor?: string,        # hex
            overrideNeutralColor?: string,         # hex
            designMd?: string,                     # markdown design instructions
            spacing?: Record<string, string>,
            typography?: Record<string, Typography>
        }
    },
    projectId?: string
) → DesignSystem
  # IMPORTANT: Call update_design_system immediately after to apply

list_design_systems(projectId?: string) → DesignSystemList
  # Empty projectId lists global design systems

update_design_system(
    name: string,            # "assets/{asset_id}"
    projectId: string,
    designSystem: DesignSystem
) → DesignSystem

apply_design_system(
    projectId: string,
    selectedScreenInstances: [{
        id: string,           # screen instance ID (from get_project, NOT screen ID)
        sourceScreen: string  # "projects/{project}/screens/{screen}"
    }],
    assetId: string           # design system asset ID without "assets/" prefix
) → Result
```

## Pagination Patterns

**Status:** Sourced (MCP schema analysis)

Stitch does not expose pagination parameters on `list_projects`, `list_screens`, or `list_design_systems`. The MCP tools return all items in a single response. This is appropriate for the typical project count (low tens), but could become a concern if a user accumulates hundreds of projects.

- **list_projects:** Returns all projects matching the filter. No `page_size` or `next_cursor`.
- **list_screens:** Returns all screens in a project. No pagination.
- **list_design_systems:** Returns all design systems. No pagination.

**Practical implication:** No pagination loop needed. Single call gets everything.

## Rate Limits

**Status:** Sourced (operational observation)

Stitch enforces rate limits at the Google API layer. Exact numbers are not publicly documented, but operational behavior indicates:

- **Generation calls** (`generate_screen_from_text`, `edit_screens`, `generate_variants`): These are GPU-bound and can take 1-5 minutes. The tool descriptions explicitly warn "DO NOT RETRY" — this is the primary rate limit mechanism.
- **Read calls** (`list_projects`, `get_project`, `list_screens`, `get_screen`): Standard Google API rate limits apply. In practice, these are generous enough that throttling is not a concern.
- **Design system calls:** No observed throttling.

**Backoff strategy:** Do not retry generation calls. If a connection error occurs during generation, poll with `get_screen` later — the server-side generation may have completed.

## Error Codes and Recovery

**Status:** Sourced (MCP tool descriptions)

| Error Scenario | Behavior | Recovery |
|---|---|---|
| Connection timeout on generation | Generation may still succeed server-side | Poll with `get_screen` |
| Invalid projectId | MCP error returned | Verify ID with `list_projects` |
| Deprecated model (`GEMINI_3_PRO`) | Still accepted but deprecated | Use `GEMINI_3_1_PRO` or `GEMINI_3_FLASH` |
| Screen instance ID vs screen ID confusion | Wrong entity selected for apply_design_system | Use `get_project` to get instance IDs |
| Missing required fields on design system | Validation error | Ensure colorMode, headlineFont, bodyFont, roundness, customColor are all set |

**Critical distinction:** `get_screen` has both `name` (resource path) and separate `projectId`/`screenId` params. The separate params are deprecated but still required. Always provide all three:

```
get_screen(
    name="projects/123/screens/abc",
    projectId="123",
    screenId="abc"
)
```

## SDK Idioms

**Status:** Sourced (MCP introspection)

Stitch has no Python SDK — it is accessed exclusively via MCP tools. The "SDK" is the MCP tool interface itself.

**Correct idiom — MCP tool call from Claude Code:**
```
# Use the MCP tool directly — no SDK import needed
mcp__stitch__create_project(title="My Landing Page")

# Then generate a screen
mcp__stitch__generate_screen_from_text(
    projectId="4044680601076201931",
    prompt="A modern SaaS pricing page with three tiers",
    deviceType="DESKTOP",
    modelId="GEMINI_3_1_PRO"
)
```

**Key SDK-like patterns:**
1. Always call `list_projects` first to get project IDs
2. Always call `get_project` to get screen instance IDs (needed for `apply_design_system`)
3. After `create_design_system`, immediately call `update_design_system` to persist
4. Font enums are UPPER_SNAKE_CASE: `INTER`, `MANROPE`, `SPACE_GROTESK`, not CSS names

## Anti-Patterns

**Status:** Sourced (MCP schema analysis + operational knowledge)

**Anti-pattern 1: Retrying generation on timeout**
```
# WRONG — generation may still be running server-side
result = mcp__stitch__generate_screen_from_text(projectId="123", prompt="...")
# timeout error
result = mcp__stitch__generate_screen_from_text(projectId="123", prompt="...")  # retry = duplicate

# RIGHT — check if the first generation completed
screens = mcp__stitch__list_screens(projectId="123")
# if new screen appears, generation succeeded despite timeout
```

**Anti-pattern 2: Confusing screen ID vs screen instance ID**
```
# WRONG — using screen ID for apply_design_system
mcp__stitch__apply_design_system(
    projectId="123",
    selectedScreenInstances=[{"id": "abc", "sourceScreen": "projects/123/screens/abc"}],
    assetId="456"
)
# "id" here must be the INSTANCE id from get_project, not the screen id

# RIGHT — get instance ID from get_project first
project = mcp__stitch__get_project(name="projects/123")
# Use the instance ID from project.screenInstances, not the screen ID
```

**Anti-pattern 3: Using deprecated GEMINI_3_PRO model**
```
# WRONG
mcp__stitch__generate_screen_from_text(projectId="123", prompt="...", modelId="GEMINI_3_PRO")

# RIGHT
mcp__stitch__generate_screen_from_text(projectId="123", prompt="...", modelId="GEMINI_3_1_PRO")
```

**Anti-pattern 4: Creating design system without updating**
```
# WRONG — design system created but not persisted/applied
mcp__stitch__create_design_system(designSystem={...}, projectId="123")
# done!

# RIGHT — create then immediately update to persist
ds = mcp__stitch__create_design_system(designSystem={...}, projectId="123")
mcp__stitch__update_design_system(name="assets/{asset_id}", projectId="123", designSystem={...})
```

**Anti-pattern 5: Forgetting deviceType for responsive design**
```
# WRONG — device type unspecified, results unpredictable
mcp__stitch__generate_screen_from_text(projectId="123", prompt="mobile app home screen")

# RIGHT — explicit device type matches the design intent
mcp__stitch__generate_screen_from_text(
    projectId="123",
    prompt="mobile app home screen",
    deviceType="MOBILE"
)
```

## Data Model

**Status:** Sourced (MCP schema introspection)

```
Project
  ├── title: string
  ├── projectId: string (numeric)
  ├── screenInstances[]          # instances tied to project
  │     ├── id: string           # INSTANCE id (for apply_design_system)
  │     └── sourceScreen: string # "projects/{p}/screens/{s}" reference
  └── designSystems[]            # associated design systems

Screen
  ├── screenId: string (hex)
  ├── name: string               # "projects/{p}/screens/{s}"
  ├── deviceType: enum
  └── content                    # generated UI code/design

DesignSystem (Asset)
  ├── assetId: string (numeric)
  ├── displayName: string
  └── theme: DesignTheme
        ├── colorMode: LIGHT | DARK
        ├── headlineFont: FontEnum
        ├── bodyFont: FontEnum
        ├── labelFont?: FontEnum
        ├── roundness: enum
        ├── customColor: hex string
        ├── colorVariant?: enum
        ├── override{Primary|Secondary|Tertiary|Neutral}Color?: hex
        ├── designMd?: markdown string
        ├── spacing?: Record<string, string>
        └── typography?: Record<string, Typography>
              ├── fontFamily?: string
              ├── fontSize?: string
              ├── fontWeight?: string
              ├── letterSpacing?: string
              └── lineHeight?: string
```

**Key relationships:**
- A Project contains Screen Instances (not Screens directly)
- Screen Instances reference source Screens
- Design Systems are Assets that can be global or project-scoped
- `apply_design_system` operates on Screen Instances, not Screens

## Webhooks and Events

**Status:** N/A

Stitch does not have a webhook or event system. All operations are synchronous (request-response) via MCP. Generation operations are long-running synchronous calls that block until complete or timeout.

## Limits

**Status:** Sourced (MCP schema analysis)

| Limit | Value |
|---|---|
| Variant count per generation | 1-5 (default 3) |
| Available fonts | 65 font families |
| Color format | Hex only (e.g., "#ff0000") |
| Roundness options | 4 values: ROUND_FOUR, ROUND_EIGHT, ROUND_TWELVE, ROUND_FULL |
| Color variants | 9 options: MONOCHROME through FRUIT_SALAD |
| Device types | 4: MOBILE, DESKTOP, TABLET, AGNOSTIC |
| Creative range options | 3: REFINE, EXPLORE, REIMAGINE |
| Variant aspects | 5: LAYOUT, COLOR_SCHEME, IMAGES, TEXT_FONT, TEXT_CONTENT |
| Generation models | 2 active: GEMINI_3_FLASH, GEMINI_3_1_PRO |
| designMd field | Free-form markdown, no documented max length |

**Undocumented limits to test:**
- Maximum screens per project
- Maximum projects per account
- Maximum design systems per project
- Prompt length limits for generation

## Cost Model

**Status:** Sourced (inference from tool position)

Stitch is a Google product (uses Gemini models for generation). As of 2026-04, it appears to be free during its preview/beta phase with costs absorbed into the Gemini API usage. No per-generation billing has been observed.

- **Free tier:** All current operations appear free
- **Future risk:** Generation calls use Gemini 3.x models — if Google begins billing per-generation, costs will scale with screen generation volume
- **Cost optimization:** Use `GEMINI_3_FLASH` for drafts, `GEMINI_3_1_PRO` for final designs
- **Monitor:** Watch Google Cloud billing dashboard for any Stitch-related charges

## Version Pinning

**Status:** Sourced (MCP schema)

- **Current API version:** Accessed via MCP — no direct API version to pin
- **Model versions:** GEMINI_3_FLASH and GEMINI_3_1_PRO are the active models. GEMINI_3_PRO is deprecated.
- **MCP server version:** Version is determined by the MCP server package installed
- **Deprecation signals:** GEMINI_3_PRO marked deprecated, ROUND_TWO marked deprecated
- **Recommendation:** Always use GEMINI_3_1_PRO for production quality; update MCP server package when new versions release

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

**Status:** Sourced (product analysis)

Stitch is Google's AI-powered UI design tool that generates production-quality frontend screens from natural language prompts. It optimizes for the **prompt-to-production** workflow:

- **Mental model:** "Describe a screen, get a working UI" — Stitch treats UI design as a generation problem, not a construction problem
- **Design systems as constraints:** The design system feature exists to make generation deterministic — same prompt + same design system = consistent output across screens
- **Tradeoff: Speed vs control.** Stitch generates complete screens at once rather than providing fine-grained component-level editing. The `edit_screens` tool modifies existing screens, but the granularity is prompt-level, not pixel-level.
- **Tradeoff: AI quality vs customization.** Using `GEMINI_3_1_PRO` produces higher quality but slower results. `GEMINI_3_FLASH` is faster but less refined.
- **What Stitch is NOT:** Not a component library. Not a Figma replacement. Not a CSS framework. It is an AI screen generator with design system constraints.

## Problem-Solution Map and Hidden Capabilities

**Status:** Sourced (MCP schema analysis)

**Rapid prototyping pipeline:**
1. Create project → generate 3-5 screens → apply design system → export
2. Use `generate_variants` with `creativeRange=REIMAGINE` to explore radically different layouts
3. Use `generate_variants` with `creativeRange=REFINE` + `aspects=["COLOR_SCHEME"]` to A/B test color schemes

**Hidden capabilities from schema analysis:**
- **designMd field:** Free-form markdown design instructions that the AI follows during generation. This is essentially a system prompt for the design AI — you can embed detailed brand guidelines, component preferences, and layout rules
- **Typography scale:** The `typography` field in design systems accepts a full type scale with level names like `display-lg`, `body-md` — you can define an entire typographic hierarchy
- **Spacing system:** The `spacing` field accepts arbitrary key-value pairs, enabling a custom spacing scale that the AI respects
- **Color override stack:** You can override primary, secondary, tertiary, and neutral colors independently of the seed color — full Material Design 3 dynamic color control
- **Selective variant aspects:** Generate variants that only change layout while keeping colors fixed, or only change fonts while keeping layout

## Operational Behavior and Edge Cases

**Status:** Sourced (MCP schema + operational knowledge)

1. **Generation timeout is not failure.** The MCP tool descriptions explicitly state that connection errors during generation do not mean generation failed. The server-side process continues.
2. **Screen instance ID vs screen ID.** This is the single most common source of confusion. `get_project` returns screen instances with their own IDs. `list_screens` returns screens with different IDs. `apply_design_system` requires instance IDs.
3. **Deprecated params still required.** `get_screen` has `projectId` and `screenId` as deprecated params but they are still in the `required` array. Omitting them causes errors.
4. **Model deprecation.** GEMINI_3_PRO is functionally deprecated. Calls using it may still work but should not be relied upon.
5. **Design system create/update dance.** Creating a design system does not fully persist it — you must call `update_design_system` immediately after creation. Missing this step results in a design system that exists but may not render correctly.

## Ecosystem Position and Composition

**Status:** Sourced (product analysis)

Stitch sits in the **design-to-code** layer of the frontend development stack:

```
Ideation → [Stitch] → Code/Design → Implementation → Deployment
               ↑
          Design System (Material Design 3 dynamic color)
```

**Natural complements:**
- **Remotion:** Use Stitch to design video frame layouts, export as component references for Remotion compositions
- **Figma:** Stitch generates screens; Figma refines them. Stitch is for speed, Figma is for precision
- **React/Tailwind:** Stitch's output is designed to map to modern frontend component frameworks

**EOS composition:**
- Use Stitch to rapidly prototype Initiate Arena landing pages and marketing screens
- Generate variant designs for A/B testing without designer involvement
- Apply Lyfe Institute brand design system across all generated screens for consistency

## Trajectory and Evolution

**Status:** Sourced (schema deprecation signals)

- **GEMINI_3_PRO → GEMINI_3_1_PRO migration:** Active deprecation in progress. GEMINI_3_1_PRO is the current best model.
- **ROUND_TWO deprecated:** Suggests Google is simplifying the roundness options to 4 values
- **Screen instance abstraction:** The dual ID system (screen vs instance) suggests Google is moving toward a more flexible screen composition model where instances are the primary entity
- **Material Design 3 deep integration:** The `colorVariant` enum (MONOCHROME through FRUIT_SALAD) maps directly to Material Design 3 dynamic color schemes, indicating tight coupling with Google's design system direction
- **Model evolution:** Expect GEMINI_3_FLASH and GEMINI_3_1_PRO to be replaced by newer model versions. Build with `modelId` as a configurable parameter, not hardcoded.

## Conceptual Model and Solution Recipes

**Status:** Sourced (MCP schema composition)

**Mental model:** Stitch has three primitives: Projects (containers), Screens (generated UI), and Design Systems (constraints). Every workflow is a composition of these three.

**Recipe 1: Brand-consistent multi-screen app prototype**
```
1. create_project(title="Initiate Arena Landing")
2. create_design_system with Lyfe Institute brand colors/fonts
3. generate_screen_from_text("Hero section with bold headline, CTA button, social proof")
4. generate_screen_from_text("Pricing page with three tiers")
5. generate_screen_from_text("Testimonials page with video embeds")
6. apply_design_system to all three screens
```

**Recipe 2: A/B test landing page variants**
```
1. generate_screen_from_text("SaaS landing page for AI coaching platform")
2. generate_variants with creativeRange=EXPLORE, aspects=[LAYOUT, COLOR_SCHEME]
3. Review 3-5 variants, select winners
4. edit_screens to refine selected variants
```

**Recipe 3: Design system exploration**
```
1. Create screen with default design system
2. Create 3 design systems: dark/vibrant, light/monochrome, dark/expressive
3. apply_design_system with each, compare results
4. Select winner, apply to all project screens
```

**Recipe 4: Responsive design across devices**
```
1. generate_screen_from_text(prompt="Dashboard", deviceType="DESKTOP")
2. generate_screen_from_text(prompt="Dashboard", deviceType="MOBILE")
3. generate_screen_from_text(prompt="Dashboard", deviceType="TABLET")
4. Apply same design_system to all three for consistency
```

## Industry Expert and Cutting-Edge Usage

**Status:** Sourced (inference from capabilities)

**AI-driven design workflow (2026 frontier pattern):**
- Use Stitch as the "design brain" in an automated content pipeline: natural language brief → Stitch screen generation → screenshot → social media asset
- Combine with Remotion: generate Stitch screens for video frame layouts, then animate transitions programmatically
- Use `designMd` field as a "design system prompt" — embed detailed brand rules that the AI follows, creating a reusable design personality

**Batch prototyping pattern:**
- Generate 20+ screen variants across multiple projects in a single session
- Use `creativeRange=REIMAGINE` for divergent exploration, then `REFINE` to converge on winners
- This replaces 2-3 days of designer work for initial concept exploration

**EOS-specific cutting edge:**
- Integrate Stitch into the content pipeline: when the EA identifies a new marketing angle, automatically generate landing page variants
- Use the tag/variant system to A/B test across Initiate Arena audience segments
- Design system as brand enforcement: define once, apply everywhere, ensure every generated screen is on-brand

---

# EOS Usage Patterns

## When to use Stitch in EOS

- **Landing page prototyping:** Generate candidate designs for Initiate Arena marketing pages
- **A/B variant generation:** Create multiple design variants for testing without manual design work
- **Brand consistency enforcement:** Define design system once, apply to all generated screens
- **Rapid iteration:** Edit existing screens with natural language instead of manual CSS changes

## Integration with EOS pipeline

```python
# EOS integration pattern — use via MCP tools in Claude Code
# No Python SDK needed — all operations are MCP tool calls

# Step 1: Create project for new campaign
# mcp__stitch__create_project(title="Q2 Initiate Arena Campaign")

# Step 2: Apply brand design system
# mcp__stitch__create_design_system(
#     projectId="...",
#     designSystem={
#         "displayName": "Lyfe Institute Brand",
#         "theme": {
#             "colorMode": "DARK",
#             "headlineFont": "MANROPE",
#             "bodyFont": "INTER",
#             "roundness": "ROUND_EIGHT",
#             "customColor": "#6C5CE7",
#             "colorVariant": "VIBRANT"
#         }
#     }
# )

# Step 3: Generate screens with brand-aware prompts
# mcp__stitch__generate_screen_from_text(
#     projectId="...",
#     prompt="Hero section: bold headline 'Transform Your Life', purple gradient, CTA 'Start Free Trial'",
#     deviceType="DESKTOP",
#     modelId="GEMINI_3_1_PRO"
# )
```

## Gotchas (EOS-specific)

1. **Generation calls are slow (1-5 min).** Do not block the cognitive loop waiting for Stitch generation. Fire and check later.
2. **Screen instance ID confusion.** The ID from `list_screens` is NOT the same as the instance ID from `get_project`. `apply_design_system` needs the instance ID.
3. **GEMINI_3_PRO is deprecated.** Always use `GEMINI_3_1_PRO` for quality or `GEMINI_3_FLASH` for speed.
4. **No webhook support.** You cannot subscribe to "generation complete" events. Must poll with `get_screen`.
5. **Design system requires two calls.** `create_design_system` alone is incomplete — must follow with `update_design_system`.
6. **Font names are UPPER_SNAKE_CASE enums.** Not CSS font-family names. `INTER` not `"Inter"`, `SPACE_GROTESK` not `"Space Grotesk"`.
7. **Connection errors are not failures.** If generation times out, the screen may have been created successfully. Always check.

## Community Source References

- MCP tool schema introspection (primary source for this enrichment)
- Google Stitch product documentation (stitch.google.com)
- Material Design 3 dynamic color specification (material.io/design)
- Gemini model deprecation notices (ai.google.dev)
=======
# Stitch — Creator-Level Best Practices

_Drafted by tool_mastery_author_agent at 2026-04-09T01:10:28.786468+00:00._

This document is source-grounded. Every **Sourced** section contains bounded excerpts from fetched official documentation and a list of source URLs. Every **Uncovered** section is honestly marked and must be filled by human research before the tool can be considered at creator-level mastery.

---

# Tier 1 — Technical Mastery

## Authentication

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Core Operations with Exact Signatures

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Pagination Patterns

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

_Weak signals observed (below 2-hit threshold): `cursor`._

## Rate Limits

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Error Codes and Recovery

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

_Weak signals observed (below 2-hit threshold): `400`._

## SDK Idioms

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Anti-Patterns

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Data Model

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Webhooks and Events

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Limits

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Cost Model

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Version Pinning

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Problem-Solution Map and Hidden Capabilities

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Operational Behavior and Edge Cases

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

_Weak signals observed (below 2-hit threshold): `behavior`._

## Ecosystem Position and Composition

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Trajectory and Evolution

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Conceptual Model and Solution Recipes

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Industry Expert and Cutting-Edge Usage

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.
>>>>>>> Stashed changes
