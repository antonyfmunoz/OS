#!/usr/bin/env python3
"""CodeWiki verifier — the single acceptance check for docs/codewiki/.

Asserts (Inventory & Audit Verification Protocol — never claim 100% without
matching numbers):

  1. Reconciliation: an independent re-walk of the tree matches
     _manifest.json per directory. CODE/SKILL dirs must match EXACTLY
     (they change only via commits). ROLLUP dirs and excluded categories
     may drift on a live system (logs/ grows continuously) — drift is
     reported and bounded (< 0.5% or < 2,000 files per dir).
  2. Row-count truth: every inventory page's table row count equals the
     manifest count for that directory (files + symlinks).
  3. Coverage: every top-level directory has an inventory page AND a
     narrative page under dirs/, and index.md links to every page.
  4. Hygiene: all relative markdown links resolve; no TODO/PLACEHOLDER
     markers; no near-empty pages.
  5. SHA pinning: repo HEAD equals manifest git_sha (warning only).

Exit codes: 0 pass, 1 reconciliation/coverage failure, 2 setup error.

Usage:
    UMH_ROOT=/opt/OS python3 scripts/verify_codewiki.py \
        [--wiki /path/to/docs/codewiki]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_codewiki as gen  # noqa: E402 — shared walk rules, same UMH_ROOT

ROLLUP_DRIFT_FRac = 0.005
ROLLUP_DRIFT_ABS = 2000

ROW_RE = re.compile(r"^\| `")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)#]+)(?:#[^)]*)?\)")
PLACEHOLDER_RE = re.compile(r"\b(TODO|PLACEHOLDER|TBD|FIXME|XXX)\b")


def fail(msg: str, failures: list[str]) -> None:
    failures.append(msg)
    print(f"  FAIL  {msg}")


def ok(msg: str) -> None:
    print(f"  ok    {msg}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--wiki", type=Path, default=gen.ROOT / "docs" / "codewiki")
    args = ap.parse_args()
    wiki: Path = args.wiki

    manifest_path = wiki / "_manifest.json"
    if not manifest_path.is_file():
        print(f"no manifest at {manifest_path}")
        return 2
    manifest = json.loads(manifest_path.read_text())
    failures: list[str] = []

    # ── 1. Reconciliation: independent re-walk vs manifest ──────────────────
    print(f"[1/5] Re-walking {gen.ROOT} for independent reconciliation …")
    reports, excluded, unknown = gen.walk_repo()
    if unknown:
        fail(f"unclassified top-level dirs: {unknown}", failures)

    print("\n  Reconciliation table (manifest vs re-walk):")
    print(f"  {'dir':<18}{'treat':<8}{'manifest':>10}{'re-walk':>10}{'delta':>8}  verdict")
    man_dirs = manifest.get("dirs", {})
    for name in sorted(set(man_dirs) | set(reports)):
        m = man_dirs.get(name, {})
        r = reports.get(name)
        mf = m.get("files", -1)
        rf = r.n_files if r else -1
        treat = m.get("treatment", "?")
        delta = rf - mf
        if treat in ("code", "skill"):
            verdict = "MATCH" if delta == 0 else "MISMATCH"
            if delta != 0:
                fail(
                    f"{name}: code-dir count drifted by {delta:+d} "
                    f"(manifest {mf:,} vs re-walk {rf:,}) — regenerate",
                    failures,
                )
        else:
            bound = max(ROLLUP_DRIFT_ABS, int(mf * ROLLUP_DRIFT_FRac))
            verdict = "drift-ok" if abs(delta) <= bound else "DRIFT-EXCESS"
            if abs(delta) > bound:
                fail(f"{name}: rollup drift {delta:+d} exceeds bound {bound}", failures)
        print(f"  {name:<18}{treat:<8}{mf:>10,}{rf:>10,}{delta:>+8,}  {verdict}")

    acc_gen = manifest.get("accounted_files", -1)
    raw_gen = manifest.get("raw_total_files", -1)
    delta_gen = raw_gen - acc_gen
    # logs/ can grow between the generator's two passes; small deltas are
    # live-system noise, not missing coverage.
    if abs(delta_gen) > ROLLUP_DRIFT_ABS:
        fail(
            f"generation-time accounting gap: raw {raw_gen:,} vs "
            f"accounted {acc_gen:,} (delta {delta_gen:+,})",
            failures,
        )
    else:
        ok(
            f"full accounting at generation: raw {raw_gen:,} vs accounted "
            f"{acc_gen:,} (delta {delta_gen:+,}, within live-drift bound)"
        )

    # ── 2. Inventory page row counts == manifest ─────────────────────────────
    print("\n[2/5] Inventory row counts vs manifest …")
    for name, m in sorted(man_dirs.items()):
        page = wiki / "inventory" / f"{gen._slug(name)}.md"
        if not page.is_file():
            fail(f"missing inventory page for {name}", failures)
            continue
        if m.get("treatment") == "rollup":
            continue  # rollup pages tabulate subdirs, not files
        rows = sum(1 for line in page.read_text().splitlines() if ROW_RE.match(line))
        expect = m.get("files", 0) + m.get("links", 0)
        if name == "skills":
            # skills page: overview table + appendix → appendix rows only
            appendix = page.read_text().split("## Complete File Appendix", 1)
            rows = sum(1 for line in appendix[-1].splitlines() if ROW_RE.match(line))
        if rows != expect:
            fail(f"{name}: page rows {rows:,} != manifest {expect:,}", failures)
        else:
            ok(f"{name}: {rows:,} rows == manifest")

    # ── 3. Coverage: dirs/ page + index links ────────────────────────────────
    print("\n[3/5] Coverage: narrative pages + index links …")
    index_path = wiki / "index.md"
    index_text = index_path.read_text() if index_path.is_file() else ""
    if not index_text:
        fail("index.md missing or empty", failures)
    for name in sorted(man_dirs):
        slug = gen._slug(name)
        if not (wiki / "dirs" / f"{slug}.md").is_file():
            fail(f"missing narrative page dirs/{slug}.md", failures)
        if f"{slug}.md" not in index_text:
            fail(f"index.md does not link {slug}.md", failures)
    if not failures:
        ok(f"all {len(man_dirs)} dirs have narrative pages and index links")

    # ── 4. Hygiene: links resolve, no placeholders, no stubs ────────────────
    print("\n[4/5] Link resolution + placeholder scan …")
    n_links = n_broken = 0
    for md in sorted(wiki.rglob("*.md")):
        text = md.read_text(errors="replace")
        for match in LINK_RE.finditer(text):
            target = match.group(1).strip()
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            n_links += 1
            if not (md.parent / target).resolve().exists():
                n_broken += 1
                fail(f"broken link in {md.relative_to(wiki)}: {target}", failures)
        rel = md.relative_to(wiki)
        if str(rel).startswith("dirs/") or rel.name in (
            "index.md",
            "architecture.md",
            "data-flow.md",
            "tech-stack.md",
            "services-runtime.md",
            "conventions.md",
            "health-findings.md",
        ):
            if PLACEHOLDER_RE.search(text):
                fail(f"placeholder marker in {rel}", failures)
            if len(text) < 400:
                fail(f"near-empty page {rel} ({len(text)} bytes)", failures)
    ok(f"{n_links:,} relative links checked, {n_broken} broken")

    # ── 5. SHA pinning ───────────────────────────────────────────────────────
    print("\n[5/5] SHA pinning …")
    try:
        head = subprocess.run(
            ["git", "-C", str(gen.ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout.strip()
    except Exception:
        head = "unknown"
    if head != manifest.get("git_sha"):
        print(
            f"  WARN  HEAD {head[:9]} != manifest "
            f"{manifest.get('git_sha', '?')[:9]} (tree drifted since "
            "generation — regenerate before merge)"
        )
    else:
        ok(f"HEAD matches manifest SHA {head[:9]}")

    print(f"\n{'PASS' if not failures else 'FAIL'} — {len(failures)} failure(s)")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
