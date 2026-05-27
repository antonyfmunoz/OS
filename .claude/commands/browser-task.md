Run a browser task using Playwright.

Usage:
  python3 -c "from substrate import run_browser_task" --url [url] --task "[task description]"

The script will:
1. Launch headless Chromium
2. Navigate to URL
3. Extract initial page state (title, headings, inputs, body text)
4. Plan and execute steps using AgentRuntime
5. After each navigation, extract full structured page state
6. Print structured text output — findings, steps taken, final URL
7. Close browser

Screenshots are taken only on exception or failure.
Read the text output directly — no image files needed.

Example:
  python3 -c "from substrate import run_browser_task" \
    --url https://news.ycombinator.com \
    --task "find the top 5 story titles"

Return shape (from run_browser_task()):
  {
    success:     bool,
    steps_taken: list[str],   # human-readable action log
    page_states: list[dict],  # structured extraction per navigation
    findings:    str,         # synthesized plain-text summary
    final_url:   str,
  }

Use from Python:
  import asyncio
  from substrate import run_browser_task
  result = asyncio.run(run_browser_task(url="...", task="..."))
  print(result["findings"])
