import asyncio
from playwright.async_api import async_playwright
import time
import os

async def run():
    print("Starting Playwright...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=['--window-size=1200,900'])
        context = await browser.new_context(viewport={'width': 1200, 'height': 900})
        page = await context.new_page()
        
        print("Navigating to MEGAN...")
        await page.goto("http://localhost:5174")
        
        # Wait for splash screen to disappear (class 'splash-exit')
        print("Waiting for splash screen...")
        await page.wait_for_selector('.megan-chat', timeout=10000)
        await asyncio.sleep(4) # extra wait for transitions
        
        async def send_message_and_wait(msg, filename):
            print(f"Sending: {msg}")
            # Type into textarea
            await page.fill('#megan-input', msg)
            await page.click('#megan-send-btn')
            
            # Wait for response (typing indicator appears then disappears)
            print("Waiting for response...")
            await asyncio.sleep(1) # wait for request to start
            # wait until typing indicator is gone
            await page.wait_for_selector('.typing-bubble', state='hidden', timeout=30000)
            await asyncio.sleep(2) # wait for render and animations
            
            os.makedirs('screenshots', exist_ok=True)
            path = f'screenshots/{filename}'
            await page.screenshot(path=path)
            print(f"Saved {path}")

        # Task 1: Basic
        await send_message_and_wait("Hello MEGAN! Kaun ho tum?", "screenshot_basic.png")
        
        # Task 2: Brightness
        await send_message_and_wait("Set system brightness to 60%", "screenshot_brightness.png")
        
        # Task 3: Browser
        await send_message_and_wait("Open browser and search for Gemini 1.5 Flash", "screenshot_browser.png")
        
        await browser.close()
        print("Done!")

if __name__ == "__main__":
    asyncio.run(run())
