"""
Messaging Agent - WhatsApp Web automation + Email via smtplib
Uses PyAutoGUI + Playwright to control WhatsApp Web
"""

import time
import smtplib
import os
from email.mime.text    import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional, List
from datetime import datetime


class MessagingAgent:
    """
    Messaging Agent for MEGAN.

    Capabilities:
    - Send WhatsApp messages via WhatsApp Web (requires open browser)
    - Send emails via SMTP
    - Search contacts
    - Schedule messages (via APScheduler — optional)

    Requirements for WhatsApp:
    - Chrome running with --remote-debugging-port=9222
    - WhatsApp Web open and logged in
    """

    def __init__(self, browser_page=None):
        """
        Args:
            browser_page: Optional Playwright page already connected to WhatsApp Web
        """
        self.page          = browser_page
        self._pyautogui    = None
        self._scheduled:   List[Dict] = []

    # ─── WhatsApp ─────────────────────────────────────────────────────────────

    def send_whatsapp(
        self,
        contact: str,
        message: str,
        confirm: bool = True,
    ) -> Dict:
        """
        Send a WhatsApp message.
        Uses Playwright if a browser page is available, otherwise PyAutoGUI.

        Args:
            contact: Contact name or number to search
            message: Message text to send
            confirm: Bypass confirmation (set False to prompt)

        Returns:
            Status dict
        """
        if not confirm:
            return {
                "status":  "needs_confirmation",
                "message": f"Send WhatsApp to '{contact}': \"{message}\"?",
            }

        if self.page is not None:
            return self._send_whatsapp_playwright(contact, message)
        else:
            return self._send_whatsapp_pyautogui(contact, message)

    def _send_whatsapp_playwright(self, contact: str, message: str) -> Dict:
        """Send via Playwright (WhatsApp Web must be open on self.page)."""
        try:
            import asyncio

            async def _send():
                # Navigate to WhatsApp Web if not already there
                if "web.whatsapp.com" not in self.page.url:
                    await self.page.goto("https://web.whatsapp.com")
                    await self.page.wait_for_load_state("networkidle")
                    time.sleep(3)

                # Search for contact
                search_box = await self.page.wait_for_selector(
                    '[data-testid="chat-list-search"]', timeout=10000
                )
                await search_box.fill(contact)
                await self.page.wait_for_load_state("networkidle")
                time.sleep(1)

                # Click first result
                first_result = await self.page.query_selector('[data-testid="cell-frame-container"]')
                if not first_result:
                    return {"error": f"Contact '{contact}' not found"}
                await first_result.click()
                time.sleep(1)

                # Type and send message
                msg_box = await self.page.wait_for_selector(
                    '[data-testid="conversation-compose-box-input"]', timeout=5000
                )
                await msg_box.fill(message)
                await msg_box.press("Enter")
                time.sleep(1)

                return {"status": "success", "contact": contact, "message": message}

            # Run async in new event loop if needed
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, _send())
                        return future.result()
                else:
                    return loop.run_until_complete(_send())
            except RuntimeError:
                return asyncio.run(_send())

        except Exception as e:
            print(f"[ERROR] WhatsApp Playwright send failed: {str(e)}")
            return {"error": str(e)}

    def _send_whatsapp_pyautogui(self, contact: str, message: str) -> Dict:
        """Fallback: use PyAutoGUI to control WhatsApp Web via keyboard."""
        try:
            import pyautogui
            import pyperclip

            print(f"[MESSAGING] Sending WhatsApp to '{contact}' via PyAutoGUI...")
            # Search for contact using keyboard shortcut
            pyautogui.hotkey("ctrl", "k")
            time.sleep(1)
            pyautogui.typewrite(contact, interval=0.05)
            time.sleep(2)
            pyautogui.press("enter")
            time.sleep(1)

            # Paste message (supports Unicode)
            pyperclip.copy(message)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.5)
            pyautogui.press("enter")
            time.sleep(0.5)

            return {
                "status":    "success",
                "method":    "pyautogui",
                "contact":   contact,
                "message":   message,
                "timestamp": datetime.now().isoformat(),
            }

        except ImportError:
            return {"error": "pyautogui not installed. Run: pip install pyautogui pyperclip"}
        except Exception as e:
            print(f"[ERROR] WhatsApp PyAutoGUI send failed: {str(e)}")
            return {"error": str(e)}

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
        """
        Send an email via SMTP.

        Reads credentials from environment variables if not provided:
          MEGAN_EMAIL_ADDRESS  — sender address
          MEGAN_EMAIL_PASSWORD — app password

        Args:
            to:         Recipient address
            subject:    Email subject
            body:       Email body (plain text)
            from_email: Sender address (defaults to env var)
            smtp_host:  SMTP server (default: Gmail)
            smtp_port:  SMTP port (default: 587 TLS)
            password:   SMTP password (defaults to env var)

        Returns:
            Status dict
        """
        sender   = from_email or os.getenv("MEGAN_EMAIL_ADDRESS", "")
        pwd      = password   or os.getenv("MEGAN_EMAIL_PASSWORD", "")

        if not sender or not pwd:
            return {
                "error": "Email credentials not configured. Set MEGAN_EMAIL_ADDRESS and "
                         "MEGAN_EMAIL_PASSWORD in your .env file.",
            }

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

            print(f"[MESSAGING] ✓ Email sent to {to}")
            return {
                "status":    "success",
                "to":        to,
                "subject":   subject,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            print(f"[ERROR] Email send failed: {str(e)}")
            return {"error": str(e)}

    # ─── Scheduled Messages ───────────────────────────────────────────────────

    def schedule_message(
        self,
        contact: str,
        message: str,
        send_at: datetime,
        method: str = "whatsapp",
    ) -> Dict:
        """
        Schedule a message to be sent at a specific time.
        Returns a task record; caller is responsible for executing at send_at.

        Args:
            contact: Recipient
            message: Message text
            send_at: datetime when to send
            method:  'whatsapp' or 'email'
        """
        task = {
            "id":      len(self._scheduled) + 1,
            "contact": contact,
            "message": message,
            "send_at": send_at.isoformat(),
            "method":  method,
            "status":  "scheduled",
        }
        self._scheduled.append(task)
        print(f"[MESSAGING] Scheduled {method} to '{contact}' at {send_at}")
        return {"status": "scheduled", "task": task}

    def list_scheduled(self) -> Dict:
        """List all scheduled messages."""
        return {"status": "success", "scheduled": self._scheduled}


# ─── Standalone Test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    agent = MessagingAgent()
    # Sends via PyAutoGUI — WhatsApp Web must be open and focused
    result = agent.send_whatsapp("Mom", "Hello! This is a test from MEGAN 🤖")
    print(result)
