"""
Messaging Agent - WhatsApp Web automation (Playwright) + WhatsApp Desktop App + Email via smtplib
"""

import time
import smtplib
import os
import asyncio
import concurrent.futures
from email.mime.text    import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional, List
from datetime import datetime

class MessagingAgent:
    """
    Messaging Agent for MEGAN.

    Capabilities:
    - Send WhatsApp messages via WhatsApp Web (Playwright with persistent session)
    - Send WhatsApp media via Web
    - Read recent WhatsApp messages via Web
    - Send WhatsApp messages via Windows Desktop App (pyautogui)
    - Send emails via SMTP
    """

    def __init__(self):
        self._scheduled: List[Dict] = []
        self.session_dir = os.path.abspath(os.path.join(os.getcwd(), "whatsapp_session"))
        os.makedirs(self.session_dir, exist_ok=True)

    # ─── WhatsApp Common ──────────────────────────────────────────────────────

    def send_whatsapp(
        self,
        contact: str,
        message: str,
        method: str = "browser",
        media_path: Optional[str] = None,
        phone: Optional[str] = None,
        confirm: bool = False,
    ) -> Dict:
        """
        Send a WhatsApp message.

        Args:
            contact: Contact name
            message: Message text
            method: 'browser' or 'app'
            media_path: Absolute path to media file (only works in browser mode)
            phone: Optional phone number (e.g. "+1234567890") for direct links
            confirm: If True, requires user confirmation before sending
        """
        if confirm:
            return {
                "status":  "needs_confirmation",
                "message": f"Send WhatsApp to '{contact}' via {method}? Message: \"{message}\"",
            }

        # Clean phone number if provided
        if phone:
            phone = ''.join(filter(str.isdigit, phone))

        if method == "browser":
            return self._run_async(self._send_whatsapp_browser(contact, message, media_path, phone))
        else:
            return self._send_whatsapp_app(contact, message, phone)

    def read_whatsapp(self, contact: str, limit: int = 5) -> Dict:
        """
        Read recent incoming messages from a specific contact via Browser.
        """
        return self._run_async(self._read_whatsapp_browser(contact, limit))

    # ─── Async Runner Helper ──────────────────────────────────────────────────

    def _run_async(self, coro):
        """Helper to run async Playwright code in sync environment safely."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, coro)
                    return future.result()
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            return asyncio.run(coro)

    # ─── WhatsApp Browser (Playwright) ────────────────────────────────────────

    async def _send_whatsapp_browser(self, contact: str, message: str, media_path: Optional[str] = None, phone: Optional[str] = None) -> Dict:
        """Send via Playwright with persistent session."""
        from playwright.async_api import async_playwright
        
        print(f"[MESSAGING] Launching WhatsApp Web for {contact}...")
        async with async_playwright() as p:
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=self.session_dir,
                headless=False,
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = browser.pages[0] if browser.pages else await browser.new_page()
            
            try:
                if phone:
                    # Direct link bypasses search
                    await page.goto(f"https://web.whatsapp.com/send/?phone={phone}", wait_until="domcontentloaded")
                else:
                    await page.goto("https://web.whatsapp.com", wait_until="domcontentloaded")
                
                # Wait for login and chat load
                try:
                    # div[contenteditable="true"][data-tab="10"] is the message box
                    await page.wait_for_selector('div[contenteditable="true"][data-tab="10"]', timeout=45000)
                except Exception:
                    # Fallback if chat isn't focused automatically
                    try:
                        await page.wait_for_selector('div[contenteditable="true"][data-tab="3"]', timeout=15000)
                    except:
                        await browser.close()
                        return {"error": "Timeout waiting for login. Please scan QR code and try again."}
                
                if not phone:
                    # Search contact manually if no phone number provided
                    search_box = await page.wait_for_selector('div[contenteditable="true"][data-tab="3"]')
                    await search_box.fill(contact)
                    await page.wait_for_timeout(2000)
                    await page.keyboard.press("Enter")
                    await page.wait_for_timeout(2000)
                
                # Type message
                if message:
                    msg_box = await page.wait_for_selector('div[contenteditable="true"][data-tab="10"]')
                    await msg_box.fill(message)
                    await msg_box.press("Enter")
                    await page.wait_for_timeout(1000)
                
                # Send Media
                if media_path and os.path.exists(media_path):
                    # Find Attach button robustly
                    attach_btn = None
                    selectors = [
                        'div[title="Attach"]',
                        'span[data-icon="plus"]', 
                        'span[data-icon="clip"]',
                        'button[aria-label="Attach"]'
                    ]
                    for sel in selectors:
                        try:
                            attach_btn = await page.wait_for_selector(sel, timeout=3000)
                            if attach_btn:
                                break
                        except:
                            continue
                            
                    if not attach_btn:
                        raise Exception("Could not find the Attach button on the screen")
                        
                    await attach_btn.click()
                    await page.wait_for_timeout(1500)
                    
                    # Wait for file chooser
                    async with page.expect_file_chooser() as fc_info:
                        # Click Image/Video icon in the menu
                        imgs = await page.locator('li > div > span').all()
                        clicked = False
                        for img in imgs:
                            try:
                                await img.click(timeout=1000)
                                clicked = True
                                break
                            except:
                                continue
                        
                        if not clicked:
                            # Fallback: look for generic input type=file
                            await page.evaluate("document.querySelector('input[type=file]').click()")
                            
                    file_chooser = await fc_info.value
                    await file_chooser.set_files(media_path)
                    await page.wait_for_timeout(2000)
                    
                    # Try to click Send button, or just press Enter if caption box is focused
                    send_btn = None
                    for sel in ['div[aria-label="Send"]', 'span[data-icon="send"]']:
                        try:
                            send_btn = await page.wait_for_selector(sel, timeout=3000)
                            if send_btn:
                                break
                        except:
                            continue
                            
                    if send_btn:
                        await send_btn.click()
                    else:
                        await page.keyboard.press("Enter")
                        
                    await page.wait_for_timeout(3000)
                    
                await browser.close()
                return {
                    "status": "success",
                    "method": "browser",
                    "contact": contact,
                    "has_media": bool(media_path)
                }
                
            except Exception as e:
                await browser.close()
                print(f"[ERROR] WhatsApp Browser send failed: {e}")
                return {"error": str(e)}

    async def _read_whatsapp_browser(self, contact: str, limit: int = 5) -> Dict:
        """Read latest incoming messages from a contact."""
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=self.session_dir,
                headless=False
            )
            page = browser.pages[0] if browser.pages else await browser.new_page()
            
            try:
                await page.goto("https://web.whatsapp.com", wait_until="domcontentloaded")
                await page.wait_for_selector('div[contenteditable="true"][data-tab="3"]', timeout=45000)
                
                search_box = await page.wait_for_selector('div[contenteditable="true"][data-tab="3"]')
                await search_box.fill(contact)
                await page.wait_for_timeout(2000)
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(3000)
                
                # Extract messages (incoming only)
                # WhatsApp uses .message-in for received messages
                msg_elements = await page.locator('div.message-in span.selectable-text').all()
                
                messages = []
                for el in msg_elements[-limit:]:
                    text = await el.inner_text()
                    if text:
                        messages.append(text)
                        
                await browser.close()
                return {
                    "status": "success",
                    "contact": contact,
                    "messages": messages
                }
            except Exception as e:
                await browser.close()
                return {"error": str(e)}

    # ─── WhatsApp App (PyAutoGUI) ─────────────────────────────────────────────

    def _send_whatsapp_app(self, contact: str, message: str, phone: Optional[str] = None) -> Dict:
        """Send via Windows WhatsApp Desktop App."""
        try:
            import pyautogui
            import pyperclip
        except ImportError:
            return {"error": "pyautogui and pyperclip are required for App mode. Run: pip install pyautogui pyperclip"}

        try:
            print(f"[MESSAGING] Launching WhatsApp Desktop...")
            
            if phone:
                # Direct launch to chat
                os.system(f"start whatsapp://send?phone={phone}")
                print("[MESSAGING] Waiting 6 seconds for app to load directly into chat...")
                time.sleep(6)
            else:
                # Launch and search
                os.system("start whatsapp:")
                print("[MESSAGING] Waiting 8 seconds for app to load and focus...")
                time.sleep(8)
                
                print(f"[MESSAGING] Searching for '{contact}'...")
                pyautogui.hotkey("ctrl", "f")
                time.sleep(1.5)
                
                pyperclip.copy(contact)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(2.5) # Wait for search results
                
                pyautogui.press("enter")
                time.sleep(1.5) # Wait for chat to open
            
            print(f"[MESSAGING] Typing message...")
            pyperclip.copy(message)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(1)
            pyautogui.press("enter")
            time.sleep(1)
            
            return {
                "status": "success",
                "method": "app",
                "contact": contact
            }
            
        except Exception as e:
            return {"error": str(e)}

    # ─── Advanced Features ────────────────────────────────────────────────────
    
    def schedule_whatsapp(
        self,
        contact: str,
        message: str,
        delay_seconds: int,
        method: str = "browser",
        phone: Optional[str] = None
    ) -> Dict:
        """Schedule a message to be sent after delay_seconds."""
        import threading
        
        def _delayed_send():
            import time
            time.sleep(delay_seconds)
            try:
                self.send_whatsapp(contact, message, method=method, phone=phone)
                print(f"\n[SCHEDULED] Sent message to {contact} successfully.")
            except Exception as e:
                print(f"\n[SCHEDULED ERROR] Failed to send to {contact}: {e}")

        t = threading.Thread(target=_delayed_send, daemon=True)
        t.start()
        
        return {
            "status": "scheduled",
            "contact": contact,
            "delay_seconds": delay_seconds,
            "method": method
        }

    def start_auto_reply(self, contact: str, phone: Optional[str] = None, reply_callback=None) -> Dict:
        """Starts a background monitor for a specific chat. If they message, auto-reply."""
        import threading
        
        # Clean phone
        if phone:
            phone = ''.join(filter(str.isdigit, phone))
            
        def _listener_loop():
            # Run async loop in thread
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._auto_reply_loop(contact, phone, reply_callback))
            
        t = threading.Thread(target=_listener_loop, daemon=True)
        t.start()
        
        return {
            "status": "listener_started",
            "contact": contact
        }

    async def _auto_reply_loop(self, contact: str, phone: Optional[str], reply_callback=None):
        """Persistent playwright session listening for messages."""
        from playwright.async_api import async_playwright
        import asyncio
        
        print(f"[AUTO-REPLY] Starting monitor for {contact}...")
        async with async_playwright() as p:
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=self.session_dir,
                headless=False,
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = browser.pages[0] if browser.pages else await browser.new_page()
            
            try:
                if phone:
                    await page.goto(f"https://web.whatsapp.com/send/?phone={phone}", wait_until="domcontentloaded")
                else:
                    await page.goto("https://web.whatsapp.com", wait_until="domcontentloaded")
                    # Search contact manually
                    search_box = await page.wait_for_selector('div[contenteditable="true"][data-tab="3"]', timeout=45000)
                    await search_box.fill(contact)
                    await page.wait_for_timeout(2000)
                    await page.keyboard.press("Enter")
                    
                await page.wait_for_selector('div[contenteditable="true"][data-tab="10"]', timeout=45000)
                
                last_msg = ""
                
                print(f"[AUTO-REPLY] Actively listening for messages from {contact}...")
                while True:
                    await page.wait_for_timeout(5000) # Poll every 5s
                    
                    # Extract last message
                    try:
                        msgs = await page.locator('div.message-in span.selectable-text').all_text_contents()
                        if not msgs:
                            continue
                            
                        current_last = msgs[-1].strip()
                        
                        # If we have a new message that isn't empty
                        if current_last and current_last != last_msg:
                            last_msg = current_last
                            print(f"\n[AUTO-REPLY] New message received: {current_last}")
                            
                            reply = ""
                            if reply_callback:
                                # Use dynamic callback for proper reply
                                if asyncio.iscoroutinefunction(reply_callback):
                                    reply = await reply_callback(current_last)
                                else:
                                    reply = reply_callback(current_last)
                            else:
                                # Simple fallback logic
                                text_lower = current_last.lower()
                                if "owner" in text_lower or "sineha" in text_lower or "admin" in text_lower:
                                    reply = "Hello! I am MEGAN, the AI assistant. My owner is currently busy, but I have notified them of your message. 🤖"
                                elif "hello" in text_lower or "hi" in text_lower:
                                    reply = "Hi there! This is an automated reply from MEGAN. How can I help?"
                            
                            if reply:
                                print(f"[AUTO-REPLY] Sending automated reply: {reply}")
                                msg_box = await page.wait_for_selector('div[contenteditable="true"][data-tab="10"]')
                                await msg_box.fill(reply)
                                await page.keyboard.press("Enter")
                                await page.wait_for_timeout(2000)
                                # Update last_msg so we don't reply again
                                msgs_after = await page.locator('div.message-in span.selectable-text').all_text_contents()
                                if msgs_after:
                                    last_msg = msgs_after[-1].strip()
                                
                    except Exception as e:
                        print(f"[AUTO-REPLY ERROR] {e}")
                        
            except Exception as e:
                print(f"[AUTO-REPLY FATAL ERROR] {e}")
            finally:
                # Loop runs forever until script dies
                pass

    # ─── Email ────────────────────────────────────────────────────────────────

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        from_email: Optional[str] = None,
        smtp_host: str = "smtp.gmail.com",
        smtp_port: int = 587,
        password: Optional[str] = None,
    ) -> Dict:
        sender   = from_email or os.getenv("MEGAN_EMAIL_ADDRESS", "")
        pwd      = password   or os.getenv("MEGAN_EMAIL_PASSWORD", "")

        if not sender or not pwd:
            return {"error": "Email credentials not configured in .env"}

        try:
            msg = MIMEMultipart()
            msg["From"]    = sender
            msg["To"]      = to
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.login(sender, pwd)
                server.send_message(msg)

            return {"status": "success", "to": to, "subject": subject}
        except Exception as e:
            return {"error": str(e)}

    # ─── Scheduled Messages ───────────────────────────────────────────────────

    def schedule_message(
        self, contact: str, message: str, send_at: datetime, method: str = "whatsapp"
    ) -> Dict:
        task = {
            "id": len(self._scheduled) + 1,
            "contact": contact,
            "message": message,
            "send_at": send_at.isoformat(),
            "method": method,
            "status": "scheduled",
        }
        self._scheduled.append(task)
        return {"status": "scheduled", "task": task}

    def list_scheduled(self) -> Dict:
        return {"status": "success", "scheduled": self._scheduled}
