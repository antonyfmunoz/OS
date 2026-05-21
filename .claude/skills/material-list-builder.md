---
name: material-list-builder
description: Build a structured shopping/materials list as an .xlsx spreadsheet for any physical build, fabrication project, hardware setup, or purchase plan. Use whenever the user says "create a materials list", "make me a shopping list", "what do I need to buy for X", "BOM for X", "parts list", "spreadsheet of everything I need", "cost to build X", "build me a shopping cart", or any time a multi-item purchase plan emerges from a build discussion (helmet builds, studio setups, workshop tooling, electronics prototypes, home office builds, computer builds, travel kits, etc.). Trigger proactively when a build conversation has produced enough specificity to itemize — don't wait for explicit "make me a spreadsheet" if the items are already mapped. The output is always a categorized, formula-driven .xlsx with current prices, working links, subtotals, grand total, and a strategic notes section. Anchored to OST-style execution discipline (tier items, verify prices for big-ticket, don't fabricate URLs) but works for any project.
allowed-tools: Bash, Read, Write, WebSearch, WebFetch
---

# Material List Builder

A material list is the bridge between a build plan and a buy decision. Bad lists waste money on the wrong items, miss critical consumables, and lock the user into a single vendor. Good lists are tiered by necessity, priced from current sources, structured for easy editing, and annotated with the strategic context that turns a shopping list into a procurement plan.

This skill produces that good list. Always as a spreadsheet, never as conversational prose, because a prose list is unworkable the moment the user wants to change quantities, swap vendors, or check off completed purchases.

## When to trigger

- **Explicit ask:** "make me a shopping list", "what do I need for X", "BOM for X", "spreadsheet of everything", "total cost to build", "parts list"
- **Implicit ask:** the conversation has produced a build plan specific enough to itemize, and the user is signaling intent to purchase (saying "I'm going to buy X" or asking about prices for multiple items)
- **Proactive:** any time a build discussion ends with "I'm gonna order this stuff" — write the list without waiting to be asked, then offer it

Do NOT trigger for single-item purchase recommendations ("which laptop should I buy"). That's a conversational answer, not a spreadsheet.

## The decision framework (run before generating)

### 1. Scope check — what phase, what variant?

The biggest failure mode is itemizing for the wrong scope. Before listing anything, confirm:

- **Phase:** is this the prototype, the v1, the production version? Lists for "eventually" vs "this weekend" look completely different.
- **Variant:** if the build is modular (e.g., a mask with HUD-on and HUD-off faceplates), list for the variant the user is actually building now. Future variants get an "out of scope this list" note.
- **Constraints:** budget ceiling, tools they already own, vendor preferences (Amazon-only, manufacturer-direct OK, willing to wait for sales).

If the conversation already established this, don't re-ask — just confirm by stating the scope at the top of the spreadsheet. If it didn't, ask **before** building.

### 2. Categorize before itemizing

Identify the natural categories for this build. Common patterns:

- **Hardware** (the main tools/machines/devices)
- **Materials** (filaments, resins, raw stock, paint)
- **Consumables** (gloves, IPA, sandpaper, tape — things you'll go through)
- **Hardware accessories** (magnets, screws, brackets — small parts that connect things)
- **Finishing supplies** (primer, filler, paint)
- **Tools** (instruments, separate "skip if owned" section)
- **Optional / future phase** (clearly labeled — out of scope but listed so they don't forget later)

Categories drive the spreadsheet's section structure. Get them right before populating items.

### 3. Tier items by necessity

Inside each category, items fall into tiers:

- **Essential** — the build doesn't happen without it. Include in main list.
- **Recommended** — significantly improves outcome or reduces labor. Include with a note explaining why.
- **Optional** — nice-to-have. Include in a separate "Optional" subsection or skip and mention in notes.
- **Skip if owned** — tools/consumables the user may already have. Put in a "Skip if owned" category so they can delete the rows.
- **Future phase** — don't include in this list. Mention in notes that these were considered but deferred.

Tiering protects the user from over-buying. Anyone can write a list that includes everything; the value-add is the discipline to separate must-have from might-want.

### 4. Verify prices for big-ticket items

Anything over $200, web-search the current price before quoting. Hardware markets shift constantly — printers go on sale, glasses get discounts, GPUs swing wildly. Quoting training-data prices for big-ticket items is the fastest way to lose credibility.

For items under $200, training-data + estimation is fine, but note that prices are "approximate" in the notes section.

### 5. Never fabricate product URLs

Direct Amazon product URLs (`amazon.com/dp/ASIN`) are session-specific, contain affiliate parameters, and frequently 404 when copy-pasted from training data. Do **not** invent them.

Instead:

- **Amazon items:** use search URLs in the format `https://www.amazon.com/s?k=search+terms`. These always resolve to live results.
- **Major hardware (printers, glasses, named products):** use the manufacturer's product page URL — Bambu store, Elegoo store, Viture, etc. These are stable.
- **Specialty items:** McMaster-Carr, AliExpress, Adafruit, Sparkfun direct URLs are stable enough if you've verified them through web search.

Tell the user in the notes section that links are search URLs (for honesty about why they're not direct).

### 6. Add a strategic notes section

A list without strategic context is just a list. Always include a notes section at the bottom of the spreadsheet covering:

- **Where to find discounts** (alternative vendors, recent sale prices, coupon mechanics)
- **Bundle savings** (when buying X + Y together saves vs separate purchases)
- **Sequencing** (what should arrive first, what depends on what)
- **Gotchas before purchase** (size variants, compatibility checks, ventilation/space requirements)
- **What's not on this list and why** (deferred items, alternative paths)

These notes are usually the highest-value part of the spreadsheet.

## Spreadsheet structure (mandatory)

Every output follows this structure. Don't improvise the layout — it's been tuned.

```
Row 1: Title (large, bold, project color)
Row 2: Subtitle / scope description (italic, small)
Row 3: (blank)
Row 4: Headers (Category | Item | Qty | Unit Price | Total | Link | Notes)
Row 5+: Category sections, each ending in a subtotal row
... grand total row (bold, large, accent color)
... (blank)
Notes & Recommendations section (heading + bullet rows)
```

### Columns (exact, in order)

1. **Category** — populated only on the category header row; blank on item rows under that category
2. **Item** — descriptive name (e.g., "Bambu Lab X1 Carbon (no AMS)" not "X1C")
3. **Qty** — integer
4. **Unit Price** — currency, formatted as `$#,##0.00`
5. **Total** — `=Qty*UnitPrice` as a formula, formatted as currency
6. **Link** — clickable hyperlink with text "Link", styled blue underline
7. **Notes** — short rationale, gotchas, alternatives. Italic gray.

### Formulas (mandatory)

- Each row's Total: `=C{row}*D{row}`
- Each category's subtotal: `=SUM(E{first_row}:E{last_row})`
- Grand total: sum of all subtotal cells (e.g., `=E10+E18+E25+...`)

**Never hardcode totals.** All math must be formula-driven so the user can edit quantities and see live totals.

### Formatting (mandatory)

- Font: Arial throughout
- Title row: 16pt bold, navy color (#1F4E78)
- Category headers: white text on blue (#2E75B6) background, 11pt bold
- Subtotal rows: italic bold, light blue background (#D9E1F2)
- Grand total row: large bold white text on navy background, 13pt
- Item rows: 10pt regular Arial, thin gray borders
- Notes: italic 9pt gray (#666666)
- Freeze panes at row 5 so headers stay visible when scrolling

### Column widths

- Category: 22, Item: 42, Qty: 6, Unit Price: 12, Total: 12, Link: 8, Notes: 50

## Execution pattern

When this skill triggers, the execution order is:

1. **Confirm scope** if not already locked in conversation. State it explicitly: "Building for [phase], variant [X], assuming you don't already have [Y]."
2. **Categorize the items** mentally before writing code. The categories define the spreadsheet structure.
3. **Verify prices for items >$200** via web search. Quote current prices, not training-data prices.
4. **Generate the spreadsheet** using openpyxl following the structure above. Write a Python script that:
   - Creates the workbook with proper formatting
   - Uses formulas for all Total cells (`=C{row}*D{row}`)
   - Uses SUM formulas for subtotals and grand total
   - Adds hyperlinks via `ws.cell().hyperlink`
   - Applies all formatting (fonts, fills, borders, column widths, freeze panes)
5. **Run the script** and verify the output file exists and is non-zero size.
6. **Present the file** to the user with a short summary: category totals, grand total, top 3 strategic notes. The spreadsheet has the detail; the chat message has the recap.

## Quality bar

A material list is good when:

1. The user can edit any quantity and see live totals update.
2. Every link resolves to a real, current product or search result.
3. Big-ticket prices are within 10% of current market.
4. The notes section saves the user more money than the spreadsheet cost in time to make.
5. The tiering is clear enough that the user can produce a "minimum viable purchase" by deleting rows tagged optional/skip-if-owned.

A material list is bad when:

- It bundles essential and optional items without flagging which is which.
- It quotes stale prices for hardware that's been on sale or discontinued.
- It uses fake Amazon product URLs that return 404s.
- It lacks a strategic notes section (just an itemized list with no procurement context).
- It hardcodes totals as numbers instead of formulas, so the user can't recalculate after editing.

## Common pitfalls (worked examples)

### Wrong: building the list for the wrong scope

User: "Help me plan my Red Hood helmet build."
*Assistant lists everything for the full high-tech electronics version when user is on the cosplay-shell phase.*
Right: confirm scope before listing — "you're on Phase 1 shell, right? Skipping electronics housing items?"

### Wrong: fabricated Amazon URLs

*Assistant generates `https://www.amazon.com/dp/B0XXXXXXXX` links that return 404s.*
Right: `https://www.amazon.com/s?k=bambu+lab+x1+carbon` — always resolves.

### Wrong: hardcoded totals

*Assistant computes totals in Python and writes the number to the cell.*
Right: `sheet['E5'] = '=C5*D5'`, `sheet['E20'] = '=SUM(E5:E19)'` — formulas survive user edits.

### Wrong: training-data prices for current hardware

*Assistant quotes $1,449 for the X1 Carbon Combo from training data.*
Right: web search before quoting, find current price, note alternative vendors.

### Wrong: no strategic notes

*Assistant produces a clean spreadsheet with no notes section.*
Right: bottom section covers alternative vendor pricing, bundle savings, ventilation requirements before purchase, etc. This is where the spreadsheet earns its keep.

## Gotchas

- openpyxl must be installed (`pip install openpyxl`). Check before running.
- Hyperlinks in openpyxl: use `ws.cell(row=r, col=6).hyperlink = url` and set the cell value to `"Link"`. Also apply blue underline font style explicitly — openpyxl doesn't auto-style hyperlinks.
- Formula cells must be written as strings starting with `=`. If you write `=C5*D5` as a Python expression result, openpyxl will store the number, not the formula.
- Freeze panes: `ws.freeze_panes = "A5"` freezes rows 1-4 (title + subtitle + blank + headers).
- Column width in openpyxl is in character units, not pixels. The widths specified above (22, 42, 6, etc.) are character counts.
- Currency format string for openpyxl: `'$#,##0.00'` — set on the cell's `number_format` attribute.
