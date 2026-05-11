"""
Drive UI inventory comparator for Phase 95.0.

Compares a computer-use-derived Drive inventory against the API baseline
to validate the fallback path's accuracy.

The API baseline is used for validation only — it is not the source of
truth for the computer-use test. The test proves the system CAN inventory
Drive through the visible UI alone.
"""

from __future__ import annotations

from typing import Any

from runtime.transport.local_gui_control_contracts import GUIInventoryItem


def normalize_name_for_comparison(name: str) -> str:
    """Normalize a file name for fuzzy comparison."""
    return name.strip().lower()


def build_api_baseline_names(api_inventory: list[dict[str, Any]]) -> set[str]:
    """Extract normalized names from API inventory."""
    return {normalize_name_for_comparison(f.get("name", "")) for f in api_inventory if f.get("name")}


def build_cu_names(cu_items: list[GUIInventoryItem]) -> set[str]:
    """Extract normalized names from computer-use inventory."""
    return {normalize_name_for_comparison(item.name) for item in cu_items if item.name}


def compare_inventories(
    api_inventory: list[dict[str, Any]],
    cu_items: list[GUIInventoryItem],
) -> dict[str, Any]:
    """Compare computer-use inventory against API baseline.

    Returns comparison report with:
    - matching items
    - missing from CU (in API but not CU)
    - extra in CU (in CU but not API)
    - count difference
    - confidence score
    """
    api_names = build_api_baseline_names(api_inventory)
    cu_names = build_cu_names(cu_items)

    matching = api_names & cu_names
    missing_from_cu = api_names - cu_names
    extra_in_cu = cu_names - api_names

    api_count = len(api_inventory)
    cu_count = len(cu_items)

    if api_count == 0 and cu_count == 0:
        confidence = 1.0
    elif api_count == 0:
        confidence = 0.0
    else:
        confidence = len(matching) / max(api_count, cu_count)

    return {
        "api_baseline_count": api_count,
        "cu_inventory_count": cu_count,
        "count_difference": cu_count - api_count,
        "matching_items": sorted(matching),
        "matching_count": len(matching),
        "missing_from_cu": sorted(missing_from_cu),
        "missing_from_cu_count": len(missing_from_cu),
        "extra_in_cu": sorted(extra_in_cu),
        "extra_in_cu_count": len(extra_in_cu),
        "confidence_score": round(confidence, 3),
        "confidence_rating": _rate_confidence(confidence),
    }


def _rate_confidence(score: float) -> str:
    """Rate the confidence score."""
    if score >= 0.95:
        return "HIGH"
    elif score >= 0.80:
        return "MEDIUM"
    elif score >= 0.50:
        return "LOW"
    else:
        return "VERY_LOW"


def find_name_mismatches(
    api_inventory: list[dict[str, Any]],
    cu_items: list[GUIInventoryItem],
    threshold: float = 0.8,
) -> list[dict[str, str]]:
    """Find potential name mismatches (similar but not exact).

    Uses simple character overlap ratio for fuzzy matching.
    """
    api_names = {normalize_name_for_comparison(f.get("name", "")): f.get("name", "")
                 for f in api_inventory if f.get("name")}
    cu_name_map = {normalize_name_for_comparison(item.name): item.name
                   for item in cu_items if item.name}

    api_set = set(api_names.keys())
    cu_set = set(cu_name_map.keys())

    unmatched_api = api_set - cu_set
    unmatched_cu = cu_set - api_set

    mismatches: list[dict[str, str]] = []

    for api_norm in unmatched_api:
        for cu_norm in unmatched_cu:
            ratio = _similarity_ratio(api_norm, cu_norm)
            if ratio >= threshold:
                mismatches.append({
                    "api_name": api_names[api_norm],
                    "cu_name": cu_name_map[cu_norm],
                    "similarity": f"{ratio:.2f}",
                })

    return mismatches


def _similarity_ratio(a: str, b: str) -> float:
    """Simple character overlap similarity."""
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    return len(common) / max(len(set(a)), len(set(b)))


def build_comparison_report(
    comparison: dict[str, Any],
    mismatches: list[dict[str, str]],
    observation_method: str = "",
) -> dict[str, Any]:
    """Build the full comparison report."""
    return {
        "work_order": "WO-LOCAL-PILOT-GDRIVE-GDOCS-001",
        "comparison_type": "CU_VS_API_BASELINE",
        "observation_method": observation_method,
        "api_baseline_count": comparison["api_baseline_count"],
        "cu_inventory_count": comparison["cu_inventory_count"],
        "matching_count": comparison["matching_count"],
        "missing_from_cu_count": comparison["missing_from_cu_count"],
        "extra_in_cu_count": comparison["extra_in_cu_count"],
        "confidence_score": comparison["confidence_score"],
        "confidence_rating": comparison["confidence_rating"],
        "name_mismatches": mismatches,
        "proves": "System CAN inventory Drive through visible UI when APIs unavailable",
        "does_not_prove": "CU path is as reliable/complete as API path",
    }
