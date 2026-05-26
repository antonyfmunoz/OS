---
name: browser-control
description: Use when a task requires web browser interaction without a direct API — Instagram, LinkedIn, Notion, or any web tool.
allowed-tools: Bash, Read
---

# Browser Control — Best Practices

## When to use
When a task requires web browser interaction without a direct API:
Manus, Instagram, LinkedIn, Notion, any web tool.

## The right pattern
Text output only — no screenshots.
Screenshots = 1000+ tokens each.
Text extraction = fast and cheap.

```python
from substrate.execution.agents.browser_agent import BrowserAgent, run_browser_task
import asyncio

async def run_task(task: str, url: str = '') -> str:
    agent = BrowserAgent(headless=True)
    await agent.start()
    if url:
        await agent.navigate(url)
    text = await agent.get_page_text()
    await agent.stop()
    return text  # text only, never screenshot

# Single-call convenience
result = asyncio.run(run_browser_task(
    url='https://example.com',
    task='extract the main content',
))
```

## Available classes
- `BrowserAgent` — full control, manual lifecycle
- `run_browser_task(url, task)` — single-call convenience

## Extraction methods (prefer these over screenshot)
- `agent.get_page_text()` — full text of current page
- `agent.extract_text()` — alias, returns BrowserResult with .output
- `agent.get_page_source()` — raw HTML when structure matters
- `agent.get_element_text(selector)` — targeted extraction

## NEVER
- `agent.screenshot()` inside automation loops
- Storing screenshots in memory pipelines
- Taking screenshots to "see" content — use text extraction

## Common patterns

### Check a page for information
```python
result = await run_browser_task(url='https://site.com', task='find X')
# result is str — pass directly to LLM or parse
```

### Fill a form
```python
agent = BrowserAgent(headless=True)
await agent.start()
await agent.navigate(url)
await agent.fill_form({'selector': 'value'})
await agent.click('button[type=submit]')
text = await agent.get_page_text()
await agent.stop()
```

### Login flow (avoid storing credentials in code)
```python
import os
agent = BrowserAgent(headless=True)
await agent.start()
await agent.navigate(login_url)
await agent.fill_form({
    '#email': os.getenv('SERVICE_EMAIL'),
    '#password': os.getenv('SERVICE_PASSWORD'),
})
await agent.click('button[type=submit]')
await agent.wait_for_navigation()
```
