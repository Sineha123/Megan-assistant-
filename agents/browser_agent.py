"""
Browser Agent - Handles all web browsing tasks
Uses Playwright for automation; connects to an existing Chrome instance
launched with --remote-debugging-port=9222
"""

import asyncio
from typing import Dict, Optional, List
from enum import Enum


class BrowserAction(Enum):
    """Available browser actions"""
    SEARCH        = "search"
    NAVIGATE      = "navigate"
    CLICK         = "click"
    TYPE          = "type"
    SCROLL        = "scroll"
    EXTRACT_TEXT  = "extract_text"
    FILL_FORM     = "fill_form"
    TAKE_SCREENSHOT = "screenshot"
    GET_TITLE     = "get_title"
    GET_URL       = "get_url"


class BrowserAgent:
    """
    Browser Agent - Controls web browser for automation.

    Capabilities:
    - Search on Google/other search engines
    - Navigate to URLs
    - Click elements
    - Extract data from websites
    - Fill forms
    - Take screenshots

    Requirements:
    - Existing Chrome/Chromium instance running with --remote-debugging-port=9222
    - playwright package installed
    """

    def __init__(self):
        self.browser     = None
        self.context     = None
        self.page        = None
        self.is_connected = False

    # ─── Connection ──────────────────────────────────────────────────────────

    async def connect_to_browser(self, browser_port: int = 9222) -> bool:
        """
        Connect to existing Chrome/Chromium instance.

        Args:
            browser_port: Port where Chrome is running

        Returns:
            True if connected successfully
        """
        try:
            from playwright.async_api import async_playwright

            print(f"[BROWSER] Attempting to connect on port {browser_port}...")

            # Note: We store the playwright context manager reference
            self._playwright_ctx = async_playwright()
            p = await self._playwright_ctx.__aenter__()
            self._playwright = p

            self.browser = await p.chromium.connect_over_cdp(
                f"http://localhost:{browser_port}"
            )

            contexts = self.browser.contexts
            if contexts:
                self.context = contexts[0]
                pages = self.context.pages
                if pages:
                    self.page = pages[0]
                    self.is_connected = True
                    print(f"[BROWSER] OK: Connected! URL: {self.page.url}")
                    return True

            print("[BROWSER] WARN:  No active browser context found")
            return False

        except ImportError:
            print("[BROWSER] WARN:  playwright not installed -- browser agent disabled")
            return False
        except Exception as e:
            print(f"[ERROR] Failed to connect to browser: {str(e)}")
            return False

    # ─── Actions ─────────────────────────────────────────────────────────────

    async def search(self, query: str, search_engine: str = "google") -> Dict:
        """Search on the specified search engine."""
        try:
            if not self.page:
                return {"error": "Browser not connected"}

            print(f"[BROWSER] Searching: {query}")

            search_urls = {
                "google":    "https://www.google.com",
                "bing":      "https://www.bing.com",
                "duckduckgo": "https://www.duckduckgo.com",
            }
            url = search_urls.get(search_engine, search_urls["google"])

            await self.page.goto(url)

            search_box = (
                await self.page.query_selector('input[name="q"]') or
                await self.page.query_selector('[type="search"]')
            )

            if search_box:
                await search_box.fill(query)
                await search_box.press("Enter")
                await self.page.wait_for_load_state("load")
                return {
                    "status": "success",
                    "query":  query,
                    "url":    self.page.url,
                    "title":  await self.page.title(),
                }

            return {"error": "Could not find search box"}

        except Exception as e:
            print(f"[ERROR] Search failed: {str(e)}")
            return {"error": str(e)}

    async def navigate(self, url: str) -> Dict:
        """Navigate to a URL."""
        try:
            if not self.page:
                return {"error": "Browser not connected"}
            print(f"[BROWSER] Navigating to: {url}")
            await self.page.goto(url)
            await self.page.wait_for_load_state("load")
            return {"status": "success", "url": self.page.url, "title": await self.page.title()}

        except Exception as e:
            print(f"[ERROR] Navigation failed: {str(e)}")
            return {"error": str(e)}

    async def extract_text(self, selector: Optional[str] = None) -> Dict:
        """Extract text from page or a specific element."""
        try:
            if not self.page:
                return {"error": "Browser not connected"}
            print("[BROWSER] Extracting text...")

            if selector:
                element = await self.page.query_selector(selector)
                text = (await element.text_content()) if element else "Element not found"
            else:
                text = await self.page.inner_text("body")

            return {"status": "success", "text": text, "url": self.page.url}

        except Exception as e:
            print(f"[ERROR] Text extraction failed: {str(e)}")
            return {"error": str(e)}

    async def click(self, selector: str) -> Dict:
        """Click on a page element."""
        try:
            if not self.page:
                return {"error": "Browser not connected"}
            print(f"[BROWSER] Clicking: {selector}")
            await self.page.click(selector)
            await self.page.wait_for_load_state("load")
            return {"status": "success", "action": "clicked", "url": self.page.url}

        except Exception as e:
            print(f"[ERROR] Click failed: {str(e)}")
            return {"error": str(e)}

    async def fill_form(self, form_data: Dict) -> Dict:
        """Fill form fields. form_data = {selector: value, ...}"""
        try:
            if not self.page:
                return {"error": "Browser not connected"}
            print(f"[BROWSER] Filling {len(form_data)} form fields...")
            for selector, value in form_data.items():
                await self.page.fill(selector, str(value))
            return {"status": "success", "fields_filled": len(form_data)}

        except Exception as e:
            print(f"[ERROR] Form fill failed: {str(e)}")
            return {"error": str(e)}

    async def take_screenshot(self, output_path: str = "screenshot.png") -> Dict:
        """Take screenshot of the current page."""
        try:
            if not self.page:
                return {"error": "Browser not connected"}
            print("[BROWSER] Taking screenshot...")
            await self.page.screenshot(path=output_path)
            return {"status": "success", "path": output_path, "url": self.page.url}

        except Exception as e:
            print(f"[ERROR] Screenshot failed: {str(e)}")
            return {"error": str(e)}

    async def get_page_info(self) -> Dict:
        """Return current page title and URL."""
        try:
            if not self.page:
                return {"error": "Browser not connected"}
            return {
                "title":        await self.page.title(),
                "url":          self.page.url,
                "is_connected": self.is_connected,
            }
        except Exception as e:
            return {"error": str(e)}

    async def close(self):
        """Close the browser connection."""
        if self.browser:
            await self.browser.close()
            self.is_connected = False
            print("[BROWSER] Browser connection closed")
        if hasattr(self, "_playwright_ctx"):
            await self._playwright_ctx.__aexit__(None, None, None)


# ─── Standalone Test ──────────────────────────────────────────────────────────

async def _test():
    agent = BrowserAgent()
    if await agent.connect_to_browser():
        result = await agent.search("weather in hyderabad")
        print(f"Search result: {result}")
        await agent.close()
    else:
        print("Could not connect. Launch Chrome with --remote-debugging-port=9222")

if __name__ == "__main__":
    print("""
    Browser Agent -- Setup:
    Windows: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222
    macOS:   open -a "Google Chrome" --args --remote-debugging-port=9222
    Linux:   google-chrome --remote-debugging-port=9222
    """)
    asyncio.run(_test())
