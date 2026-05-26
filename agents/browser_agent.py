"""
Browser Agent - Handles all web browsing tasks
Uses Playwright for automation; auto-launches Chrome if not running.

Supported tasks:
  search         - Google / Bing / YouTube search
  navigate       - Go to any URL
  play_song      - Play a song on YouTube
  youtube_search - Search YouTube
  click          - Click a CSS selector
  extract_text   - Pull text from page / selector
  fill_form      - Fill form fields
  screenshot     - Take a screenshot
  page_info      - Return current title + URL
  close_tab      - Close current tab
  new_tab        - Open a new tab
  go_back        - Browser back
  go_forward     - Browser forward
  scroll         - Scroll page up/down
  check_info     - Navigate and extract a quick answer (weather, news, etc.)
"""

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional
from enum import Enum


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _find_chrome() -> Optional[str]:
    """Return path to Chrome/Chromium executable on Windows, macOS, or Linux.
    Checks system Chrome first, then falls back to Playwright's bundled Chromium.
    """
    candidates = [
        # Windows - Google Chrome
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        # macOS
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        # Linux
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path

    # Fallback: use Playwright's bundled Chromium
    try:
        from playwright.sync_api import sync_playwright
        p = sync_playwright().start()
        exe = p.chromium.executable_path
        p.stop()
        if exe and os.path.isfile(exe):
            print(f"[BROWSER] Using Playwright Chromium: {exe}")
            return exe
    except Exception:
        pass

    return None


async def _wait_for_cdp(port: int, timeout: float = 10.0) -> bool:
    """Poll the CDP endpoint until Chrome is ready."""
    import urllib.request
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(f"http://localhost:{port}/json/version", timeout=1)
            return True
        except Exception:
            await asyncio.sleep(0.4)
    return False


# ──────────────────────────────────────────────────────────────────────────────
# BrowserAgent
# ──────────────────────────────────────────────────────────────────────────────

class BrowserAgent:
    """
    Controls a Chrome/Chromium browser via Playwright CDP.

    On first use, if Chrome is not already running with --remote-debugging-port
    it will be auto-launched.
    """

    def __init__(self, browser_port: int = 9222):
        self.browser_port  = browser_port
        self.browser       = None
        self.context       = None
        self.page          = None
        self.is_connected  = False
        self._playwright   = None
        self._pw_ctx       = None
        self._chrome_proc  = None   # subprocess handle if we launched Chrome

    # ── Connection ────────────────────────────────────────────────────────────

    async def ensure_connected(self) -> bool:
        """Connect (or reconnect) to browser, launching Chrome if necessary."""
        if self.is_connected and self.page:
            return True
        return await self._connect_or_launch()

    async def _connect_or_launch(self) -> bool:
        """Try CDP connect; if it fails, auto-launch Chrome then retry."""
        if await self._try_connect():
            return True

        print("[BROWSER] Chrome not found on CDP port — attempting auto-launch...")
        if not self._launch_chrome():
            return False

        # Give Chrome time to start and settle
        ready = await _wait_for_cdp(self.browser_port, timeout=12)
        if not ready:
            print("[BROWSER] ERROR: Chrome did not become ready in time")
            return False

        # Extra stabilization pause — lets Chrome finish opening default tabs
        await asyncio.sleep(2.0)

        return await self._try_connect()

    async def _try_connect(self) -> bool:
        try:
            from playwright.async_api import async_playwright

            # Close any old playwright instance
            if self._pw_ctx:
                try:
                    await self._pw_ctx.__aexit__(None, None, None)
                except Exception:
                    pass

            self._pw_ctx = async_playwright()
            p = await self._pw_ctx.__aenter__()
            self._playwright = p

            self.browser = await p.chromium.connect_over_cdp(
                f"http://localhost:{self.browser_port}"
            )

            contexts = self.browser.contexts
            if contexts:
                self.context = contexts[0]
                pages = self.context.pages
                if pages:
                    self.page = pages[0]
                else:
                    self.page = await self.context.new_page()
            else:
                self.context = await self.browser.new_context()
                self.page = await self.context.new_page()

            self.is_connected = True
            print(f"[BROWSER] Connected! URL: {self.page.url}")
            return True

        except ImportError:
            print("[BROWSER] ERROR: playwright not installed — run: pip install playwright && playwright install chromium")
            return False
        except Exception as e:
            print(f"[BROWSER] Could not connect via CDP: {e}")
            self.is_connected = False
            return False

    def _launch_chrome(self) -> bool:
        chrome_path = _find_chrome()
        if not chrome_path:
            print("[BROWSER] ERROR: Google Chrome not found on this system")
            return False

        user_data = str(Path.home() / ".megan_chrome_profile")
        cmd = [
            chrome_path,
            f"--remote-debugging-port={self.browser_port}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-default-apps",
            f"--user-data-dir={user_data}",
            "about:blank",
        ]
        try:
            self._chrome_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print(f"[BROWSER] Chrome launched (PID {self._chrome_proc.pid})")
            return True
        except Exception as e:
            print(f"[BROWSER] ERROR launching Chrome: {e}")
            return False

    # ── Core Navigation ───────────────────────────────────────────────────────

    async def navigate(self, url: str, retries: int = 2) -> Dict:
        """Navigate to any URL (with automatic retry on navigation interruption)."""
        if not await self.ensure_connected():
            return {"error": "Browser not available"}
        try:
            # Prepend https:// if no scheme
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            print(f"[BROWSER] Navigating to: {url}")

            last_error = None
            for attempt in range(retries + 1):
                try:
                    await self.page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    title = await self.page.title()
                    return {"status": "success", "url": self.page.url, "title": title}
                except Exception as e:
                    last_error = e
                    err_str = str(e)
                    # If interrupted by another navigation, wait and retry
                    if "interrupted by another navigation" in err_str or "ERR_CONNECTION_RESET" in err_str:
                        if attempt < retries:
                            print(f"[BROWSER] Navigation interrupted, retrying ({attempt+1}/{retries})...")
                            await asyncio.sleep(1.5)
                            continue
                    raise

            return {"error": str(last_error)}
        except Exception as e:
            print(f"[BROWSER] navigate error: {e}")
            return {"error": str(e)}


    async def go_back(self) -> Dict:
        if not await self.ensure_connected():
            return {"error": "Browser not available"}
        try:
            await self.page.go_back(wait_until="domcontentloaded", timeout=10000)
            return {"status": "success", "url": self.page.url}
        except Exception as e:
            return {"error": str(e)}

    async def go_forward(self) -> Dict:
        if not await self.ensure_connected():
            return {"error": "Browser not available"}
        try:
            await self.page.go_forward(wait_until="domcontentloaded", timeout=10000)
            return {"status": "success", "url": self.page.url}
        except Exception as e:
            return {"error": str(e)}

    async def new_tab(self, url: str = "about:blank") -> Dict:
        if not await self.ensure_connected():
            return {"error": "Browser not available"}
        try:
            self.page = await self.context.new_page()
            if url and url != "about:blank":
                await self.page.goto(url, wait_until="domcontentloaded", timeout=20000)
            return {"status": "success", "url": self.page.url}
        except Exception as e:
            return {"error": str(e)}

    async def close_tab(self) -> Dict:
        if not await self.ensure_connected():
            return {"error": "Browser not available"}
        try:
            await self.page.close()
            # Switch to another open page if available
            pages = self.context.pages
            self.page = pages[-1] if pages else await self.context.new_page()
            return {"status": "success", "url": self.page.url}
        except Exception as e:
            return {"error": str(e)}

    # ── Search ────────────────────────────────────────────────────────────────

    async def search(self, query: str, search_engine: str = "google") -> Dict:
        """Search on Google, Bing, DuckDuckGo, or YouTube."""
        search_urls = {
            "google":     f"https://www.google.com/search?q={_urlencode(query)}",
            "bing":       f"https://www.bing.com/search?q={_urlencode(query)}",
            "duckduckgo": f"https://duckduckgo.com/?q={_urlencode(query)}",
            "youtube":    f"https://www.youtube.com/results?search_query={_urlencode(query)}",
        }
        url = search_urls.get(search_engine.lower(), search_urls["google"])
        print(f"[BROWSER] Searching [{search_engine}]: {query}")
        result = await self.navigate(url)
        result["query"] = query
        result["engine"] = search_engine
        return result

    async def youtube_search(self, query: str) -> Dict:
        """Search YouTube for a video/song."""
        return await self.search(query, search_engine="youtube")

    async def play_song(self, song_name: str, artist: str = "") -> Dict:
        """Open YouTube and play the best match for a song."""
        q = f"{song_name} {artist}".strip() + " official audio"
        print(f"[BROWSER] Playing song: {q}")
        result = await self.navigate(
            f"https://www.youtube.com/results?search_query={_urlencode(q)}"
        )
        if result.get("status") == "success":
            # Try to click the first video result (YouTube needs JS to load)
            clicked = False
            selectors_to_try = [
                "ytd-video-renderer a#thumbnail",
                "ytd-video-renderer #video-title",
                "a#video-title",
                ".ytd-video-renderer a[href*='/watch']",
                "a[href*='watch?v=']",
            ]
            for sel in selectors_to_try:
                try:
                    await self.page.wait_for_selector(sel, timeout=6000)
                    await self.page.click(sel)
                    await asyncio.sleep(2)
                    title = await self.page.title()
                    result["video_title"] = title
                    result["action"] = "playing"
                    clicked = True
                    break
                except Exception:
                    continue

            if not clicked:
                # YouTube search is open — that's still useful
                result["action"] = "search_open"
                result["note"] = f"YouTube search open for '{song_name}'. Click the first result to play."
        return result

    # ── Interaction ───────────────────────────────────────────────────────────

    async def click(self, selector: str) -> Dict:
        if not await self.ensure_connected():
            return {"error": "Browser not available"}
        try:
            print(f"[BROWSER] Clicking: {selector}")
            await self.page.click(selector, timeout=8000)
            await asyncio.sleep(0.5)
            return {"status": "success", "clicked": selector, "url": self.page.url}
        except Exception as e:
            print(f"[BROWSER] click error: {e}")
            return {"error": str(e)}

    async def scroll(self, direction: str = "down", amount: int = 500) -> Dict:
        if not await self.ensure_connected():
            return {"error": "Browser not available"}
        try:
            delta = amount if direction == "down" else -amount
            await self.page.evaluate(f"window.scrollBy(0, {delta})")
            return {"status": "success", "direction": direction, "amount": amount}
        except Exception as e:
            return {"error": str(e)}

    async def fill_form(self, form_data: Dict) -> Dict:
        """Fill form fields. form_data = {selector: value, ...}"""
        if not await self.ensure_connected():
            return {"error": "Browser not available"}
        try:
            print(f"[BROWSER] Filling {len(form_data)} form fields")
            for selector, value in form_data.items():
                await self.page.fill(selector, str(value))
            return {"status": "success", "fields_filled": len(form_data)}
        except Exception as e:
            print(f"[BROWSER] fill_form error: {e}")
            return {"error": str(e)}

    async def type_text(self, text: str, selector: Optional[str] = None) -> Dict:
        """Type text into focused element or a specific selector."""
        if not await self.ensure_connected():
            return {"error": "Browser not available"}
        try:
            if selector:
                await self.page.click(selector)
            await self.page.keyboard.type(text)
            return {"status": "success", "typed": text}
        except Exception as e:
            return {"error": str(e)}

    # ── Extraction ────────────────────────────────────────────────────────────

    async def extract_text(self, selector: Optional[str] = None, max_chars: int = 2000) -> Dict:
        """Extract text from the page or a specific element."""
        if not await self.ensure_connected():
            return {"error": "Browser not available"}
        try:
            print("[BROWSER] Extracting text...")
            if selector:
                el = await self.page.query_selector(selector)
                text = (await el.text_content()) if el else "Element not found"
            else:
                text = await self.page.inner_text("body")
            text = text.strip()[:max_chars]
            return {"status": "success", "text": text, "url": self.page.url}
        except Exception as e:
            print(f"[BROWSER] extract_text error: {e}")
            return {"error": str(e)}

    async def check_info(self, query: str) -> Dict:
        """
        Quick-info lookup: search Google and extract a snippet from the results page.
        Good for weather, news headlines, sports scores, etc.
        """
        result = await self.search(query, search_engine="google")
        if result.get("error"):
            return result
        try:
            await asyncio.sleep(1)
            # Try to grab featured snippet or first result text
            snippet = None
            for sel in [
                "[data-attrid='wa:/description'] span",
                ".hgKElc",          # featured snippet short answer
                ".BNeawe.s3v9rd",   # answer box
                ".BNeawe.tAd8D",
                "div.g .VwiC3b",    # regular result snippet
            ]:
                el = await self.page.query_selector(sel)
                if el:
                    snippet = (await el.text_content()).strip()
                    if snippet:
                        break
            title = await self.page.title()
            return {
                "status":  "success",
                "query":   query,
                "title":   title,
                "snippet": snippet or "Could not extract a snippet — try navigating to the result page",
                "url":     self.page.url,
            }
        except Exception as e:
            return {"error": str(e)}

    async def get_page_info(self) -> Dict:
        """Return current page title and URL."""
        if not await self.ensure_connected():
            return {"error": "Browser not available"}
        try:
            title = await self.page.title()
            return {
                "status":       "success",
                "title":        title,
                "url":          self.page.url,
                "is_connected": self.is_connected,
            }
        except Exception as e:
            # Execution context may be destroyed — try to grab another page
            try:
                pages = self.context.pages if self.context else []
                if pages:
                    self.page = pages[-1]
                    return {
                        "status":       "success",
                        "title":        await self.page.title(),
                        "url":          self.page.url,
                        "is_connected": self.is_connected,
                    }
            except Exception:
                pass
            return {"error": str(e)}

    # ── Screenshot ────────────────────────────────────────────────────────────

    async def take_screenshot(self, output_path: str = "screenshot.png") -> Dict:
        if not await self.ensure_connected():
            return {"error": "Browser not available"}
        try:
            print(f"[BROWSER] Screenshot -> {output_path}")
            await self.page.screenshot(path=output_path, full_page=False)
            return {"status": "success", "path": output_path, "url": self.page.url}
        except Exception as e:
            print(f"[BROWSER] screenshot error: {e}")
            return {"error": str(e)}

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def close(self):
        """Disconnect from the browser (does NOT kill Chrome)."""
        if self.browser:
            try:
                await self.browser.close()
            except Exception:
                pass
        self.is_connected = False
        if self._pw_ctx:
            try:
                await self._pw_ctx.__aexit__(None, None, None)
            except Exception:
                pass
        print("[BROWSER] Browser connection closed")


# ──────────────────────────────────────────────────────────────────────────────
# Utilities
# ──────────────────────────────────────────────────────────────────────────────

def _urlencode(text: str) -> str:
    from urllib.parse import quote_plus
    return quote_plus(text)


# ──────────────────────────────────────────────────────────────────────────────
# Standalone test
# ──────────────────────────────────────────────────────────────────────────────

async def _test():
    agent = BrowserAgent()

    print("\n── Test 1: Google search ──")
    print(await agent.search("weather in Hyderabad today"))

    print("\n── Test 2: Navigate to website ──")
    print(await agent.navigate("https://www.bbc.com"))

    print("\n── Test 3: Quick info check ──")
    print(await agent.check_info("India cricket score today"))

    print("\n── Test 4: Play a song ──")
    print(await agent.play_song("Tum Hi Ho", "Arijit Singh"))

    await agent.close()


if __name__ == "__main__":
    asyncio.run(_test())
