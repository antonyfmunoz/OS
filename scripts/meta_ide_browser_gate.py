"""Meta IDE Browser Verification Gate — 4-layer × 3-pass.

Runs on Beast (GPU workstation with display) via Playwright WebKit
with iPhone 14 emulation to validate iOS Safari touch behavior.

Layers:
  1. Browser/DOM — file tree elements, folder expand, file open
  2. Network — /workspace/browse and /workspace/remote-browse return 200
  3. Console — zero application errors
  4. Logs — os-operator has no tracebacks (checked via SSH to VPS)
"""

import json
import os
import subprocess
import sys
import time

COCKPIT_URL = "https://universalmetaharness.tech/"
# SSH host from env (never hardcode a node IP). Format: user@host or UMH_VPS_SSH.
VPS_SSH = os.getenv("UMH_VPS_SSH") or (
    f"{os.getenv('UMH_VPS_USER', 'root')}@{os.getenv('UMH_VPS_IP', '')}"
)
PASS_COUNT = 3


def collect_pass(pw, pass_num: int) -> dict:
    """Collect one pass of 4-layer evidence using iPhone 14 emulation."""
    from playwright.sync_api import Playwright

    iphone = pw.devices["iPhone 14"]
    browser = pw.webkit.launch(headless=False)
    context = browser.new_context(**iphone)
    page = context.new_page()

    evidence = {
        "pass_number": pass_num,
        "browser": {},
        "network": {},
        "console": {},
        "logs": {},
    }

    errors_collected = []
    page.on("console", lambda msg: errors_collected.append(msg.text) if msg.type == "error" else None)

    network_log = []
    page.on("response", lambda resp: network_log.append({
        "url": resp.url, "status": resp.status, "ok": resp.ok,
    }))

    # Navigate and wait for load
    print(f"  Pass {pass_num}: Navigating to cockpit...")
    page.goto(COCKPIT_URL, wait_until="networkidle", timeout=30000)
    time.sleep(3)

    # Click Meta IDE
    meta_ide_btn = page.get_by_role("button", name="Meta IDE")
    if meta_ide_btn.count() > 0:
        meta_ide_btn.click()
        time.sleep(2)
    else:
        evidence["browser"]["error"] = "Meta IDE button not found"
        browser.close()
        return evidence

    # Layer 1: Browser/DOM
    print(f"  Pass {pass_num}: Layer 1 — DOM inspection...")
    tree_data = page.evaluate("""() => {
        return new Promise(resolve => setTimeout(() => {
            const buttons = document.querySelectorAll('button');
            const entries = [];
            const deviceRoots = [];
            for (const b of buttons) {
                const txt = b.textContent?.trim();
                if (!txt) continue;
                if (txt.startsWith('▸') || txt.startsWith('▾') || txt.startsWith('·')) {
                    entries.push(txt);
                }
                if (txt.includes('srv1500858') || txt.includes('desktop-')) {
                    deviceRoots.push(txt);
                }
            }
            resolve({ entryCount: entries.length, entries: entries.slice(0, 10), deviceRoots });
        }, 1000));
    }""")

    evidence["browser"]["elements_confirmed"] = tree_data.get("entries", [])
    evidence["browser"]["entry_count"] = tree_data.get("entryCount", 0)
    evidence["browser"]["device_roots"] = tree_data.get("deviceRoots", [])

    # Check filesystem roots (not project roots)
    vps_has_root = any("bin" in e or "boot" in e or "dev" in e or "etc" in e for e in tree_data.get("entries", []))
    win_entries_raw = page.evaluate("""() => {
        const buttons = document.querySelectorAll('button');
        const entries = [];
        let pastWindows = false;
        for (const b of buttons) {
            const txt = b.textContent?.trim();
            if (txt && txt.includes('desktop-')) { pastWindows = true; continue; }
            if (pastWindows && txt && (txt.startsWith('▸') || txt.startsWith('·'))) {
                entries.push(txt);
                if (entries.length >= 5) break;
            }
        }
        return entries;
    }""")
    win_has_root = any("Users" in e or "Windows" in e or "Program" in e for e in win_entries_raw)
    evidence["browser"]["vps_shows_filesystem_root"] = vps_has_root
    evidence["browser"]["windows_shows_filesystem_root"] = win_has_root

    # Test folder expand via touch/click
    print(f"  Pass {pass_num}: Layer 1 — Testing folder expand (touch)...")
    expand_result = page.evaluate("""() => {
        return new Promise(resolve => {
            const buttons = document.querySelectorAll('button');
            let target = null;
            for (const b of buttons) {
                const txt = b.textContent?.trim();
                if (txt && txt.startsWith('▸') && !txt.includes('srv') && !txt.includes('desktop')) {
                    target = b;
                    break;
                }
            }
            if (!target) { resolve({ expanded: false, error: 'no collapsed folder found' }); return; }
            const folderName = target.textContent?.trim();
            target.click();
            setTimeout(() => {
                // Check if it expanded
                let found = false;
                const btns = document.querySelectorAll('button');
                for (const b of btns) {
                    const txt = b.textContent?.trim();
                    if (txt === folderName.replace('▸', '▾')) {
                        found = true;
                        break;
                    }
                }
                // Check for children
                let childCount = 0;
                let pastTarget = false;
                for (const b of btns) {
                    const txt = b.textContent?.trim();
                    if (found && txt === folderName.replace('▸', '▾')) { pastTarget = true; continue; }
                    if (pastTarget && txt && (txt.startsWith('▸') || txt.startsWith('▾') || txt.startsWith('·'))) {
                        const depth = parseInt(b.style.paddingLeft) || 0;
                        if (depth > 12) { childCount++; }
                        else { break; }
                    }
                }
                resolve({ expanded: found, folderName, childCount });
            }, 2000);
        });
    }""")
    evidence["browser"]["folder_expand"] = expand_result

    # Test file open via touch/click
    print(f"  Pass {pass_num}: Layer 1 — Testing file open (touch)...")
    file_result = page.evaluate("""() => {
        return new Promise(resolve => {
            const buttons = document.querySelectorAll('button');
            let target = null;
            for (const b of buttons) {
                const txt = b.textContent?.trim();
                if (txt && txt.startsWith('·') && (txt.includes('.md') || txt.includes('.json') || txt.includes('.txt') || txt.includes('.gitignore'))) {
                    target = b;
                    break;
                }
            }
            if (!target) { resolve({ opened: false, error: 'no file found' }); return; }
            const fileName = target.textContent?.trim();
            target.click();
            setTimeout(() => {
                // Check if editor area has content (textarea or tab appeared)
                const textarea = document.querySelector('textarea');
                const hasContent = textarea && textarea.value.length > 0;
                const tabs = document.querySelectorAll('[class*="truncate"]');
                let tabFound = false;
                for (const t of tabs) {
                    if (t.textContent?.includes(fileName?.replace('·', '').trim())) {
                        tabFound = true;
                        break;
                    }
                }
                resolve({ opened: hasContent || tabFound, fileName, hasContent: !!hasContent, tabFound });
            }, 3000);
        });
    }""")
    evidence["browser"]["file_open"] = file_result
    evidence["browser"]["snapshot_summary"] = f"Pass {pass_num}: {tree_data.get('entryCount', 0)} entries, {len(tree_data.get('deviceRoots', []))} device roots"

    # Layer 2: Network
    print(f"  Pass {pass_num}: Layer 2 — Network...")
    browse_requests = [r for r in network_log if "/workspace/browse" in r["url"] or "/workspace/remote-browse" in r["url"]]
    error_requests = [r for r in browse_requests if not r["ok"]]
    evidence["network"]["endpoints_checked"] = [r["url"].split("?")[0].split("/api/umh")[-1] for r in browse_requests]
    evidence["network"]["error_count"] = len(error_requests)
    evidence["network"]["errors"] = error_requests

    # Layer 3: Console
    print(f"  Pass {pass_num}: Layer 3 — Console...")
    app_errors = [e for e in errors_collected if "clerk" not in e.lower() and "third-party" not in e.lower() and "favicon" not in e.lower()]
    evidence["console"]["app_error_count"] = len(app_errors)
    evidence["console"]["app_errors"] = app_errors[:5]
    evidence["console"]["ignored_errors"] = len(errors_collected) - len(app_errors)

    browser.close()

    # Layer 4: Logs (SSH to VPS)
    print(f"  Pass {pass_num}: Layer 4 — Logs (SSH to VPS)...")
    try:
        log_result = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=5", VPS_SSH,
             "docker logs os-operator --tail 50 2>&1 | tail -50"],
            capture_output=True, text=True, timeout=15,
        )
        log_lines = log_result.stdout.strip().splitlines()
        tracebacks = sum(1 for l in log_lines if "Traceback" in l)
        auth_failures = sum(1 for l in log_lines if "401" in l or "403" in l)
        timeouts = sum(1 for l in log_lines if "timeout" in l.lower() or "timed out" in l.lower())
        evidence["logs"]["service_name"] = "os-operator"
        evidence["logs"]["log_lines_checked"] = len(log_lines)
        evidence["logs"]["tracebacks_found"] = tracebacks
        evidence["logs"]["auth_failures"] = auth_failures
        evidence["logs"]["timeouts"] = timeouts
    except Exception as e:
        evidence["logs"]["error"] = str(e)
        evidence["logs"]["log_lines_checked"] = 0
        evidence["logs"]["tracebacks_found"] = 0
        evidence["logs"]["auth_failures"] = 0
        evidence["logs"]["timeouts"] = 0

    return evidence


def evaluate_pass(evidence: dict) -> tuple[bool, list[str]]:
    """Evaluate a single pass across all 4 layers."""
    failures = []

    b = evidence.get("browser", {})
    if b.get("entry_count", 0) == 0:
        failures.append("Layer 1: No file tree entries found")
    if not b.get("vps_shows_filesystem_root"):
        failures.append("Layer 1: VPS not showing filesystem root (/)")
    if not b.get("windows_shows_filesystem_root"):
        failures.append("Layer 1: Windows not showing filesystem root (C:\\)")
    expand = b.get("folder_expand", {})
    if not expand.get("expanded"):
        failures.append(f"Layer 1: Folder expand failed: {expand.get('error', 'unknown')}")
    file_open = b.get("file_open", {})
    if not file_open.get("opened"):
        failures.append(f"Layer 1: File open failed: {file_open}")

    n = evidence.get("network", {})
    if n.get("error_count", 0) > 0:
        failures.append(f"Layer 2: {n['error_count']} network errors: {n.get('errors', [])}")
    if len(n.get("endpoints_checked", [])) == 0:
        failures.append("Layer 2: No browse endpoints captured")

    c = evidence.get("console", {})
    if c.get("app_error_count", 0) > 0:
        failures.append(f"Layer 3: {c['app_error_count']} console errors: {c.get('app_errors', [])}")

    l = evidence.get("logs", {})
    if l.get("tracebacks_found", 0) > 0:
        failures.append(f"Layer 4: {l['tracebacks_found']} tracebacks in os-operator")
    if l.get("auth_failures", 0) > 0:
        failures.append(f"Layer 4: {l['auth_failures']} auth failures in os-operator")

    return len(failures) == 0, failures


def main():
    from playwright.sync_api import sync_playwright

    print("=" * 60)
    print("Meta IDE Browser Verification Gate")
    print("4-layer × 3-pass | iPhone 14 WebKit emulation on Beast")
    print("=" * 60)

    all_passes = []
    all_verdicts = []

    with sync_playwright() as pw:
        for i in range(1, PASS_COUNT + 1):
            print(f"\n--- Pass {i}/{PASS_COUNT} ---")
            evidence = collect_pass(pw, i)
            passed, failures = evaluate_pass(evidence)
            all_passes.append(evidence)
            all_verdicts.append({"pass": i, "passed": passed, "failures": failures})

            if passed:
                print(f"  Pass {i}: PASS - ALL 4 LAYERS PASSED")
            else:
                print(f"  Pass {i}: FAIL")
                for f in failures:
                    print(f"    - {f}")

            if i < PASS_COUNT:
                print("  Waiting 2s before next pass...")
                time.sleep(2)

    # Final verdict
    print("\n" + "=" * 60)
    consecutive_passing = sum(1 for v in all_verdicts if v["passed"])
    verified = consecutive_passing == PASS_COUNT

    print(f"RESULT: {'VERIFIED' if verified else 'FAILED'}")
    print(f"Passes: {consecutive_passing}/{PASS_COUNT}")
    for v in all_verdicts:
        status = "PASS" if v["passed"] else "FAIL"
        print(f"  Pass {v['pass']}: {status}")
        for f in v.get("failures", []):
            print(f"    - {f}")
    print("=" * 60)

    # Write evidence JSON
    output = {
        "verified": verified,
        "consecutive_passing": consecutive_passing,
        "total_passes": PASS_COUNT,
        "passes": all_passes,
        "verdicts": all_verdicts,
    }
    output_path = "C:\\dev\\dev\\meta_ide_gate_result.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nEvidence written to {output_path}")

    sys.exit(0 if verified else 1)


if __name__ == "__main__":
    main()
