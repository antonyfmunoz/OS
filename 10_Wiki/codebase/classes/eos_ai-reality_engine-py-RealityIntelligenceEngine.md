---
type: codebase-class
file: eos_ai/reality_engine.py
line: 94
generated: 2026-04-12
---

# RealityIntelligenceEngine

**File:** [[eos_ai-reality_engine-py]] | **Line:** 94

Continuously running intelligence layer. Detects market signals,
classifies by priority tier, and routes through the event bus.

Reasons from known venture data — real web scraping replaces the
simulation layer when browser tools are wired in.

## Methods

- [[eos_ai-reality_engine-py-RealityIntelligenceEngine-__init__]]`(ctx)` — 
- [[eos_ai-reality_engine-py-RealityIntelligenceEngine-_venture_scan_ready]]`(venture_id) → bool` — Return True if the venture has enough real data to ground a scan.
- [[eos_ai-reality_engine-py-RealityIntelligenceEngine-scan_market_signals]]`(venture_id) → list[dict]` — Scan market signals using live web data via ScraplingConnector,
- [[eos_ai-reality_engine-py-RealityIntelligenceEngine-classify_signal]]`(signal) → str` — Classify signal into CRITICAL / HIGH / NORMAL / BACKGROUND.
- [[eos_ai-reality_engine-py-RealityIntelligenceEngine-process_signal_queue]]`() → dict` — Run scan_market_signals() for each venture, classify, and route by tier.
- [[eos_ai-reality_engine-py-RealityIntelligenceEngine-run_competitor_analysis]]`(venture_id, competitor) → dict` — Deep analysis of a specific competitor.
- [[eos_ai-reality_engine-py-RealityIntelligenceEngine-generate_truth_report]]`(venture_id) → str` — On-demand competitor DNA analysis and strategic synthesis.
