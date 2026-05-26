"""
BrowserAgent — Playwright-based web operator for EOS agents.

Gives agents the ability to operate any website or web application.
Same pattern as gws_connector.py — a clean wrapper that agents call,
it executes in the browser, returns results.

Usage:
    from substrate.execution.agents.browser_agent import BrowserAgent, run_browser_task

    # Full control
    agent = BrowserAgent()
    await agent.start()
    await agent.navigate('https://notion.so')
    text = await agent.get_page_text()
    await agent.stop()

    # Single-call convenience
    result = await run_browser_task(
        url='https://notion.so',
        task='find the OS Dashboard page',
    )
"""

import json
import re

from pathlib import Path
from dotenv import load_dotenv

_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / 'services' / '.env')
load_dotenv(_ROOT / 'runtime' / '.env', override=True)


class BrowserAgent:

    def __init__(self, headless: bool = True) -> None:
        self.headless = headless
        self._browser = None
        self._context = None
        self._page = None
        self._pw = None

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    async def start(self) -> None:
        from playwright.async_api import async_playwright
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=self.headless,
            args=['--no-sandbox', '--disable-dev-shm-usage'],
        )
        self._context = await self._browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent=(
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
        )
        self._page = await self._context.new_page()

    async def stop(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()

    # ── Navigation ────────────────────────────────────────────────────────────

    async def navigate(self, url: str) -> str:
        """Navigate to URL. Returns final URL after redirects."""
        await self._page.goto(
            url,
            wait_until='domcontentloaded',
            timeout=30000,
        )
        return self._page.url

    # ── Content extraction ────────────────────────────────────────────────────

    async def get_text(
        self,
        selector: str = 'body',
        timeout: int = 5000,
    ) -> str:
        """Get inner text of a specific element. Returns '' on miss."""
        try:
            el = await self._page.wait_for_selector(
                selector, timeout=timeout)
            return await el.inner_text()
        except Exception:
            return ''

    async def get_page_text(self) -> str:
        """Get full visible text of the page body."""
        return await self._page.inner_text('body')

    async def get_all_inputs(self) -> list[dict]:
        """Return all input/textarea/select fields with their attributes."""
        inputs = await self._page.query_selector_all(
            'input, textarea, select')
        result = []
        for inp in inputs:
            result.append({
                'tag':         await inp.evaluate('el => el.tagName'),
                'name':        await inp.get_attribute('name') or '',
                'type':        await inp.get_attribute('type') or '',
                'placeholder': await inp.get_attribute('placeholder') or '',
                'id':          await inp.get_attribute('id') or '',
            })
        return result

    async def extract_table(self, selector: str = 'table') -> list[dict]:
        """Extract table data as a list of row dicts keyed by column headers."""
        try:
            return await self._page.evaluate(f'''
                () => {{
                    const table = document.querySelector('{selector}');
                    if (!table) return [];
                    const headers = [...table.querySelectorAll('th')]
                        .map(h => h.innerText.trim());
                    const rows = [...table.querySelectorAll('tr')].slice(1);
                    return rows.map(row => {{
                        const cells = [...row.querySelectorAll('td')]
                            .map(c => c.innerText.trim());
                        return Object.fromEntries(
                            headers.map((h, i) => [h, cells[i]]));
                    }});
                }}
            ''')
        except Exception:
            return []

    # ── Interaction ───────────────────────────────────────────────────────────

    async def click(
        self,
        selector: str,
        timeout: int = 5000,
    ) -> bool:
        """Click an element. Returns True on success, False on miss."""
        try:
            await self._page.click(selector, timeout=timeout)
            return True
        except Exception:
            return False

    async def type_into(
        self,
        selector: str,
        text: str,
        delay: int = 50,
        timeout: int = 5000,
    ) -> bool:
        """Click then type into a field. Returns True on success."""
        try:
            el = await self._page.wait_for_selector(
                selector, timeout=timeout)
            await el.click()
            await el.type(text, delay=delay)
            return True
        except Exception:
            return False

    async def select_option(
        self,
        selector: str,
        value: str,
    ) -> bool:
        """Select a dropdown option by value. Returns True on success."""
        try:
            await self._page.select_option(selector, value)
            return True
        except Exception:
            return False

    async def wait_for(
        self,
        selector: str,
        timeout: int = 10000,
    ) -> bool:
        """Wait for element to appear. Returns True when found."""
        try:
            await self._page.wait_for_selector(
                selector, timeout=timeout)
            return True
        except Exception:
            return False

    async def fill_form(
        self,
        fields: dict[str, str],
        submit_selector: str | None = None,
        delay: int = 50,
    ) -> dict:
        """
        Fill multiple form fields at once.
        fields: {selector: value}
        Returns {filled: int, failed: list[str]}
        """
        filled = 0
        failed = []
        for selector, value in fields.items():
            ok = await self.type_into(selector, value, delay)
            if ok:
                filled += 1
            else:
                failed.append(selector)
        if submit_selector and not failed:
            await self.click(submit_selector)
        return {'filled': filled, 'failed': failed}

    # ── Screenshot ────────────────────────────────────────────────────────────

    async def screenshot(self, path: str) -> bool:
        """Save screenshot to path. Returns True on success."""
        try:
            await self._page.screenshot(path=path)
            return True
        except Exception:
            return False

    # ── Page state extraction ─────────────────────────────────────────────────

    async def extract_page_state(self) -> dict:
        """
        Extract full structured state of the current page.
        Returns title, url, headings, links, inputs, and truncated body text.
        Used after every navigation — not screenshots.
        """
        url   = self._page.url
        title = await self._page.title()

        headings = await self._page.evaluate('''() => {
            return [...document.querySelectorAll("h1,h2,h3")]
                .map(h => h.innerText.trim())
                .filter(t => t.length > 0)
                .slice(0, 20);
        }''')

        links = await self._page.evaluate('''() => {
            return [...document.querySelectorAll("a[href]")]
                .map(a => ({text: a.innerText.trim(), href: a.href}))
                .filter(l => l.text.length > 0)
                .slice(0, 30);
        }''')

        inputs = await self.get_all_inputs()

        body_text = ''
        try:
            body_text = await self._page.inner_text('body')
        except Exception:
            pass

        return {
            'url':      url,
            'title':    title,
            'headings': headings,
            'links':    links,
            'inputs':   inputs,
            'body':     body_text[:3000],
        }

    # ── Agent reasoning ───────────────────────────────────────────────────────

    async def run_task(
        self,
        task_description: str,
        ctx=None,
    ) -> dict:
        """
        Higher-level: describe what to do, agent reasons about how.

        Uses AgentRuntime to plan steps, then executes each one.
        After every navigation, extracts full page state as structured text.
        Screenshots are taken only on exception/failure.

        Returns:
          {
            success:      bool,
            steps_taken:  list[str],      # human-readable action log
            page_states:  list[dict],     # structured extraction per navigation
            findings:     str,            # synthesized summary of what was found
            final_url:    str,
          }
        """
        from adapters.models.agent_runtime import AgentRuntime, TaskType

        if not ctx:
            from substrate.state.context.context import load_context_from_env
            ctx = load_context_from_env()

        # Capture initial page state to give the planner real context
        initial_state = await self.extract_page_state() if self._page else {}

        rt = AgentRuntime(ctx)
        plan = rt.run(
            task_type=TaskType.GENERATE,
            prompt=(
                f"You are controlling a web browser. Plan the steps to complete this task.\n\n"
                f"Current URL: {initial_state.get('url', 'none')}\n"
                f"Page title: {initial_state.get('title', '')}\n"
                f"Headings: {initial_state.get('headings', [])}\n"
                f"Available inputs: {initial_state.get('inputs', [])}\n"
                f"Body text (first 800 chars): "
                f"{initial_state.get('body', '')[:800]}\n\n"
                f"Task: {task_description}\n\n"
                f"Return a JSON list of steps. Valid actions:\n"
                f'  {{"action": "navigate", "target": "https://..."}}\n'
                f'  {{"action": "click",    "target": "css_selector"}}\n'
                f'  {{"action": "type",     "target": "css_selector", "value": "text"}}\n'
                f'  {{"action": "wait",     "target": "css_selector"}}\n'
                f'  {{"action": "extract_table", "target": "table"}}\n'
                f"Do NOT use screenshot — text extraction is automatic after navigate.\n"
                f"Return ONLY the JSON array."
            ),
            agent='operations_agent',
            max_tokens=600,
        )

        steps: list[dict] = []
        try:
            text  = plan.output or '[]'
            match = re.search(r'\[.*\]', text, re.DOTALL)
            if match:
                steps = json.loads(match.group(), strict=False)
        except Exception:
            pass

        action_log:  list[str]  = []
        page_states: list[dict] = [initial_state] if initial_state else []

        try:
            for step in steps:
                action = step.get('action', '')
                target = step.get('target', '')
                value  = step.get('value', '')

                if action == 'navigate':
                    final_url = await self.navigate(target)
                    state = await self.extract_page_state()
                    page_states.append(state)
                    action_log.append(
                        f"navigate → {final_url} | title: {state.get('title', '')} | "
                        f"headings: {state.get('headings', [])[:3]}"
                    )

                elif action == 'click':
                    ok = await self.click(target)
                    action_log.append(f"click '{target}': {'ok' if ok else 'missed'}")
                    if ok:
                        # Capture state after meaningful interactions
                        state = await self.extract_page_state()
                        page_states.append(state)

                elif action == 'type':
                    ok = await self.type_into(target, value)
                    action_log.append(
                        f"type into '{target}' ← '{value[:50]}': "
                        f"{'ok' if ok else 'missed'}"
                    )

                elif action == 'wait':
                    ok = await self.wait_for(target)
                    action_log.append(f"wait for '{target}': {'found' if ok else 'timeout'}")

                elif action == 'extract_table':
                    rows = await self.extract_table(target)
                    action_log.append(f"extract_table '{target}': {len(rows)} rows")
                    if rows:
                        page_states.append({'table': rows, 'url': self._page.url})

        except Exception as exc:
            # Screenshot only on failure
            shot_path = f'{_ROOT}/logs/browser_error_{len(action_log)}.png'
            await self.screenshot(shot_path)
            action_log.append(f"ERROR: {exc} — screenshot saved to {shot_path}")
            return {
                'success':     False,
                'steps_taken': action_log,
                'page_states': page_states,
                'findings':    f'Task failed at step {len(action_log)}: {exc}',
                'final_url':   self._page.url if self._page else '',
            }

        # Synthesize findings from all extracted page states
        findings = _synthesize_findings(task_description, page_states, action_log)

        return {
            'success':     len(action_log) > 0,
            'steps_taken': action_log,
            'page_states': page_states,
            'findings':    findings,
            'final_url':   self._page.url if self._page else '',
        }


# ── Findings synthesis ────────────────────────────────────────────────────────

def _synthesize_findings(
    task: str,
    page_states: list[dict],
    action_log: list[str],
) -> str:
    """
    Build a plain-text summary of what was found across all page states.
    No LLM call — deterministic, fast.
    """
    lines = [f"Task: {task}", ""]

    for i, state in enumerate(page_states):
        if 'table' in state:
            lines.append(f"Table data ({len(state['table'])} rows):")
            for row in state['table'][:10]:
                lines.append(f"  {row}")
            continue

        label = f"Page {i + 1}" if i > 0 else "Initial page"
        lines.append(f"{label}: {state.get('title', '')} — {state.get('url', '')}")
        if state.get('headings'):
            lines.append(f"  Headings: {', '.join(state['headings'][:5])}")
        if state.get('body'):
            lines.append(f"  Content: {state['body'][:400]}")
        lines.append("")

    lines.append("Steps taken:")
    for step in action_log:
        lines.append(f"  • {step}")

    return "\n".join(lines)


# ── Convenience function for agent calls ──────────────────────────────────────

async def run_browser_task(
    url: str,
    task: str,
    ctx=None,
) -> dict:
    """
    Single-call interface for agents. Handles start/stop automatically.

    Returns:
      {success, steps_taken, page_states, findings, final_url}
    """
    agent = BrowserAgent()
    try:
        await agent.start()
        await agent.navigate(url)
        result = await agent.run_task(task, ctx)
        return result
    finally:
        await agent.stop()


# ── Specialized browser agents ────────────────────────────────────────────────

class ManusAgent(BrowserAgent):
    """
    Access Manus via browser — no API key required.
    Routes tasks to manus.im and extracts results.
    When Meta opens a native API, migrate to model_router MANUS provider.
    """

    MANUS_URL = 'https://manus.im'

    async def submit_task(self, task: str) -> dict:
        """Navigate to Manus, submit a task, return findings."""
        await self.navigate(self.MANUS_URL)
        return await self.run_task(
            task_description=task,
        )


class InstagramAgent(BrowserAgent):
    """
    Control Instagram via browser for DM sending without the API.

    Requires INSTAGRAM_USERNAME + INSTAGRAM_PASSWORD in .env.
    Session is maintained across calls within the same agent instance.
    """

    INSTAGRAM_URL = 'https://www.instagram.com'
    DM_URL        = 'https://www.instagram.com/direct/new/'

    async def login(self) -> bool:
        """Log in using env credentials. Returns True on success."""
        import os
        username = os.getenv('INSTAGRAM_USERNAME', '')
        password = os.getenv('INSTAGRAM_PASSWORD', '')
        if not username or not password:
            print('[InstagramAgent] INSTAGRAM_USERNAME/PASSWORD not set')
            return False

        await self.navigate(self.INSTAGRAM_URL)
        import asyncio as _aio
        await _aio.sleep(2)
        ok = await self.fill_form(
            fields={
                'input[name="username"], input[name="email"]': username,
                'input[name="password"], input[name="pass"]': password,
            },
            submit_selector='button[type="submit"]',
        )
        if ok['failed']:
            print(f'[InstagramAgent] Login form fill failed: {ok["failed"]}')
            return False

        # Wait for home feed or challenge screen
        found = await self.wait_for('svg[aria-label="Home"]', timeout=15000)
        if not found:
            shot = f'{_ROOT}/logs/instagram_login_error.png'
            await self.screenshot(shot)
            print(f'[InstagramAgent] Login may have failed — screenshot: {shot}')
        return found

    async def send_dm(self, username: str, message: str) -> dict:
        """
        Send a DM to @username.
        Navigates to the direct compose screen and types the message.
        """
        print(f'[InstagramAgent] Sending DM to @{username}')
        return await self.run_task(
            task_description=(
                f'Send this DM to @{username}: {message}. '
                f'Find the recipient field, type their username, '
                f'select them from the dropdown, type the message, '
                f'and send it.'
            ),
        )


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(
        description='Run a browser task using Playwright.',
    )
    parser.add_argument('--url',  required=True, help='URL to navigate to')
    parser.add_argument('--task', required=True, help='Task description')
    args = parser.parse_args()

    async def _main() -> None:
        result = await run_browser_task(url=args.url, task=args.task)
        print("\n─── Browser Task Result ───────────────────────────────")
        print(result['findings'])
        print("\n─── Steps taken ───────────────────────────────────────")
        for step in result['steps_taken']:
            print(f"  • {step}")
        print(f"\nFinal URL: {result['final_url']}")
        print(f"Success:   {result['success']}")

    asyncio.run(_main())
