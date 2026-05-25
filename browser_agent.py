"""
Browser Agent - Handles all web browsing tasks
Uses Playwright for automation
"""

import asyncio
from typing import Dict, Optional, List
from enum import Enum

class BrowserAction(Enum):
    """Available browser actions"""
    SEARCH = "search"
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    SCROLL = "scroll"
    EXTRACT_TEXT = "extract_text"
    FILL_FORM = "fill_form"
    TAKE_SCREENSHOT = "screenshot"
    GET_TITLE = "get_title"
    GET_URL = "get_url"


class BrowserAgent:
    """
    Browser Agent - Controls web browser for automation
    
    Capabilities:
    - Search on Google/other search engines
    - Navigate to URLs
    - Click elements
    - Extract data from websites
    - Fill forms
    - Take screenshots
    
    Requirements:
    - Existing Chrome/Chromium instance
    - Playwright library
    """
    
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.is_connected = False
    
    async def connect_to_browser(self, browser_port: int = 9222) -> bool:
        """
        Connect to existing Chrome/Chromium instance
        
        Args:
            browser_port: Port where Chrome is running
        
        Returns:
            True if connected successfully
        """
        try:
            from playwright.async_api import async_playwright
            
            print(f"[BROWSER] Attempting to connect to browser on port {browser_port}...")
            
            async with async_playwright() as p:
                # Connect to existing browser
                # Note: Chrome must be started with --remote-debugging-port=9222
                self.browser = await p.chromium.connect_over_cdp(
                    f"http://localhost:{browser_port}"
                )
                
                # Get first context/page
                contexts = self.browser.contexts
                if contexts:
                    self.context = contexts[0]
                    pages = self.context.pages
                    if pages:
                        self.page = pages[0]
                        self.is_connected = True
                        print(f"[BROWSER] Connected! Current URL: {self.page.url}")
                        return True
                
                print("[BROWSER] No active browser context found")
                return False
        
        except Exception as e:
            print(f"[ERROR] Failed to connect to browser: {str(e)}")
            return False
    
    async def search(self, query: str, search_engine: str = "google") -> Dict:
        """
        Search on specified search engine
        
        Args:
            query: Search query
            search_engine: 'google', 'bing', etc.
        
        Returns:
            Dictionary with search results
        """
        try:
            if not self.page:
                return {"error": "Browser not connected"}
            
            print(f"[BROWSER] Searching for: {query}")
            
            # Navigate to search engine
            search_urls = {
                "google": "https://www.google.com",
                "bing": "https://www.bing.com",
                "duckduckgo": "https://www.duckduckgo.com"
            }
            
            url = search_urls.get(search_engine, search_urls["google"])
            await self.page.goto(url)
            
            # Find and fill search box
            search_box = await self.page.query_selector('input[name="q"]') or \
                        await self.page.query_selector('[type="search"]')
            
            if search_box:
                await search_box.fill(query)
                await search_box.press("Enter")
                
                # Wait for results
                await self.page.wait_for_load_state("load")
                
                print(f"[BROWSER] Search completed. URL: {self.page.url}")
                
                return {
                    "status": "success",
                    "query": query,
                    "url": self.page.url,
                    "title": await self.page.title()
                }
            
            return {"error": "Could not find search box"}
        
        except Exception as e:
            print(f"[ERROR] Search failed: {str(e)}")
            return {"error": str(e)}
    
    async def navigate(self, url: str) -> Dict:
        """
        Navigate to URL
        """
        try:
            if not self.page:
                return {"error": "Browser not connected"}
            
            print(f"[BROWSER] Navigating to: {url}")
            
            await self.page.goto(url)
            await self.page.wait_for_load_state("load")
            
            return {
                "status": "success",
                "url": self.page.url,
                "title": await self.page.title()
            }
        
        except Exception as e:
            print(f"[ERROR] Navigation failed: {str(e)}")
            return {"error": str(e)}
    
    async def extract_text(self, selector: Optional[str] = None) -> Dict:
        """
        Extract text from page or specific element
        """
        try:
            if not self.page:
                return {"error": "Browser not connected"}
            
            print("[BROWSER] Extracting text...")
            
            if selector:
                element = await self.page.query_selector(selector)
                if element:
                    text = await element.text_content()
                else:
                    text = "Element not found"
            else:
                text = await self.page.text_content()
            
            return {
                "status": "success",
                "text": text,
                "url": self.page.url
            }
        
        except Exception as e:
            print(f"[ERROR] Text extraction failed: {str(e)}")
            return {"error": str(e)}
    
    async def click(self, selector: str) -> Dict:
        """
        Click on element
        """
        try:
            if not self.page:
                return {"error": "Browser not connected"}
            
            print(f"[BROWSER] Clicking element: {selector}")
            
            await self.page.click(selector)
            await self.page.wait_for_load_state("load")
            
            return {
                "status": "success",
                "action": "clicked",
                "url": self.page.url
            }
        
        except Exception as e:
            print(f"[ERROR] Click failed: {str(e)}")
            return {"error": str(e)}
    
    async def fill_form(self, form_data: Dict) -> Dict:
        """
        Fill and submit form
        
        Args:
            form_data: {selector: value, ...}
        """
        try:
            if not self.page:
                return {"error": "Browser not connected"}
            
            print(f"[BROWSER] Filling form with {len(form_data)} fields...")
            
            for selector, value in form_data.items():
                await self.page.fill(selector, str(value))
            
            return {
                "status": "success",
                "fields_filled": len(form_data)
            }
        
        except Exception as e:
            print(f"[ERROR] Form fill failed: {str(e)}")
            return {"error": str(e)}
    
    async def take_screenshot(self, output_path: str = "screenshot.png") -> Dict:
        """
        Take screenshot of current page
        """
        try:
            if not self.page:
                return {"error": "Browser not connected"}
            
            print(f"[BROWSER] Taking screenshot...")
            
            await self.page.screenshot(path=output_path)
            
            return {
                "status": "success",
                "path": output_path,
                "url": self.page.url
            }
        
        except Exception as e:
            print(f"[ERROR] Screenshot failed: {str(e)}")
            return {"error": str(e)}
    
    async def get_page_info(self) -> Dict:
        """
        Get current page information
        """
        try:
            if not self.page:
                return {"error": "Browser not connected"}
            
            return {
                "title": await self.page.title(),
                "url": self.page.url,
                "is_connected": self.is_connected
            }
        
        except Exception as e:
            return {"error": str(e)}
    
    async def close(self):
        """Close browser connection"""
        if self.browser:
            await self.browser.close()
            self.is_connected = False
            print("[BROWSER] Browser connection closed")


# Example usage
async def test_browser_agent():
    """Test the browser agent"""
    
    agent = BrowserAgent()
    
    # Note: You need to have Chrome running with remote debugging
    # Start Chrome with: google-chrome --remote-debugging-port=9222
    
    if await agent.connect_to_browser():
        # Test search
        result = await agent.search("weather in hyderabad")
        print(f"Search result: {result}")
        
        # Get page info
        info = await agent.get_page_info()
        print(f"Page info: {info}")
        
        await agent.close()
    else:
        print("Could not connect to browser")


if __name__ == "__main__":
    print("""
    Browser Agent - Setup Instructions
    
    To use this agent, start Chrome with remote debugging:
    
    Windows:
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222
    
    macOS:
    /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222
    
    Linux:
    google-chrome --remote-debugging-port=9222
    
    Then run this script.
    """)
    
    asyncio.run(test_browser_agent())
