// userscript_meet_captions.example.js
//
// This file is a reference example, not active code.
// No HTTP endpoint ships with EOS — operator wires their own `curl` or
// writes via meet_caption_writer.py --stdin.
//
// Intent: demonstrate how a Tampermonkey/Violentmonkey userscript could
// observe the Google Meet captions DOM and forward each new caption line
// to a tiny localhost shim the operator runs by hand. The shim then pipes
// lines into `python3 scripts/meet_caption_writer.py --stdin ...`.
//
// Do NOT hardcode Meet selectors in production — Meet changes its DOM
// frequently. Treat the selector below as a starting hint.
// As of this writing, live captions live inside a container marked with
// [aria-live="polite"]; speaker names sit in a nearby span. Inspect with
// devtools and adapt.

(function () {
  "use strict";

  // Operator-configured shim endpoint. Not shipped by EOS.
  const ENDPOINT = "http://localhost:8799/caption";
  const MEETING_CODE = location.pathname.replace(/^\//, "") || "unknown";
  const SOURCE = "google_meet";

  // Dedup window — Meet emits partial caption updates; we only forward
  // on final changes.
  const seen = new Map();
  const DEDUP_MS = 4000;

  function nowIsoUtc() {
    return new Date().toISOString().replace(/Z?$/, "Z");
  }

  function post(record) {
    // Fire-and-forget. Operator shim must be running.
    fetch(ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(record),
      mode: "no-cors",
    }).catch(() => {});
  }

  function handleCaption(speaker, text) {
    if (!text || !text.trim()) return;
    const key = (speaker || "") + "|" + text;
    const last = seen.get(key) || 0;
    const t = Date.now();
    if (t - last < DEDUP_MS) return;
    seen.set(key, t);
    post({
      ts: nowIsoUtc(),
      text: text.trim(),
      speaker: speaker || null,
      meeting_code: MEETING_CODE,
      source: SOURCE,
    });
  }

  // Observe the captions region. Selector is illustrative only.
  function start() {
    const container = document.querySelector('[aria-live="polite"]');
    if (!container) {
      setTimeout(start, 1500);
      return;
    }
    const obs = new MutationObserver(() => {
      // Operator: walk container children, pull speaker + text per row.
      // Exact structure changes — inspect and adapt.
      const rows = container.querySelectorAll("div");
      rows.forEach((row) => {
        const speaker = row.querySelector("span")?.innerText || null;
        const text = row.innerText || "";
        handleCaption(speaker, text);
      });
    });
    obs.observe(container, { childList: true, subtree: true, characterData: true });
  }

  start();
})();
