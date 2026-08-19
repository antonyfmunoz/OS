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

## Verification Record

Verified at `2026-08-19T05:18:27Z` after rebasing onto `c9ac68225`.

| Command | Result |
|---------|--------|
| `UMH_ROOT="$PWD" python3 -m scripts.verify_tool_skill --skill apify` | Pass |
| `UMH_ROOT="$PWD" python3 -m scripts.tme_quality_audit apify` | A, 10/10 frontmatter, 19/19 sections, 6/6 depth, 0 warnings |
| `uv run --python 3.11 --with pytest --with pytest-asyncio --with requests python -m pytest tests/test_apify_xquik_docs.py -q` | 3 passed |
| `uvx ruff check tests/test_apify_xquik_docs.py` | Pass |
| `uvx ruff format --check tests/test_apify_xquik_docs.py` | Pass |
| `git diff --check` | Pass |

The committed regression at `tests/test_apify_xquik_docs.py` parses all 38
Python examples. It executes the paid-run helper offline and proves the request
sends only `maxTotalChargeUsd`. It also rejects pricing-model drift.

Public Actor metadata checks returned these IDs with `PAY_PER_EVENT` pricing:

- X Tweet Scraper: `wAusCMrm284Voaw86`
- X Follower Scraper: `AaT0BcKU5GQh97wdt`

Both Store listing checks returned HTTP 200. No Actor was run.

### Partial Platform Gate

The canonical command was:

```bash
uv run --python 3.11 --with pydantic --with pyyaml --with psutil \
  --with pytest bash scripts/pre-commit
```

Gates 1 through 8 passed. Gate 9 stopped because macOS lacks Docker and
`iptables`. Gates 10 through 14 then passed separately with the same Python
3.11 environment. Overall canonical verification remains partial until the
Linux firewall-state gate runs on a host with `iptables`.
