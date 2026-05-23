"""
ScraplingConnector — stealth HTTP fetching for EOS agents.

Wraps Scrapling's Fetcher and StealthyFetcher to give agents
clean, structured access to any public web page without triggering
bot detection. Used by reality_engine and research_engine for
competitor monitoring, trend research, and market intelligence.

Usage:
    from adapters.scrapling.scrapling_connector import ScraplingConnector
    sc = ScraplingConnector()

    page = sc.fetch('https://hamza.social')
    # page = {url, title, text, links, status}

    results = sc.search_and_fetch('discipline programs for men 2025', num_results=5)
    # results = [page, page, ...]

    delta = sc.monitor_competitor('https://hamza.social', last_content=cached_text)
    # delta = {url, changed, new_content, status}
"""

import urllib.parse


class ScraplingConnector:
    """
    Stealth web fetcher using Scrapling under the hood.

    StealthyFetcher (default) — uses Playwright with stealth patches.
    Fetcher (fallback) — curl_cffi based, lighter, less stealth.
    """

    def fetch(self, url: str, stealth: bool = True) -> dict:
        """
        Fetch a URL and return structured page data.

        Args:
            url:    Target URL.
            stealth: Use StealthyFetcher (default). Set False for lighter Fetcher.

        Returns:
            {url, title, text, links, status}
        """
        try:
            if stealth:
                from scrapling import StealthyFetcher

                page = StealthyFetcher().fetch(url)
            else:
                from scrapling import Fetcher

                page = Fetcher().get(url)

            title_el = page.find("title")
            title = title_el.text if title_el else ""

            text = page.get_all_text()

            links = [
                a.attrib.get("href", "")
                for a in page.find_all("a")
                if a.attrib.get("href", "").startswith("http")
            ][:20]

            return {
                "url": url,
                "title": title,
                "text": text[:5000],
                "links": links,
                "status": "ok",
            }

        except Exception as e:
            return {
                "url": url,
                "title": "",
                "text": "",
                "links": [],
                "status": f"error: {e}",
            }

    def search_and_fetch(
        self,
        query: str,
        num_results: int = 5,
    ) -> list[dict]:
        """
        Search Google and fetch the top organic results.

        Args:
            query:       Search query string.
            num_results: Max pages to fetch (default 5).

        Returns:
            List of page dicts from fetch().
        """
        search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"

        search_page = self.fetch(search_url)

        # Extract non-Google result links
        result_links = [
            l for l in search_page.get("links", []) if "google" not in l and l.startswith("http")
        ][:num_results]

        results = []
        for link in result_links:
            page = self.fetch(link)
            if page.get("status") == "ok":
                results.append(page)

        return results

    def monitor_competitor(
        self,
        url: str,
        last_content: str = "",
    ) -> dict:
        """
        Fetch a competitor page and detect content changes.

        Args:
            url:          Competitor URL to monitor.
            last_content: Previously stored text to diff against.
                          Pass '' on first run to establish baseline.

        Returns:
            {url, changed, new_content, status}
        """
        page = self.fetch(url)
        new_content = page.get("text", "")
        changed = last_content != "" and new_content != last_content

        return {
            "url": url,
            "changed": changed,
            "new_content": new_content,
            "title": page.get("title", ""),
            "status": page.get("status"),
        }
