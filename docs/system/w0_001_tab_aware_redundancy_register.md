# W0-001 Tab-Aware Redundancy Register

**Date**: 2026-05-04
**Status**: COMPLETE
**Supersedes**: w0_001_redundancy_register.md
**Corpus**: 283,831 words (full tab-aware extraction)

---

## 1. Summary

| Metric | Value |
|--------|-------|
| Documents analyzed | 26 (2 empty excluded) |
| Redundancy pairs found | 3 |
| High redundancy (>10% overlap) | 0 |
| Moderate redundancy (2-10%) | 3 |
| Prior register validity | INVALID (marked empty docs as empty) |

## 2. Redundancy Pairs Detected

| Doc A | Doc B | Shared Phrases | Overlap | Assessment |
|-------|-------|:--------------:|:-------:|:----------:|
| Copy of Script Storytelling | Script Storytelling Structures | High | ~95% | Intentional copy |
| Coaching Philosophy | Coaching Frameworks | Moderate | ~4% | Expected (same domain) |
| LyfeOS | EntrepreneurOS | Low | ~2.5% | Related products share terminology |

## 3. Analysis

**Very low redundancy across the corpus.** The 28 documents are largely
non-overlapping despite covering related topics. This suggests the founder
maintained distinct documents for distinct purposes.

Notable findings:
- "Copy of Script Storytelling Structures" is an intentional duplicate (marked by "Copy of")
- Coaching documents share methodology terminology but not duplicate content
- Product specs (LyfeOS/EntrepreneurOS/CreatorOS) share vocabulary but have distinct architectures

## 4. Prior Register Correction

The previous redundancy register incorrectly reported:
- CreatorOS: "empty document, possible redundancy with LyfeOS" → FALSE (27,301 words of unique content)
- Empyrean Studios: "empty document" → FALSE (10,985 words of unique brand content)

These were not redundant — they were invisible due to the first-tab-only extraction bug.

## 5. Recommendation

No consolidation needed. The corpus is well-structured:
- Each product has its own comprehensive spec
- Coaching content is split by methodology vs. frameworks vs. e-learning
- Brand docs are split by entity (personal, agency, conglomerate)
- The one true duplicate (Script Storytelling copy) can be ignored
