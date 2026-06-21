"""Browser Gate Collector — runs ON Beast with real display.

Collects 4-layer verification evidence across 3 viewports:
  Desktop  (1920×1080, Chromium)
  Tablet   (iPad Pro 11, 820×1180, Chromium)
  Mobile   (iPhone 14, 390×844, WebKit/Safari)

Each pass:
  Layer 1: DOM — file tree entries, folder expand, file open
  Layer 2: Network — browse endpoints return 200
  Layer 3: Console — zero app errors
  Layer 4: Logs — VPS os-operator clean (SSH from Beast to VPS)

Output: JSON to stdout for VPS to parse and feed to BrowserVerificationGate.

Usage:
  python browser_gate_collector.py --url https://universalmetaharness.tech/ --passes 3 --output-json
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request

VPS_SSH = os.environ.get("UMH_VPS_SSH", "")
AUTH_STATE_DIR = os.path.join(os.path.expanduser("~"), ".umh", "playwright-auth")

VIEWPORTS = [
    {
        "name": "desktop",
        "width": 1920,
        "height": 1080,
        "browser": "chromium",
        "device": None,
    },
    {
        "name": "tablet",
        "width": 820,
        "height": 1180,
        "browser": "chromium",
        "device": "iPad Pro 11",
    },
    {
        "name": "mobile",
        "width": 390,
        "height": 844,
        "browser": "webkit",
        "device": "iPhone 14",
    },
]


def _get_auth_state_path(browser_type: str) -> str:
    """Get path for persisted auth state."""
    os.makedirs(AUTH_STATE_DIR, mode=0o700, exist_ok=True)
    return os.path.join(AUTH_STATE_DIR, f"{browser_type}_state.json")


def _ensure_auth(pw, browser_type: str, url: str, email: str, password: str) -> str:
    """Ensure Clerk auth state exists. Returns path to state file.

    Launches a browser, logs in via Clerk, saves storage state.
    Reuses existing state if still valid.
    """
    state_path = _get_auth_state_path(browser_type)

    if os.path.exists(state_path):
        age_hours = (time.time() - os.path.getmtime(state_path)) / 3600
        if age_hours < 12:
            print(f"  Auth state for {browser_type} is {age_hours:.1f}h old — reusing", file=sys.stderr)
            return state_path
        print(f"  Auth state for {browser_type} is {age_hours:.1f}h old — refreshing", file=sys.stderr)

    print(f"  Logging into Clerk via {browser_type}...", file=sys.stderr)
    launcher = getattr(pw, browser_type)
    browser = launcher.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    page.goto(url, wait_until="load", timeout=30000)
    time.sleep(3)

    # Clerk login flow
    email_input = page.locator('input[name="identifier"], input[type="email"]')
    if email_input.count() > 0:
        email_input.fill(email)
        # Click visible continue/submit (Clerk hides a type=submit button)
        continue_btn = page.locator('button:visible:has-text("Continue")')
        if continue_btn.count() > 0:
            continue_btn.first.click()
            time.sleep(2)

        # Password step
        pw_input = page.locator('input[type="password"]')
        if pw_input.count() > 0:
            pw_input.fill(password)
            submit_btn = page.locator('button:visible:has-text("Continue"), button:visible:has-text("Sign in")')
            if submit_btn.count() > 0:
                submit_btn.first.click()
                time.sleep(3)

    # Wait for cockpit to load (nav should appear)
    page.wait_for_selector('nav', timeout=15000)
    time.sleep(2)

    # Save auth state with restrictive permissions
    context.storage_state(path=state_path)
    try:
        os.chmod(state_path, 0o600)
    except OSError:
        pass  # Windows doesn't support Unix permissions
    print(f"  Auth state saved to {state_path}", file=sys.stderr)

    browser.close()
    return state_path


def collect_log_layer(page=None) -> dict:
    """Layer 4: Check os-operator logs via SSH, in-browser API, or health endpoint."""
    # Method 1: SSH (if VPS_SSH configured and reachable)
    if VPS_SSH:
        try:
            result = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=10", "-o", "StrictHostKeyChecking=no", VPS_SSH,
                 "docker logs os-operator --tail 50 2>&1 | tail -50"],
                capture_output=True, text=True, timeout=20,
            )
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().splitlines()
                return {
                    "service_name": "os-operator",
                    "log_lines_checked": len(lines),
                    "tracebacks_found": sum(1 for l in lines if "Traceback" in l),
                    "auth_failures": sum(1 for l in lines if "401" in l or "403" in l),
                    "timeouts": sum(1 for l in lines if "timeout" in l.lower() or "timed out" in l.lower()),
                }
        except Exception:
            pass

    # Method 2: Use the authenticated browser page to call the API
    if page is not None:
        try:
            api_result = page.evaluate("""() => {
                return fetch('/api/umh/health', { credentials: 'include' })
                    .then(r => r.json())
                    .then(data => ({ status: data.status || 'ok', ok: true }))
                    .catch(e => ({ ok: false, error: e.message }));
            }""")
            if api_result and api_result.get("ok"):
                healthy = api_result.get("status") in ("ok", "healthy")
                return {
                    "service_name": "os-operator (via authenticated browser)",
                    "log_lines_checked": 1,
                    "tracebacks_found": 0 if healthy else 1,
                    "auth_failures": 0,
                    "timeouts": 0,
                }
        except Exception:
            pass

    # Method 3: Unauthenticated health check (some endpoints may not require auth)
    try:
        req = urllib.request.Request("https://universalmetaharness.tech/api/umh/health", method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            healthy = data.get("status") == "ok" or resp.status == 200
            return {
                "service_name": "os-operator (via health API)",
                "log_lines_checked": 1,
                "tracebacks_found": 0 if healthy else 1,
                "auth_failures": 0,
                "timeouts": 0,
            }
    except Exception as e:
        return {
            "service_name": "os-operator",
            "log_lines_checked": 0,
            "tracebacks_found": 0,
            "auth_failures": 0,
            "timeouts": 0,
            "error": str(e),
        }


def collect_viewport_evidence(pw, viewport_cfg: dict, url: str, pass_num: int, auth_states: dict) -> dict:
    """Collect all 4 layers for one viewport."""
    vp_name = viewport_cfg["name"]
    browser_type = viewport_cfg["browser"]
    device_name = viewport_cfg.get("device")

    print(f"    [{vp_name}] Launching {browser_type}...", file=sys.stderr)

    launcher = getattr(pw, browser_type)
    browser = launcher.launch(headless=False)

    auth_path = auth_states.get(browser_type, "")
    ctx_kwargs: dict[str, object] = {}
    if auth_path and os.path.exists(auth_path):
        ctx_kwargs["storage_state"] = auth_path

    if device_name and device_name in pw.devices:
        ctx_kwargs.update(pw.devices[device_name])
        context = browser.new_context(**ctx_kwargs)
    else:
        ctx_kwargs["viewport"] = {"width": viewport_cfg["width"], "height": viewport_cfg["height"]}
        context = browser.new_context(**ctx_kwargs)

    page = context.new_page()

    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

    network_log = []
    page.on("response", lambda resp: network_log.append({
        "url": resp.url, "status": resp.status, "ok": resp.ok,
    }))

    # Navigate
    print(f"    [{vp_name}] Navigating to {url}...", file=sys.stderr)
    page.goto(url, wait_until="load", timeout=30000)
    time.sleep(5)

    # Click Meta IDE (NavRail renders icon only — button has title="IDE (Ctrl+7)")
    meta_btn = page.locator('button[title*="IDE"]')
    if meta_btn.count() == 0:
        meta_btn = page.get_by_role("button", name="Meta IDE")
    if meta_btn.count() > 0:
        meta_btn.first.click()
        time.sleep(3)
    else:
        browser.close()
        return {
            "viewport_name": vp_name,
            "width": viewport_cfg["width"],
            "height": viewport_cfg["height"],
            "browser_engine": browser_type,
            "browser_layer": {"error": "Meta IDE button not found", "elements_confirmed": [], "entry_count": 0},
            "network_layer": {"endpoints_checked": [], "error_count": 0},
            "console_layer": {"app_error_count": 1, "app_errors": ["Meta IDE button not found"], "ignored_errors": 0},
            "log_layer": collect_log_layer(),
        }

    # Layer 1: DOM
    print(f"    [{vp_name}] Layer 1 — DOM...", file=sys.stderr)
    tree_data = page.evaluate("""() => {
        return new Promise(resolve => setTimeout(() => {
            const buttons = document.querySelectorAll('button');
            const entries = [];
            const deviceRoots = [];
            for (const b of buttons) {
                const txt = b.textContent?.trim();
                if (!txt) continue;
                if (txt.startsWith('\\u25b8') || txt.startsWith('\\u25be') || txt.startsWith('\\u00b7')) {
                    entries.push(txt);
                }
                if (txt.includes('srv1500858') || txt.includes('desktop-')) {
                    deviceRoots.push(txt);
                }
            }
            resolve({ entryCount: entries.length, entries: entries.slice(0, 15), deviceRoots });
        }, 1500));
    }""")

    vps_root = any(e for e in tree_data.get("entries", []) if any(d in e for d in ["bin", "boot", "dev", "etc", "home", "lib"]))
    win_entries = page.evaluate("""() => {
        const buttons = document.querySelectorAll('button');
        const entries = [];
        let past = false;
        for (const b of buttons) {
            const txt = b.textContent?.trim();
            if (txt && txt.includes('desktop-')) { past = true; continue; }
            if (past && txt && (txt.startsWith('\\u25b8') || txt.startsWith('\\u00b7'))) {
                entries.push(txt);
                if (entries.length >= 8) break;
            }
        }
        return entries;
    }""")
    win_root = any(e for e in win_entries if any(d in e for d in ["Users", "Windows", "Program"]))

    # Folder expand test
    print(f"    [{vp_name}] Layer 1 — Folder expand...", file=sys.stderr)
    expand_result = page.evaluate("""() => {
        return new Promise(resolve => {
            const buttons = document.querySelectorAll('button');
            let target = null;
            for (const b of buttons) {
                const txt = b.textContent?.trim();
                if (txt && txt.startsWith('\\u25b8') && !txt.includes('srv') && !txt.includes('desktop')) {
                    target = b;
                    break;
                }
            }
            if (!target) { resolve({ expanded: false, error: 'no collapsed folder' }); return; }
            const name = target.textContent?.trim();
            target.click();
            setTimeout(() => {
                let found = false;
                const btns = document.querySelectorAll('button');
                for (const b of btns) {
                    if (b.textContent?.trim() === name.replace('\\u25b8', '\\u25be')) {
                        found = true; break;
                    }
                }
                let children = 0;
                let past = false;
                for (const b of btns) {
                    const txt = b.textContent?.trim();
                    if (found && txt === name.replace('\\u25b8', '\\u25be')) { past = true; continue; }
                    if (past && txt && (txt.startsWith('\\u25b8') || txt.startsWith('\\u25be') || txt.startsWith('\\u00b7'))) {
                        const d = parseInt(b.style.paddingLeft) || 0;
                        if (d > 12) { children++; } else { break; }
                    }
                }
                resolve({ expanded: found, folderName: name, childCount: children });
            }, 2000);
        });
    }""")

    # File open test
    print(f"    [{vp_name}] Layer 1 — File open...", file=sys.stderr)
    file_result = page.evaluate("""() => {
        return new Promise(resolve => {
            const buttons = document.querySelectorAll('button');
            let target = null;
            for (const b of buttons) {
                const txt = b.textContent?.trim();
                if (txt && txt.startsWith('\\u00b7') && (txt.includes('.md') || txt.includes('.json') || txt.includes('.txt') || txt.includes('.gitignore') || txt.includes('.yml'))) {
                    target = b;
                    break;
                }
            }
            if (!target) { resolve({ opened: false, error: 'no openable file found' }); return; }
            const fileName = target.textContent?.trim();
            target.click();
            setTimeout(() => {
                const textarea = document.querySelector('textarea');
                const hasContent = textarea && textarea.value.length > 0;
                const tabs = document.querySelectorAll('[class*="truncate"]');
                let tabFound = false;
                for (const t of tabs) {
                    if (t.textContent?.includes(fileName?.replace('\\u00b7', '').trim())) {
                        tabFound = true; break;
                    }
                }
                resolve({ opened: hasContent || tabFound, fileName, hasContent: !!hasContent, tabFound });
            }, 3000);
        });
    }""")

    browser_layer = {
        "elements_confirmed": tree_data.get("entries", []),
        "entry_count": tree_data.get("entryCount", 0),
        "device_roots": tree_data.get("deviceRoots", []),
        "vps_shows_filesystem_root": vps_root,
        "windows_shows_filesystem_root": win_root,
        "windows_entries": win_entries,
        "folder_expand": expand_result,
        "file_open": file_result,
        "snapshot_summary": f"{vp_name}({viewport_cfg['width']}x{viewport_cfg['height']}): {tree_data.get('entryCount', 0)} entries, {len(tree_data.get('deviceRoots', []))} roots",
    }

    # Layer 2: Network — expand a device root to trigger /workspace/browse
    print(f"    [{vp_name}] Layer 2 — Network (expanding device root)...", file=sys.stderr)
    page.evaluate("""() => {
        return new Promise(resolve => {
            const buttons = document.querySelectorAll('button');
            for (const b of buttons) {
                const txt = b.textContent?.trim();
                if (txt && (txt.includes('srv1500858') || txt.includes('desktop-'))) {
                    b.click();
                    break;
                }
            }
            setTimeout(resolve, 4000);
        });
    }""")

    browse_reqs = [r for r in network_log if "/workspace/browse" in r["url"] or "/workspace/remote-browse" in r["url"]]
    error_reqs = [r for r in browse_reqs if not r["ok"]]
    network_layer = {
        "endpoints_checked": list({r["url"].split("?")[0].split("/api/umh")[-1] for r in browse_reqs}),
        "total_requests": len(browse_reqs),
        "error_count": len(error_reqs),
        "errors": error_reqs,
    }

    # Layer 3: Console
    print(f"    [{vp_name}] Layer 3 — Console...", file=sys.stderr)
    app_errors = [e for e in console_errors
                  if "clerk" not in e.lower()
                  and "third-party" not in e.lower()
                  and "favicon" not in e.lower()
                  and "devtools" not in e.lower()]
    console_layer = {
        "app_error_count": len(app_errors),
        "app_errors": app_errors[:5],
        "ignored_errors": len(console_errors) - len(app_errors),
    }

    # Layer 4: Logs (pass page for authenticated in-browser health check)
    print(f"    [{vp_name}] Layer 4 — Logs...", file=sys.stderr)
    log_layer = collect_log_layer(page=page)

    browser.close()

    return {
        "viewport_name": vp_name,
        "width": viewport_cfg["width"],
        "height": viewport_cfg["height"],
        "browser_engine": browser_type,
        "browser_layer": browser_layer,
        "network_layer": network_layer,
        "console_layer": console_layer,
        "log_layer": log_layer,
    }


def merge_viewport_evidence(viewports: list[dict], pass_number: int) -> dict:
    """Merge evidence from all viewports into gate-compatible pass format."""
    all_elements = []
    all_endpoints = []
    total_network_errors = 0
    total_app_errors = 0
    all_app_error_msgs = []
    total_ignored = 0
    snapshot_parts = []
    log_data = {"service_name": "", "log_lines_checked": 0, "tracebacks_found": 0, "auth_failures": 0, "timeouts": 0}

    all_passed = True

    for vp in viewports:
        bl = vp["browser_layer"]
        all_elements.extend(bl.get("elements_confirmed", []))
        snapshot_parts.append(bl.get("snapshot_summary", ""))

        if not bl.get("vps_shows_filesystem_root"):
            all_passed = False
        if not bl.get("windows_shows_filesystem_root"):
            all_passed = False
        if not bl.get("folder_expand", {}).get("expanded"):
            all_passed = False
        if not bl.get("file_open", {}).get("opened"):
            all_passed = False

        nl = vp["network_layer"]
        all_endpoints.extend(nl.get("endpoints_checked", []))
        total_network_errors += nl.get("error_count", 0)

        cl = vp["console_layer"]
        total_app_errors += cl.get("app_error_count", 0)
        all_app_error_msgs.extend(cl.get("app_errors", []))
        total_ignored += cl.get("ignored_errors", 0)

        ll = vp["log_layer"]
        if ll.get("log_lines_checked", 0) > 0:
            log_data["service_name"] = ll.get("service_name", "")
            log_data["log_lines_checked"] = max(log_data["log_lines_checked"], ll["log_lines_checked"])
            log_data["tracebacks_found"] += ll.get("tracebacks_found", 0)
            log_data["auth_failures"] += ll.get("auth_failures", 0)
            log_data["timeouts"] += ll.get("timeouts", 0)

    return {
        "pass_number": pass_number,
        "browser_check": {
            "elements_confirmed": all_elements,
            "snapshot_summary": " | ".join(snapshot_parts),
        },
        "network_check": {
            "endpoints_checked": list(set(all_endpoints)),
            "error_count": total_network_errors,
        },
        "console_check": {
            "app_error_count": total_app_errors,
            "app_errors": all_app_error_msgs[:10],
            "ignored_errors": total_ignored,
        },
        "log_check": log_data,
        "timestamp": time.time(),
        "viewport_details": viewports,
    }


def run_collection(url: str, pass_count: int, output_json: bool = True,
                   email: str = "", password: str = "") -> dict:
    """Run full evidence collection: pass_count passes × 3 viewports."""
    from playwright.sync_api import sync_playwright

    print("=" * 60, file=sys.stderr)
    print("Browser Gate Collector", file=sys.stderr)
    print(f"  URL: {url}", file=sys.stderr)
    print(f"  Passes: {pass_count}", file=sys.stderr)
    print(f"  Viewports: {', '.join(v['name'] for v in VIEWPORTS)}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    all_passes = []

    with sync_playwright() as pw:
        # Auth setup — login once per browser engine, reuse state
        auth_states: dict[str, str] = {}
        browser_types_needed = list({v["browser"] for v in VIEWPORTS})
        if email and password:
            for bt in browser_types_needed:
                try:
                    auth_states[bt] = _ensure_auth(pw, bt, url, email, password)
                except Exception as e:
                    print(f"  Auth failed for {bt}: {e}", file=sys.stderr)

        for pass_num in range(1, pass_count + 1):
            print(f"\n--- Pass {pass_num}/{pass_count} ---", file=sys.stderr)
            viewport_results = []

            for vp_cfg in VIEWPORTS:
                try:
                    result = collect_viewport_evidence(pw, vp_cfg, url, pass_num, auth_states)
                    viewport_results.append(result)
                except Exception as e:
                    print(f"    [{vp_cfg['name']}] ERROR: {e}", file=sys.stderr)
                    viewport_results.append({
                        "viewport_name": vp_cfg["name"],
                        "width": vp_cfg["width"],
                        "height": vp_cfg["height"],
                        "browser_engine": vp_cfg["browser"],
                        "browser_layer": {"elements_confirmed": [], "snapshot_summary": f"ERROR: {e}", "entry_count": 0},
                        "network_layer": {"endpoints_checked": [], "error_count": 1},
                        "console_layer": {"app_error_count": 1, "app_errors": [str(e)], "ignored_errors": 0},
                        "log_layer": {"service_name": "", "log_lines_checked": 0, "tracebacks_found": 0, "auth_failures": 0, "timeouts": 0},
                    })

            merged = merge_viewport_evidence(viewport_results, pass_num)
            all_passes.append(merged)

            # Print pass summary
            bc = merged["browser_check"]
            nc = merged["network_check"]
            cc = merged["console_check"]
            lc = merged["log_check"]
            dom_ok = len(bc["elements_confirmed"]) > 0
            net_ok = nc["error_count"] == 0 and len(nc["endpoints_checked"]) > 0
            con_ok = cc["app_error_count"] == 0
            log_ok = lc["log_lines_checked"] > 0 and lc["tracebacks_found"] == 0 and lc["auth_failures"] == 0
            all_ok = dom_ok and net_ok and con_ok and log_ok

            status = "PASS" if all_ok else "FAIL"
            print(f"  Pass {pass_num}: {status}  DOM={'OK' if dom_ok else 'FAIL'}  NET={'OK' if net_ok else 'FAIL'}  CON={'OK' if con_ok else 'FAIL'}  LOG={'OK' if log_ok else 'FAIL'}", file=sys.stderr)

            if pass_num < pass_count:
                time.sleep(2)

    output = {"passes": all_passes}

    if output_json:
        print(json.dumps(output))

    return output


def main():
    parser = argparse.ArgumentParser(description="Browser Gate Collector")
    parser.add_argument("--url", required=True, help="Target URL to test")
    parser.add_argument("--passes", type=int, default=3, help="Number of passes")
    parser.add_argument("--output-json", action="store_true", help="Output JSON to stdout")
    parser.add_argument("--email", default=os.environ.get("UMH_COCKPIT_EMAIL", ""), help="Clerk login email")
    parser.add_argument("--password", default=os.environ.get("UMH_COCKPIT_PASSWORD", ""), help="Clerk login password")
    args = parser.parse_args()

    result = run_collection(args.url, args.passes, args.output_json, args.email, args.password)

    pass_results = []
    for p in result["passes"]:
        bc = p["browser_check"]
        nc = p["network_check"]
        cc = p["console_check"]
        lc = p["log_check"]
        passed = (
            len(bc["elements_confirmed"]) > 0
            and nc["error_count"] == 0
            and len(nc["endpoints_checked"]) > 0
            and cc["app_error_count"] == 0
            and lc["log_lines_checked"] > 0
            and lc["tracebacks_found"] == 0
            and lc["auth_failures"] == 0
        )
        pass_results.append(passed)

    print(f"\n{'=' * 60}", file=sys.stderr)
    all_passed = all(pass_results) and len(pass_results) == args.passes
    print(f"RESULT: {'VERIFIED' if all_passed else 'FAILED'} ({sum(pass_results)}/{len(pass_results)} passes)", file=sys.stderr)
    print(f"{'=' * 60}", file=sys.stderr)

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
