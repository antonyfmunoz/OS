"""Empyrean Studios — canonical brand tokens.

THE single source for every client-facing surface (reports, web, email).
Established Build Sprint 002 per AFM ruling 2026-08-09: near-black /
near-white, ONE royal-violet accent, Archivo bold headlines, Inter body.
The Drive doc "EMPYREAN — Strategy — Agency Brand Identity [MASTER]" was
checked 2026-08-10 and contains no visual tokens — this file governs.

Never use Lyfe Spectrum gold (#c9a84c) on an Empyrean surface.
"""
from __future__ import annotations

WORDMARK = "EMPYREAN STUDIOS"
LEGAL_ENTITY = "Empyrean Creative LLC dba Empyrean Studios"

COLORS = {
    "bg": "#0A0A0B",           # near-black page ground
    "surface": "#121214",       # card / section background
    "border": "#1F1F23",        # 1px structural borders
    "text": "#F5F5F4",          # near-white primary text
    "muted": "#8E8E93",         # secondary text
    "accent": "#6D28D9",        # royal violet — THE one accent
    "accent_soft": "#8B5CF6",   # violet for fills/bars on dark
    "ok": "#22C55E",            # verdict PASS
    "warn": "#EAB308",          # verdict PRO-RATE
    "fail": "#EF4444",          # verdict FAIL / NOT ELIGIBLE
}

FONTS = {
    "headline": "Archivo, Inter, system-ui, sans-serif",
    "body": "Inter, system-ui, sans-serif",
}

# Shared CSS injected into every rendered surface. Self-contained: no CDN.
BASE_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  background: %(bg)s; color: %(text)s;
  font-family: %(body)s; line-height: 1.55;
  -webkit-font-smoothing: antialiased;
}
.page { max-width: 800px; margin: 0 auto; padding: 48px 28px; }
.wordmark {
  font-family: %(headline)s; font-weight: 700; font-size: 13px;
  letter-spacing: 0.3em; color: %(text)s; text-transform: uppercase;
}
h1, h2, h3 { font-family: %(headline)s; font-weight: 700; }
h1 { font-size: 30px; line-height: 1.15; margin: 18px 0 6px; }
h2 { font-size: 19px; margin: 34px 0 12px; }
.muted { color: %(muted)s; }
.accent { color: %(accent)s; }
.rule { height: 2px; background: %(accent)s; width: 56px; margin: 18px 0; border: 0; }
.card {
  background: %(surface)s; border: 1px solid %(border)s;
  border-radius: 6px; padding: 20px 22px; margin: 12px 0;
}
.big-number {
  font-family: %(headline)s; font-weight: 700; font-size: 44px;
  color: %(accent_soft)s; letter-spacing: -0.01em;
}
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }
table { width: 100%%; border-collapse: collapse; margin: 10px 0; }
th, td { text-align: left; padding: 9px 12px; border-bottom: 1px solid %(border)s; font-size: 14px; }
th { color: %(muted)s; font-weight: 600; text-transform: uppercase; font-size: 11px; letter-spacing: 0.08em; }
.verdict { display: inline-block; font-family: %(headline)s; font-weight: 700;
  padding: 4px 14px; border-radius: 4px; font-size: 14px; letter-spacing: 0.05em; }
.verdict.pass { background: rgba(34,197,94,.12); color: %(ok)s; border: 1px solid %(ok)s; }
.verdict.prorate { background: rgba(234,179,8,.12); color: %(warn)s; border: 1px solid %(warn)s; }
.verdict.fail { background: rgba(239,68,68,.12); color: %(fail)s; border: 1px solid %(fail)s; }
.bar { background: %(border)s; border-radius: 3px; height: 8px; overflow: hidden; }
.bar > span { display: block; height: 100%%; background: %(accent_soft)s; }
.cta {
  display: inline-block; background: %(accent)s; color: %(text)s;
  font-family: %(headline)s; font-weight: 700; font-size: 15px;
  padding: 13px 30px; border-radius: 6px; text-decoration: none; border: 0;
}
.footnote { font-size: 12px; color: %(muted)s; margin-top: 26px;
  border-top: 1px solid %(border)s; padding-top: 14px; }
@media print {
  body { background: #ffffff; color: #111113; }
  .card { background: #fafafa; border-color: #e4e4e7; }
  .wordmark, h1, h2, h3 { color: #111113; }
  .cta { display: none; }
}
""" % {**COLORS, **FONTS}


def page_shell(title: str, body_html: str, subtitle: str = "") -> str:
    """Wrap content in the branded page shell. Every surface renders through this."""
    sub = '<div class="muted" style="font-size:14px">%s</div>' % subtitle if subtitle else ""
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>%s</title><style>%s</style></head><body>"
        "<div class='page'><div class='wordmark'>%s</div>"
        "<h1>%s</h1>%s<hr class='rule'>%s</div></body></html>"
    ) % (title, BASE_CSS, WORDMARK, title, sub, body_html)
