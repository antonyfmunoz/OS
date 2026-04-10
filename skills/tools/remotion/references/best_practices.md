# Remotion — Creator-Level Best Practices

_Drafted by tool_mastery_author_agent at 2026-04-09T06:29:59.598707+00:00._

This document is source-grounded. Every **Sourced** section contains bounded excerpts from fetched official documentation and a list of source URLs. Every **Uncovered** section is honestly marked and must be filled by human research before the tool can be considered at creator-level mastery.

---

# Tier 1 — Technical Mastery

## Authentication

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Core Operations with Exact Signatures

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

_Weak signals observed (below 2-hit threshold): `get `._

## Pagination Patterns

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Rate Limits

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Error Codes and Recovery

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## SDK Idioms

**Status:** Sourced (pattern × 2 + prose)

_Grounded in 2 structured pattern(s) extracted from the raw research captures. Patterns are preferred over prose because they carry their own provenance and confidence._

**Setup Flow** — `[SOURCE: https://raw.githubusercontent.com/remotion-dev/remotion/6dcf676e7c82fcc60b31aab1c715003e8399eedd/packages/docs/docs/4-0-alpha.mdx]`  _(confidence: high, 4 occurrences)_

1. Fix warnings if Zod is not installed
2. `z` is not exported from Remotion anymore, instead, just install `zod`!
3. `zColor` is now to be installed from `@remotion/zod-types`
4. Create new array items

**Setup Flow** — `[SOURCE: https://raw.githubusercontent.com/remotion-dev/remotion/6dcf676e7c82fcc60b31aab1c715003e8399eedd/packages/docs/docs/4-0-migration.mdx]`  _(confidence: high, 9 occurrences)_

1. import {Config} from 'remotion';
2. Don't use the [`npx remotion install`](/docs/cli/install) command anymore
3. **remotion**: [`transparent`](/docs/offthreadvideo#transparent) has been added to `
4. **@remotion/cli**: New indicator whether a file has been overwritten (`○`) or newly created (`+`)
5. **@remotion/eslint-plugin**: New ESLint rule: Use the right import in the config file
6. **@remotion/lambda**: Lambda does not support the [x86 architecture anymore](/docs/lambda/runtime)

---

_Additional prose context from independent sources (cross-referenced to increase section coverage)._

**Excerpt 1:**

> There is a way [to go back to Babel, you can read about it here](/docs/legacy-babel)
> **Upgrade path**: Do nothing - should something break, use the legacy Babel plugin and file an issue.
> ## `react-dom` is a peer dependency
> `react-dom` is not anymore pre-installed, so you need to install manually if you upgrade.
> ## Upgrade to version 2.0
> Upgrade **all** dependencies containing "remotion" in your package.json to version `^2.0.0`.
> -"@remotion/bundler": "^1.5.4",
> -"@remotion/cli": "^1.5.4",
> -"@remotion/eslint-config": "^1.5.4",
> -"@remotion/renderer":…

**Excerpt 2:**

> Fix bugs reported with `
> ` and more verbose logging
> - Refined editor
> - Fix Lambda issues
> - Revamped CLI verbose logging mode
> - FFmpeg is now in the Lambda function instead of a Lambda Layer
> ### `4.0.0-alpha6`
> - Fixes `EACCES` errors appearing
> - GUI design improvements
> - Fix warnings if Zod is not installed
> - Breaking change: `staticFile()` now encodes the filename using `encodeURIComponent`.

**Excerpt 3:**

> You don't have to and should not do it manually anymore - see migration guide
> ### `4.0.0-alpha5`
> May 3rd 2023:
> - Features the new Rust renderer enabling faster `
> `!
> - `z` is not exported from Remotion anymore, instead, just install `zod`!
> - `zColor` is now to be installed from `@remotion/zod-types`
> - Overall polish of the editor
> ### `4.0.0-alpha.185+1b8f0e746`
> - Fix rendering with FFmpeg on Linux
> - Make all strings `as const` when saving back to the root file to ensure type safety.
> - New…

**Sources:**
- https://raw.githubusercontent.com/remotion-dev/remotion/6dcf676e7c82fcc60b31aab1c715003e8399eedd/packages/docs/docs/2-0-migration.mdx
- https://raw.githubusercontent.com/remotion-dev/remotion/6dcf676e7c82fcc60b31aab1c715003e8399eedd/packages/docs/docs/4-0-alpha.mdx
- https://raw.githubusercontent.com/remotion-dev/remotion/6dcf676e7c82fcc60b31aab1c715003e8399eedd/packages/docs/docs/4-0-migration.mdx

> _Authored by tool_mastery_author_agent with pattern-priority rendering. Human review recommended before treating as creator-level mastery._

## Anti-Patterns

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

_Weak signals observed (below 2-hit threshold): `do not`._

## Data Model

**Status:** Sourced (prose)

_Source-grounded excerpts from fetched documentation. Keyword matches: `field`, `object`, `property`, `schema`._

**Excerpt 1:**

> The `assetsInfo` object will be returned by `renderFrames()`.
> **Upgrade path**: See the updated examples on the [SSR page](/docs/ssr) and update your program accordingly.
> ## `--overwrite` is now default
> If an output already exists, Remotion will overwrite it without asking now, [unless you disable this…

**Excerpt 2:**

> The new behavior of Remotion 3.0 is that if an error occurs, these functions reject instead.
> **Upgrade path**: Remove the `onError` property from your `getCompositions()`, `renderFrames()` and `renderStill()` calls and catch errors in a try / catch instead.

**Excerpt 3:**

> the minimum required `glibc` version on Linux x64 to support Ubuntu 20.04
> ### `4.0.0-alpha14`
> - Make renders via the CLI faster using a reusable server
> - `console.log`'s are symbolicated when rendering locally using `--log=verbose`
> - Fix bug in composition metadata resolution
> - New design for the schema editor
> - Upgrade TypeScript ESLint, Prettier and Turborepo
> ### `4.0.0-alpha13`
> - Fix editor props not being applied
> ### `4.0.0-alpha12`
> - More performant Studio
> ### `4.0.0-alpha11`
> - Performance improvements for the Remotion Studio
> - Your component should do less unnecessary re-renders.
> ###…

**Sources:**
- https://raw.githubusercontent.com/remotion-dev/remotion/6dcf676e7c82fcc60b31aab1c715003e8399eedd/packages/docs/docs/2-0-migration.mdx
- https://raw.githubusercontent.com/remotion-dev/remotion/6dcf676e7c82fcc60b31aab1c715003e8399eedd/packages/docs/docs/3-0-migration.mdx
- https://raw.githubusercontent.com/remotion-dev/remotion/6dcf676e7c82fcc60b31aab1c715003e8399eedd/packages/docs/docs/4-0-alpha.mdx
- https://raw.githubusercontent.com/remotion-dev/remotion/6dcf676e7c82fcc60b31aab1c715003e8399eedd/packages/docs/docs/4-0-migration.mdx
- https://raw.githubusercontent.com/remotion-dev/remotion/6dcf676e7c82fcc60b31aab1c715003e8399eedd/packages/docs/docs/5-0-migration.mdx

> _Authored by tool_mastery_author_agent with pattern-priority rendering. Human review recommended before treating as creator-level mastery._

## Webhooks and Events

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

_Weak signals observed (below 2-hit threshold): `event`._

## Limits

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Cost Model

**Status:** Sourced (prose)

_Source-grounded excerpts from fetched documentation. Keyword matches: `cost`, `price`._

**Excerpt 1:**

> It should be faster, cheaper and not have any different behavior than `x86_64`.
> **How to upgrade**:
> - Remove the `architecture` option from `estimatePrice()` and `deployFunction()`.
> ## Rich timeline removed
> The option to use the "Rich timeline" has been removed due to performance problems.

**Excerpt 2:**

> This will add a miniscule cost to your renders technically, but will lead to more reliable and faster renders, since Chrome is less likely to run out of disk cache.
> **Required actions**:
> - If you want to keep the old behavior, set `diskSizeInMb: 2048`, explicitly.
> - If your Lambda function name is hardcoded to include…

**Sources:**
- https://raw.githubusercontent.com/remotion-dev/remotion/6dcf676e7c82fcc60b31aab1c715003e8399eedd/packages/docs/docs/4-0-migration.mdx
- https://raw.githubusercontent.com/remotion-dev/remotion/6dcf676e7c82fcc60b31aab1c715003e8399eedd/packages/docs/docs/5-0-migration.mdx

> _Authored by tool_mastery_author_agent with pattern-priority rendering. Human review recommended before treating as creator-level mastery._

## Version Pinning

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

_Weak signals observed (below 2-hit threshold): `changelog`._

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Problem-Solution Map and Hidden Capabilities

**Status:** Sourced (prose)

_Source-grounded excerpts from fetched documentation. Keyword matches: `example`, `guide`, `how to`._

**Excerpt 1:**

> The behavior of sequences is now the following, as explained by an example: If `durationInFrames` is 60 and `from` is 0, the sequence goes from frame 0 to 59 (60 frames in total), same as a composition with the same duration.

**Excerpt 2:**

> The `assetsInfo` object will be returned by `renderFrames()`.
> **Upgrade path**: See the updated examples on the [SSR page](/docs/ssr) and update your program accordingly.
> ## `--overwrite` is now default
> If an output already exists, Remotion will overwrite it without asking now, [unless you disable this behavior](/docs/config#setoverwriteoutput).
> **Upgrade path**: Do nothing or adjust the…

**Excerpt 3:**

> ---
> image: /generated/articles-docs-3-0-migration.png
> id: 3-0-migration
> title: v3.0 Migration
> crumb: "Version Upgrade"
> ---
> When upgrading from Remotion 2 to Remotion 3, note the following changes and apply them to your project.
> ## How to upgrade
> Upgrade `remotion` and all packages starting with `@remotion` to `^3.0.0`:
> - "remotion": "^2.6.15"
> - "@remotion/bundler": "^2.6.15"
> - "@remotion/eslint-config": "^2.6.15"
> - "@remotion/eslint-plugin": "^2.6.15"
> - "@remotion/cli": "^2.6.15"
> - "@remotion/renderer": "^2.6.15"
> +…

**Sources:**
- https://raw.githubusercontent.com/remotion-dev/remotion/6dcf676e7c82fcc60b31aab1c715003e8399eedd/packages/docs/docs/2-0-migration.mdx
- https://raw.githubusercontent.com/remotion-dev/remotion/6dcf676e7c82fcc60b31aab1c715003e8399eedd/packages/docs/docs/3-0-migration.mdx
- https://raw.githubusercontent.com/remotion-dev/remotion/6dcf676e7c82fcc60b31aab1c715003e8399eedd/packages/docs/docs/4-0-alpha.mdx
- https://raw.githubusercontent.com/remotion-dev/remotion/6dcf676e7c82fcc60b31aab1c715003e8399eedd/packages/docs/docs/4-0-migration.mdx
- https://raw.githubusercontent.com/remotion-dev/remotion/6dcf676e7c82fcc60b31aab1c715003e8399eedd/packages/docs/docs/5-0-migration.mdx

> _Authored by tool_mastery_author_agent with pattern-priority rendering. Human review recommended before treating as creator-level mastery._

## Operational Behavior and Edge Cases

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

_Weak signals observed (below 2-hit threshold): `behavior`._

## Ecosystem Position and Composition

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Trajectory and Evolution

**Status:** Sourced (prose)

_Source-grounded excerpts from fetched documentation. Keyword matches: `changelog`, `migration`._

**Excerpt 1:**

> ---
> image: /generated/articles-docs-2-0-migration.png
> id: 2-0-migration
> sidebar_label: v2.0 Migration
> title: v2.0 Migration
> crumb: "Version Upgrade"
> ---
> The following is a list of breaking changes in Remotion 2.0, as a reference for projects wanting to upgrade.
> ## Sequences are 1 frame shorter
> Because of a mistake in v1, sequences were…

**Excerpt 2:**

> ---
> image: /generated/articles-docs-3-0-migration.png
> id: 3-0-migration
> title: v3.0 Migration
> crumb: "Version Upgrade"
> ---
> When upgrading from Remotion 2 to Remotion 3, note the following changes and apply them to your project.
> ## How to upgrade
> Upgrade `remotion` and all packages starting with `@remotion` to `^3.0.0`:
> - "remotion":…

**Excerpt 3:**

> You don't have to and should not do it manually anymore - see migration guide
> ### `4.0.0-alpha5`
> May 3rd 2023:
> - Features the new Rust renderer enabling faster `
> `!
> - `z` is not exported from Remotion anymore, instead, just install `zod`!
> - `zColor` is now to be installed from `@remotion/zod-types`
> - Overall polish of the editor
> ###…

**Sources:**
- https://raw.githubusercontent.com/remotion-dev/remotion/6dcf676e7c82fcc60b31aab1c715003e8399eedd/packages/docs/docs/2-0-migration.mdx
- https://raw.githubusercontent.com/remotion-dev/remotion/6dcf676e7c82fcc60b31aab1c715003e8399eedd/packages/docs/docs/3-0-migration.mdx
- https://raw.githubusercontent.com/remotion-dev/remotion/6dcf676e7c82fcc60b31aab1c715003e8399eedd/packages/docs/docs/4-0-alpha.mdx
- https://raw.githubusercontent.com/remotion-dev/remotion/6dcf676e7c82fcc60b31aab1c715003e8399eedd/packages/docs/docs/4-0-migration.mdx
- https://raw.githubusercontent.com/remotion-dev/remotion/6dcf676e7c82fcc60b31aab1c715003e8399eedd/packages/docs/docs/5-0-migration.mdx

> _Authored by tool_mastery_author_agent with pattern-priority rendering. Human review recommended before treating as creator-level mastery._

## Conceptual Model and Solution Recipes

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Industry Expert and Cutting-Edge Usage

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.
