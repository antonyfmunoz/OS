# Add Xquik Apify Actors: Execution Summary

## Outcome

Added both Xquik X Actors without replacing any existing integration.
Refreshed Apify authentication, rate-limit, approval, and validation guidance.

## What Changed

### Apify Skill

- Added X post and audience work to the trigger.
- Added both direct Apify Store listings.
- Added bounded Tweet and Follower input examples.
- Added explicit paid-run approval and live-pricing checks.
- Added untrusted-input, privacy, and compliance guidance.
- Preserved all 3 existing Instagram Actors and workflows.
- Bumped the Skill from 1.0 to 1.1.
- Corrected the Tool Mastery speed category to `medium`.

### Apify Best Practices

- Replaced token-bearing URLs with bearer authentication.
- Removed unsupported fixed API-rate claims.
- Added bounded paid-run approval as the first anti-pattern.
- Added a compact gotcha index for the native quality audit.
- Kept the main reference below 1,000 lines.

### Xquik Actor Reference

- Added one focused reference for both Actors.
- Documented canonical modes, relations, and output controls.
- Added a reusable approval gate.
- Added strict result-shape and cap validation.
- Added the exact Xquik independence notice.

## Verification

- Apify Skill verifier: pass
- Tool Mastery quality audit: A
- Frontmatter: 10/10
- Required best-practice sections: 19/19
- Content depth: 6/6
- Quality warnings: 0
- Python examples: parsed
- Current Actor schemas: matched
- Actor Store links: HTTP 200
- Markdown links: resolved
- Diff whitespace: clean
- Simplify review: clean
- Thermonuclear review: clean after reference split
- Actor runs: 0

The full pre-commit runner reaches its Linux firewall gate on macOS, where
`iptables` is unavailable. All portable and change-relevant gates run
separately before commit.
