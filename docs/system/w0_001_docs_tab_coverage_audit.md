# W0-001 Google Docs Tab Coverage Audit

**Date**: 2026-05-04
**Status**: COMPLETE
**Finding**: CRITICAL — Prior ingestion captured only 7.9% of actual content

---

## 1. Audit Summary

| Metric | Value |
|--------|-------|
| Total Google Docs | 28 |
| Multi-tab docs | 19 |
| Single-tab docs | 9 |
| Prior extraction coverage | **7.9% (22,431 of 283,831 words)** |
| Prior extraction risk | **API_FIRST_TAB_ONLY_RISK** |
| Missing content | **261,400 words (92.1%)** |

## 2. Root Cause

The prior ingestion used `gws docs documents get --params '{"documentId": "..."}'`
**WITHOUT** `includeTabsContent: true`. This causes the Google Docs API to return
only `document.body` (the first/default tab), not `document.tabs`.

Google Docs added multi-tab support in 2024. Without `includeTabsContent=true`:
- API response contains `body` field (first tab only)
- API response does NOT contain `tabs` field
- All other tabs are silently omitted

With `includeTabsContent=true`:
- API response contains `tabs` field (all tabs recursively)
- API response does NOT contain `body` field (tabs replace it)
- Each tab has `documentTab.body` with full content

## 3. Per-Document Tab Register

| Document | Tabs | First Tab Words | All Tabs Words | Coverage |
|----------|:----:|:---------------:|:--------------:|:--------:|
| LYFEOS | **53** | 255 | 44,400 | 0.6% |
| EntrepreneurOS | **14** | 740 | 40,222 | 1.8% |
| Coaching Philosophy/Methodology | **35** | 1,646 | 34,683 | 4.7% |
| CreatorOS | **8** | 0 | 27,301 | 0% |
| Systems Inventory (Virality Bible) | **20** | 1,833 | 22,695 | 8.1% |
| Coaching Frameworks & Workbooks | **30** | 1,446 | 19,800 | 7.3% |
| Antony F. Munoz (Personal Brand) | **21** | 1,647 | 19,070 | 8.6% |
| UMH | **8** | 963 | 13,949 | 6.9% |
| Conglomerate Brands | **15** | 1,487 | 11,487 | 12.9% |
| Empyrean Studios (Agency Brand) | **15** | 0 | 10,985 | 0% |
| Life Coaching (E-Learning) | **29** | 848 | 9,717 | 8.7% |
| Content | **25** | 813 | 9,226 | 8.8% |
| Untitled (1a9HYn, coaching/outreach) | **7** | 1,440 | 4,233 | 34.0% |
| AI Tools | **5** | 29 | 2,677 | 1.1% |
| Untitled (11NeGX, UnifiedInfluence) | **4** | 426 | 2,119 | 20.1% |
| Business Template | **10** | 673 | 2,072 | 32.5% |
| Untitled (11Kd3l, dev setup) | **3** | 319 | 995 | 32.1% |
| Antony Munoz Email Sequence | **2** | 342 | 676 | 50.6% |
| Personal Curriculum | **8** | 106 | 106 | 100% |
| Hunter Hoffman - Service Contract | 1 | 2,672 | 2,672 | 100% |
| Copy of Script Storytelling... | 1 | 1,575 | 1,575 | 100% |
| Script Storytelling Structures | 1 | 1,575 | 1,575 | 100% |
| SEMAX | 1 | 299 | 299 | 100% |
| Untitled (Hormozi, 1-FhleB) | 1 | 952 | 952 | 100% |
| Copy of Claude Cowork Plugins | 1 | 310 | 310 | 100% |
| Untitled (10yvoP, SDK) | 1 | 35 | 35 | 100% |
| Automations | 1 | 0 | 0 | — |
| AI Agents | 1 | 0 | 0 | — |

## 4. Most Impacted Documents

These documents had the most content hidden in non-first tabs:

1. **LYFEOS** — 53 tabs, 44,145 words missed (entire product spec)
2. **EntrepreneurOS** — 14 tabs, 39,482 words missed
3. **Coaching Philosophy** — 35 tabs, 33,037 words missed
4. **CreatorOS** — 8 tabs, 27,301 words missed (appeared "empty" before!)
5. **Systems Inventory** — 20 tabs, 20,862 words missed
6. **Coaching Frameworks** — 30 tabs, 18,354 words missed
7. **Antony F. Munoz (Personal Brand)** — 21 tabs, 17,423 words missed
8. **Empyrean Studios** — 15 tabs, 10,985 words missed (appeared "empty"!)

## 5. Previous Findings Now Invalid

The prior ingestion report marked these as "empty":
- **CreatorOS** — actually 27,301 words across 8 tabs
- **Empyrean Studios (Agency Brand)** — actually 10,985 words across 15 tabs

The prior source graph, stale assumption register, and redundancy register
are based on only 7.9% of actual content and MUST be re-evaluated after
full tab-aware re-extraction.

## 6. Corrective Action Required

A full tab-aware re-extraction using `includeTabsContent=true` is needed.
This has been partially completed as part of this audit (word counts verified
for all tabs) but the full text content should be re-extracted and stored.

## 7. Tab-Aware API Call Pattern

```
gws docs documents get --params '{"documentId": "<ID>", "includeTabsContent": true}'
```

Response structure:
```json
{
  "tabs": [
    {
      "tabProperties": { "tabId": "...", "title": "..." },
      "documentTab": { "body": { "content": [...] } },
      "childTabs": [ ... recursive ... ]
    }
  ]
}
```

Extraction must:
1. Set `includeTabsContent: true`
2. Iterate `document.tabs` (not `document.body`)
3. Recursively traverse `childTabs`
4. Extract text from each `tab.documentTab.body`
5. Preserve tab provenance (ID, title, depth, parent path)
