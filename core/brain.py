"""
MEGAN Brain - Central AI Coordinator (powered by Google Gemini)
Processes requests and routes to appropriate agents
"""

import asyncio
from typing import Dict, Optional, Any
from datetime import datetime

from core.config import GEMINI_API_KEY, GEMINI_MODEL, MAX_TOKENS, RESPONSE_LANGUAGE


class MEGANBrain:
    """
    Central brain powered by Google Gemini that:
    - Understands user intent
    - Routes to appropriate agents
    - Coordinates multi-step tasks
    - Maintains conversation context
    """

    def __init__(self):
        self._client  = None   # google.genai.Client
        self._genai   = None   # google.genai module
        self._types   = None   # google.genai.types module
        self.model    = GEMINI_MODEL
        self.agents: Dict[str, Any] = {
            "browser":   None,
            "messaging": None,
            "file":      None,
            "vision":    None,
            "voice":     None,
            "system":    None,
        }
        self.conversation_history: Dict[str, list] = {}
        self.system_prompt = self._load_system_prompt()

    # ─── Initialization ──────────────────────────────────────────────────────

    async def initialize(self):
        """Initialize brain and Gemini client."""
        print("[BRAIN] Initializing MEGAN Brain (Gemini)...")
        if not GEMINI_API_KEY:
            print("[BRAIN] WARN: GEMINI_API_KEY not set -- using echo fallback mode")
        else:
            try:
                from google import genai
                from google.genai import types
                self._genai = genai
                self._types = types
                self._client = genai.Client(api_key=GEMINI_API_KEY)
                print(f"[BRAIN] Gemini client ready ({self.model})")
            except ImportError:
                print("[BRAIN] WARN: google-genai not installed -- run: pip install google-genai")
            except Exception as e:
                print(f"[BRAIN] WARN: Gemini init failed: {e}")
        print("[BRAIN] Brain online. Ready to think.")

    # ─── System Prompt ───────────────────────────────────────────────────────

    def _load_system_prompt(self) -> str:
        if RESPONSE_LANGUAGE == "hinglish":
            return self._hinglish_prompt()
        return self._english_prompt()

    def _hinglish_prompt(self) -> str:
        return """Tu MEGAN hai — ek advanced AI assistant jo JARVIS se inspired hai. Tu ek smart, warm aur helpful female assistant hai jiske saath baat karna natural lagta hai.

TERI SABSE BADI KHASIYAT:
Tu Hinglish mein baat karti hai — yaani Roman Hindi aur English ka natural mix, jaise real Indians bolte hain.

EXAMPLE RESPONSES:
- "Bilkul! Main abhi search karti hun."
- "Aapka kaam ho gaya! File successfully save ho gayi."
- "Koi baat nahi, main dobara try karti hun."
- "Aaj ka weather kaafi accha lag raha hai Delhi mein!"
- "Sure! WhatsApp pe message bhej deti hun."
- "System info check kar liya — CPU 30% pe hai, sab theek hai."

TERI LANGUAGE RULES:
1. HAMESHA Roman Hindi + English mix mein jawab de — kabhi pure Devanagari (Hindi script) mat likho
2. Natural bolne wali bhasha use kar, jaise ek friend baat karti hai
3. English technical words toh English mein hi reh sakte hain (file, search, browser, CPU, RAM etc.)
4. Chhoti si warmth aur energy rakh — boring ya robotic mat lag
5. Short aur to-the-point reh — zyada bada paragraph mat likh unless zaroorat ho
6. Agar user English mein likhe — Hinglish mein jawab de
7. Agar user Hindi mein likhe — Hinglish mein jawab de
8. Agar user Hinglish mein likhe — Hinglish mein jawab de

TERI PERSONALITY:
- Naam: MEGAN (Main apne aap ko MEGAN kehti hun)
- Tone: Confident, friendly, helpful — jaise ek smart female friend
- Greetings: "Haan bolo!", "Ji haan!", "Bilkul!", "Sure!", "Ho jayega!"
- Acknowledgement: "Samajh gayi", "Noted!", "Theek hai", "Done!"

TERI CAPABILITIES (Available Agents):
- Browser Agent: Google search karna, websites pe jaana, data extract karna
- Messaging Agent: WhatsApp aur email se messages bhejna
- File Agent: Files dhundhna, padhna, likhna, delete karna, organize karna
- Vision Module: Screenshot lena, screen ka text padhna (OCR)
- System Agent: Volume/brightness control, apps kholna, system info

AGENT TRIGGERING (CRITICAL):
        Format: <agent name="agent_name" task="task_name">{"key": "value"}</agent>
        
        === BROWSER AGENT ===
        - Google search: <agent name="browser" task="search">{"query": "kya dhundna hai"}</agent>
        - YouTube search: <agent name="browser" task="youtube_search">{"query": "video name"}</agent>
        - Website open: <agent name="browser" task="navigate">{"url": "https://example.com"}</agent>
        - Song play: <agent name="browser" task="play_song">{"song_name": "song", "artist": "singer"}</agent>
        - Quick info (weather/news): <agent name="browser" task="check_info">{"query": "weather in delhi today"}</agent>
        
        === SYSTEM AGENT ===
        - Brightness badhana: <agent name="system" task="brightness">{"level": 80}</agent>
        - Volume set: <agent name="system" task="volume">{"level": 60}</agent>
        - Volume mute: <agent name="system" task="mute">{"mute": true}</agent>
        - Volume get: <agent name="system" task="get_volume">{}</agent>
        - Brightness get: <agent name="system" task="get_brightness">{}</agent>
        - App kholna: <agent name="system" task="open_app">{"app": "notepad"}</agent>
        - File kholna (default app se): <agent name="system" task="open_file">{"path": "C:/path/to/file.pdf"}</agent>
        - File kholna specific app se: <agent name="system" task="open_file">{"path": "C:/code/main.py", "app": "vscode"}</agent>
        - VS Code mein project open: <agent name="system" task="open_vscode">{"path": "C:/Users/PMLS/myproject"}</agent>
        - Folder open karna (Explorer): <agent name="system" task="open_folder">{"path": "C:/Users/PMLS/Documents"}</agent>
        - CMD open karna: <agent name="system" task="open_cmd">{"path": "C:/Users/PMLS"}</agent>
        - PowerShell open: <agent name="system" task="open_powershell">{"path": "C:/Users/PMLS"}</agent>
        - CMD command run: <agent name="system" task="run_command">{"command": "ipconfig", "working_dir": "C:/"}</agent>
        - Naya terminal window mein command: <agent name="system" task="run_command">{"command": "npm install", "open_new_window": true}</agent>
        - Media play/pause: <agent name="system" task="media">{"action": "play_pause"}</agent>
        - Media next: <agent name="system" task="media">{"action": "next"}</agent>
        - System info: <agent name="system" task="system_info">{}</agent>
        - Screen lock: <agent name="system" task="lock_screen">{}</agent>
        - Sleep mode: <agent name="system" task="sleep">{}</agent>
        - Clipboard copy: <agent name="system" task="clipboard_set">{"text": "text to copy"}</agent>
        - Process kill: <agent name="system" task="kill_process">{"name_or_pid": "chrome.exe"}</agent>
        
        === FILE AGENT ===
        - File dhundhna: <agent name="file" task="find">{"directory": "C:/Users/PMLS", "pattern": "report", "file_type": ".pdf"}</agent>
        - Folder list: <agent name="file" task="list">{"directory": "C:/Users/PMLS/Desktop"}</agent>
        - File padhna: <agent name="file" task="read">{"path": "C:/path/to/file.txt"}</agent>
        - File likhna: <agent name="file" task="write">{"path": "C:/path/file.txt", "content": "content here", "overwrite": false}</agent>
        - File copy karna: <agent name="file" task="copy">{"source": "C:/from/file.txt", "destination": "C:/to/"}</agent>
        - File move karna: <agent name="file" task="move">{"source": "C:/from/file.txt", "destination": "C:/to/"}</agent>
        - File rename karna: <agent name="file" task="rename">{"source": "C:/path/old.txt", "new_name": "new.txt"}</agent>
        - File/folder delete: <agent name="file" task="delete">{"path": "C:/path/file.txt", "confirm": true}</agent>
        - Folder banana: <agent name="file" task="create_folder">{"path": "C:/Users/PMLS/NewFolder"}</agent>
        - File banana: <agent name="file" task="create_file">{"path": "C:/path/new.txt", "content": ""}</agent>
        - Folder organize karna (by type): <agent name="file" task="organize">{"directory": "C:/Users/PMLS/Desktop", "confirm": true}</agent>
        - Organize by date: <agent name="file" task="organize_by_date">{"directory": "C:/Users/PMLS/Downloads", "confirm": true}</agent>
        - File info: <agent name="file" task="file_info">{"path": "C:/path/to/file"}</agent>
        - Content search: <agent name="file" task="search_content">{"directory": "C:/project", "keyword": "todo", "file_type": ".py"}</agent>
        
        === MESSAGING AGENT ===
        - WhatsApp (Browser): <agent name="messaging" task="send_whatsapp">{"contact": "Sineha", "message": "Hello", "method": "browser"}</agent>
        - WhatsApp (App): <agent name="messaging" task="send_whatsapp">{"contact": "Mom", "message": "Hi", "method": "app"}</agent>
        - WhatsApp Media: <agent name="messaging" task="send_whatsapp">{"contact": "Sineha", "message": "Pic", "method": "browser", "media_path": "C:/image.pdf"}</agent>
        - WhatsApp Read Msg: <agent name="messaging" task="read_whatsapp">{"contact": "Sineha"}</agent>
        - WhatsApp Schedule: <agent name="messaging" task="schedule_whatsapp">{"contact": "Mom", "message": "Wake up!", "delay_seconds": 60, "method": "browser"}</agent>
        - WhatsApp Auto Reply: <agent name="messaging" task="start_auto_reply">{"contact": "Mom"}</agent>
        
        RULES:
        1. HAMESHA ek hi agent tag per response
        2. Delete karne se pehle HAMESHA confirm karo
        3. Song play ke liye play_song use karo
        4. File khone ke liye open_file use karo, VS Code project ke liye open_vscode
        
        RESPONSE FORMAT:
        - Simple kaam: 1-2 lines
        - Complex: Step-by-step"""

    def _english_prompt(self) -> str:
        return """You are MEGAN, an advanced AI assistant inspired by JARVIS. You are warm, intelligent, and speak naturally like a real assistant — not robotic. Your voice is female and your personality is professional yet friendly.

You are the central brain that:
1. UNDERSTANDS USER INTENT — parse what the user actually wants
2. ROUTES TASKS — decide which agent to use (browser, messaging, file, vision, voice, system)
3. COORDINATES — manage multi-step tasks
4. LEARNS — remember preferences and past interactions
5. RESPONDS — give natural, concise, helpful responses

AVAILABLE AGENTS:
- Browser Agent: search Google, navigate websites, click, fill forms, extract data
- Messaging Agent: send WhatsApp messages, compose emails
- File Agent: find files, read files, write, delete, organize directories
- Vision Module: take screenshot, read screen text (OCR), describe screen
- Voice Module: speech to text, text to speech, voice synthesis
- System Agent: change volume/brightness, open applications, lock screen, get system info

AGENT TRIGGERING (CRITICAL):
        Format: <agent name="agent_name" task="task_name">{"key": "value"}</agent>
        
        === BROWSER AGENT ===
        - Google search: <agent name="browser" task="search">{"query": "search term"}</agent>
        - YouTube search: <agent name="browser" task="youtube_search">{"query": "video name"}</agent>
        - Open website: <agent name="browser" task="navigate">{"url": "https://example.com"}</agent>
        - Play song: <agent name="browser" task="play_song">{"song_name": "song", "artist": "artist"}</agent>
        - Quick info (weather/news/scores): <agent name="browser" task="check_info">{"query": "weather in london"}</agent>
        
        === SYSTEM AGENT ===
        - Set brightness: <agent name="system" task="brightness">{"level": 80}</agent>
        - Set volume: <agent name="system" task="volume">{"level": 60}</agent>
        - Mute/unmute: <agent name="system" task="mute">{"mute": true}</agent>
        - Get volume: <agent name="system" task="get_volume">{}</agent>
        - Get brightness: <agent name="system" task="get_brightness">{}</agent>
        - Open app: <agent name="system" task="open_app">{"app": "notepad"}</agent>
        - Open file (default app): <agent name="system" task="open_file">{"path": "C:/path/file.pdf"}</agent>
        - Open file in specific app: <agent name="system" task="open_file">{"path": "C:/main.py", "app": "vscode"}</agent>
        - Open in VS Code: <agent name="system" task="open_vscode">{"path": "C:/project/folder"}</agent>
        - Open folder in Explorer: <agent name="system" task="open_folder">{"path": "C:/Users/PMLS"}</agent>
        - Open CMD: <agent name="system" task="open_cmd">{"path": "C:/project"}</agent>
        - Open PowerShell: <agent name="system" task="open_powershell">{"path": "C:/project"}</agent>
        - Run command (get output): <agent name="system" task="run_command">{"command": "ipconfig", "working_dir": "C:/"}</agent>
        - Run command (new window): <agent name="system" task="run_command">{"command": "npm run dev", "open_new_window": true, "working_dir": "C:/project"}</agent>
        - Media play/pause: <agent name="system" task="media">{"action": "play_pause"}</agent>
        - Media next/prev: <agent name="system" task="media">{"action": "next"}</agent>
        - System info: <agent name="system" task="system_info">{}</agent>
        - Lock screen: <agent name="system" task="lock_screen">{}</agent>
        - Sleep: <agent name="system" task="sleep">{}</agent>
        - Copy to clipboard: <agent name="system" task="clipboard_set">{"text": "text"}</agent>
        - Kill process: <agent name="system" task="kill_process">{"name_or_pid": "chrome.exe"}</agent>
        
        === FILE AGENT ===
        - Find files: <agent name="file" task="find">{"directory": "C:/Users/PMLS", "pattern": "report", "file_type": ".pdf"}</agent>
        - List folder: <agent name="file" task="list">{"directory": "C:/Users/PMLS/Desktop"}</agent>
        - Read file: <agent name="file" task="read">{"path": "C:/path/file.txt"}</agent>
        - Write file: <agent name="file" task="write">{"path": "C:/path/file.txt", "content": "text", "overwrite": false}</agent>
        - Copy file/folder: <agent name="file" task="copy">{"source": "C:/from/file", "destination": "C:/to/"}</agent>
        - Move file/folder: <agent name="file" task="move">{"source": "C:/from/file", "destination": "C:/to/"}</agent>
        - Rename: <agent name="file" task="rename">{"source": "C:/old.txt", "new_name": "new.txt"}</agent>
        - Delete: <agent name="file" task="delete">{"path": "C:/path/file", "confirm": true}</agent>
        - Create folder: <agent name="file" task="create_folder">{"path": "C:/NewFolder"}</agent>
        - Create file: <agent name="file" task="create_file">{"path": "C:/new.txt", "content": ""}</agent>
        - Organize by type: <agent name="file" task="organize">{"directory": "C:/Desktop", "confirm": true}</agent>
        - Organize by date: <agent name="file" task="organize_by_date">{"directory": "C:/Downloads", "confirm": true}</agent>
        - File info: <agent name="file" task="file_info">{"path": "C:/path"}</agent>
        - Search in files: <agent name="file" task="search_content">{"directory": "C:/project", "keyword": "todo"}</agent>
        
        === MESSAGING AGENT ===
        - WhatsApp (Browser): <agent name="messaging" task="send_whatsapp">{"contact": "Sineha", "message": "Hello", "method": "browser"}</agent>
        - WhatsApp (App): <agent name="messaging" task="send_whatsapp">{"contact": "Mom", "message": "Hi", "method": "app"}</agent>
        - WhatsApp Media: <agent name="messaging" task="send_whatsapp">{"contact": "Sineha", "message": "Pic", "method": "browser", "media_path": "C:/doc.pdf"}</agent>
        - WhatsApp Read Msg: <agent name="messaging" task="read_whatsapp">{"contact": "Sineha"}</agent>
        - WhatsApp Schedule: <agent name="messaging" task="schedule_whatsapp">{"contact": "Mom", "message": "Reminder", "delay_seconds": 3600}</agent>
        - WhatsApp Auto Reply: <agent name="messaging" task="start_auto_reply">{"contact": "Mom"}</agent>
        
        RULES:
        - Only one agent tag per response
        - Always confirm before delete operations
        - Use play_song for music, not navigate
        - Use check_info for weather/news, not plain search

YOUR PERSONALITY:
- Speak naturally and conversationally, like a real assistant
- Be concise — avoid long walls of text unless asked
- Use first-person: "I'll search that for you", "I found..."
- Add warmth: acknowledge the user, be encouraging

YOUR RULES:
1. Understand before acting
2. Always confirm before destructive operations
3. Never access private data without permission
4. Be honest about limitations
5. Break complex tasks into clear steps

RESPONSE STYLE:
- Short and direct for simple questions
- Step-by-step for complex tasks
- Never output JSON or code unless explicitly asked"""

    # ─── Message Processing ──────────────────────────────────────────────────

    async def process_message(
        self,
        user_id: str,
        content: str,
        message_type: str = "text",
        context: Optional[Dict] = None,
    ) -> str:
        """
        Process a user message through Gemini and return a response.

        Args:
            user_id:      User identifier
            content:      User's message text
            message_type: 'text', 'voice', or 'command'
            context:      User context from memory

        Returns:
            MEGAN's response string
        """
        # Build context-enriched message
        user_message = self._build_context_message(content, message_type, context)

        # Initialize conversation history
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []

        # Add to history
        self.conversation_history[user_id].append(
            {"role": "user", "parts": [user_message]}
        )

        # Get Gemini response (in thread pool — blocking SDK call)
        response = await asyncio.to_thread(
            self._get_gemini_response, user_id
        )

        # Add assistant response to history
        self.conversation_history[user_id].append(
            {"role": "model", "parts": [response]}
        )

        # Parse and execute any agent tags in the response
        import re
        import json
        pattern = r'<agent\s+name="([^"]+)"\s+task="([^"]+)">([^<]*)</agent>'
        match = re.search(pattern, response)
        if match:
            agent_name = match.group(1)
            task       = match.group(2)
            try:
                params = json.loads(match.group(3))
            except Exception:
                params = {}

            print(f"[BRAIN] Agent command: {agent_name} → {task} | params: {params}")

            # Clean the XML tag from the visible response
            response = re.sub(pattern, '', response).strip()

            # Execute the agent task and append a result line for the user
            try:
                agent_result = await self.execute_agent_task(agent_name, task, params)
                result_line  = self._format_agent_result(agent_name, task, agent_result)
                if result_line:
                    response = response.rstrip() + "\n\n" + result_line
            except Exception as ex:
                response += f"\n\n⚠ Agent error: {ex}"

        # Keep history manageable (last 30 turns)
        if len(self.conversation_history[user_id]) > 30:
            self.conversation_history[user_id] = \
                self.conversation_history[user_id][-30:]

        return response

    def _build_context_message(
        self,
        content: str,
        message_type: str,
        context: Optional[Dict],
    ) -> str:
        """Inject user context into the message."""
        msg = content
        prefix_parts = []

        if context:
            if context.get("user_name"):
                prefix_parts.append(f"User name: {context['user_name']}")
            if context.get("last_mood"):
                prefix_parts.append(f"Current mood: {context['last_mood']}")
            if context.get("recent_activities"):
                recent = context["recent_activities"][-3:]
                prefix_parts.append(f"Recent topics: {', '.join(recent)}")

        if message_type == "voice":
            prefix_parts.append("[Message type: voice — respond conversationally]")

        if prefix_parts:
            msg = "[Context: " + " | ".join(prefix_parts) + "]\n" + msg

        return msg

    def _get_gemini_response(self, user_id: str) -> str:
        """
        Call Gemini API synchronously (runs in asyncio.to_thread).
        Uses the google-genai SDK (v1+, non-deprecated).
        """
        if self._client is None:
            return (
                "I'm MEGAN in echo mode. My Gemini AI brain isn't configured yet. "
                "Please set GEMINI_API_KEY in your .env file and restart the server."
            )

        try:
            from google.genai import types

            # Build the full contents list (chat history)
            history = self.conversation_history.get(user_id, [])

            # Convert from {role, parts} format to google-genai Content objects
            contents = []
            for msg in history:
                role  = "user" if msg["role"] == "user" else "model"
                text  = msg["parts"][0] if msg["parts"] else ""
                contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part(text=text)]
                    )
                )

            config = types.GenerateContentConfig(
                system_instruction=self.system_prompt,
                max_output_tokens=MAX_TOKENS,
                temperature=0.7,
                top_p=0.95,
            )

            response = self._client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )
            return response.text

        except Exception as e:
            print(f"[ERROR] Gemini response error: {str(e)}")
            return f"I'm sorry, I ran into an issue: {str(e)}"

    # ─── Agent Result Formatter ───────────────────────────────────────────────

    def _format_agent_result(self, agent_name: str, task: str, result: Dict) -> str:
        """Convert raw agent result dict into a short human-readable line."""
        res = result.get("result", result)   # unwrap if nested
        status = result.get("status", res.get("status", "?"))

        if status == "error" or result.get("status") == "error":
            err = result.get("error", res.get("error", "unknown error"))
            return f"⚠ Browser action failed: {err}"

        if agent_name == "browser":
            url   = res.get("url", "")
            title = res.get("title", "")
            snippet = res.get("snippet", "")

            if task == "play_song":
                action = res.get("action", "")
                video = res.get("video_title") or res.get("title", "")
                if action == "playing" and video and video != "YouTube":
                    return f"🎵 Playing: **{video}**" + (f"\n🔗 {url}" if url else "")
                else:
                    note = res.get("note", "")
                    msg = "🎵 YouTube search opened for your song!"
                    if note:
                        msg += f"\n{note}"
                    if url:
                        msg += f"\n🔗 {url}"
                    return msg

            if task in ("search", "youtube_search"):
                engine = res.get("engine", "Google")
                return f"🔍 {engine.title()} search done — **{title}**\n🔗 {url}"

            if task == "check_info":
                lines = [f"📋 **{res.get('query', '')}**"]
                if snippet:
                    lines.append(snippet)
                if url:
                    lines.append(f"🔗 {url}")
                return "\n".join(lines)

            if task == "navigate":
                return f"🌐 Opened: **{title or url}**\n🔗 {url}"

            if task == "screenshot":
                return f"📸 Screenshot saved → `{res.get('path', 'screenshot.png')}`"

            if task == "extract_text":
                text = res.get("text", "")
                preview = text[:300] + ("…" if len(text) > 300 else "")
                return f"📄 Page text:\n{preview}"

            if task == "page_info":
                return f"📌 Current page: **{title}**\n🔗 {url}"

            if task in ("go_back", "go_forward", "close_tab", "new_tab"):
                return f"✅ Done — now at: {url}"

            if task == "scroll":
                return f"↕ Scrolled {res.get('direction','down')}"

            if title or url:
                return f"✅ {title or url}"

        if agent_name == "system":
            if task == "volume":
                return f"🔊 Volume set to **{res.get('volume', '?')}%**"
            if task == "get_volume":
                return f"🔊 Current volume: **{res.get('volume', '?')}%**"
            if task == "mute":
                muted = res.get("muted", True)
                return "🔇 Audio **muted**" if muted else "🔊 Audio **unmuted**"
            if task == "brightness":
                return f"☀️ Brightness set to **{res.get('brightness', '?')}%**"
            if task == "get_brightness":
                return f"☀️ Current brightness: **{res.get('brightness', '?')}%**"
            if task == "open_app":
                return f"🚀 Opening **{res.get('app', 'app')}**..."
            if task == "open_file":
                return f"📂 Opening: `{res.get('file', res.get('path', '?'))}`" + (f" with **{res.get('opened_with')}**" if res.get('opened_with') and res.get('opened_with') != 'default' else "")
            if task == "open_vscode":
                return f"💻 Opening in VS Code: `{res.get('path', '?')}`"
            if task in ("open_editor", "open_folder"):
                return f"📁 Opened: `{res.get('path', res.get('folder', '?'))}`"
            if task == "open_cmd":
                return f"⌨️ CMD opened at: `{res.get('path', '~')}`"
            if task == "open_powershell":
                return f"⌨️ PowerShell opened at: `{res.get('path', '~')}`"
            if task == "run_command":
                cmd  = res.get("command", "")
                mode = res.get("mode", "")
                if mode == "new_window":
                    return f"⌨️ Running in new terminal: `{cmd}`"
                out  = res.get("stdout", "")
                err  = res.get("stderr", "")
                rc   = res.get("returncode", 0)
                lines = [f"⌨️ Command: `{cmd}`", f"Return code: {rc}"]
                if out:
                    preview = out[:500] + ("..." if len(out) > 500 else "")
                    lines.append(f"```\n{preview}\n```")
                if err:
                    lines.append(f"⚠️ Stderr: {err[:200]}")
                return "\n".join(lines)
            if task == "media":
                icons = {"play_pause": "⏯", "next": "⏭", "prev": "⏮", "stop": "⏹",
                         "mute": "🔇", "volume_up": "🔊", "volume_down": "🔉"}
                icon = icons.get(res.get("action", ""), "🎵")
                return f"{icon} Media: **{res.get('action', 'done')}**"
            if task == "system_info":
                info = res
                lines = [
                    f"💻 **System Status**",
                    f"  CPU: {info.get('cpu_percent', '?')}% ({info.get('cpu_cores', '?')} cores)",
                    f"  RAM: {info.get('ram_used_gb', '?')} GB used / {info.get('ram_total_gb', '?')} GB ({info.get('ram_used_percent', '?')}%)",
                    f"  Disk: {info.get('disk_used_gb', '?')} GB / {info.get('disk_total_gb', '?')} GB ({info.get('disk_used_percent', '?')}%)",
                ]
                if "battery_percent" in info:
                    plug = "🔌" if info.get("battery_charging") else "🔋"
                    lines.append(f"  Battery: {plug} {info['battery_percent']}%")
                return "\n".join(lines)
            if task == "processes":
                procs = res.get("processes", [])
                lines = ["🖥 **Top Processes (by CPU)**"]
                for p in procs[:5]:
                    lines.append(f"  {p.get('name','?')} — CPU: {p.get('cpu_percent','?')}% | RAM: {round(p.get('memory_percent', 0), 1)}%")
                return "\n".join(lines)
            if task == "kill_process":
                killed = res.get("killed", [])
                return f"💀 Killed: **{', '.join(killed)}**" if killed else f"⚠️ Process not found"
            if task == "lock_screen":
                return "🔒 Screen locked"
            if task == "sleep":
                return "😴 Going to sleep..."
            if task == "shutdown":
                return f"⚡ {res.get('action', 'System action done')}"
            if task == "clipboard_set":
                return f"📋 Copied to clipboard ({res.get('characters', '?')} chars)"
            if task == "clipboard_get":
                text = res.get("text", "")
                return f"📋 Clipboard: {text[:200]}" if text else "📋 Clipboard is empty"
            return f"✅ Done"

        if agent_name == "file":
            if task == "find":
                count = res.get("count", 0)
                files = res.get("files", [])
                if count == 0:
                    return f"🔍 No files found matching your search in `{res.get('directory', '.')}`"
                lines = [f"🔍 Found **{count} file(s)**:"]
                for f in files[:8]:
                    lines.append(f"  📄 {f['name']} — {f['size_kb']} KB — {f['modified']}")
                if count > 8:
                    lines.append(f"  ...and {count - 8} more")
                return "\n".join(lines)

            if task == "list":
                folders = res.get("folders", [])
                files   = res.get("files", [])
                lines   = [f"📁 **{res.get('directory', '.')}** — {len(folders)} folders, {len(files)} files"]
                for f in folders[:5]:
                    lines.append(f"  📂 {f['name']}/ ({f.get('children', '?')} items)")
                for f in files[:10]:
                    lines.append(f"  📄 {f['name']} — {f.get('size_kb', 0)} KB")
                if len(files) > 10 or len(folders) > 5:
                    lines.append(f"  ...")
                return "\n".join(lines)

            if task == "read":
                content = res.get("content", "")
                preview = content[:500] + ("..." if len(content) > 500 else "")
                trunc   = " (truncated)" if res.get("truncated") else ""
                return f"📄 **{res.get('file', '?')}**{trunc}:\n```\n{preview}\n```"

            if task == "write":
                return f"✏️ File saved: `{res.get('file', '?')}` ({res.get('size', 0)} chars)"

            if task == "copy":
                return f"📋 Copied: `{res.get('source', '?')}` → `{res.get('destination', '?')}`"

            if task == "move":
                return f"✂️ Moved: `{res.get('source', '?')}` → `{res.get('destination', '?')}`"

            if task == "rename":
                return f"✏️ Renamed: `{res.get('old_name', '?')}` → `{res.get('new_name', '?')}`"

            if task == "delete":
                status = res.get("status", "")
                if status == "needs_confirmation":
                    return f"⚠️ **Confirmation needed:** {res.get('message', 'Are you sure?')}"
                return f"🗑️ Deleted: `{res.get('message', '?')}`"

            if task in ("bulk_delete", "bulk_copy", "bulk_move"):
                deleted = res.get("deleted") or res.get("copied") or res.get("moved") or []
                errors  = res.get("errors", [])
                op      = {"bulk_delete": "Deleted", "bulk_copy": "Copied", "bulk_move": "Moved"}[task]
                return f"✅ {op} {len(deleted)} items" + (f" ({len(errors)} errors)" if errors else "")

            if task == "create_folder":
                return f"📁 Folder created: `{res.get('folder', '?')}`"

            if task == "create_file":
                return f"📄 File created: `{res.get('file', '?')}`"

            if task == "organize":
                status = res.get("status", "")
                if status == "needs_confirmation":
                    preview = res.get("preview", {})
                    cats    = preview.get("categories", {})
                    total   = preview.get("total", 0)
                    lines   = [f"⚠️ **Confirmation needed** — Organize {total} files?"]
                    for cat, flist in list(cats.items())[:5]:
                        lines.append(f"  📂 {cat}: {len(flist)} files")
                    return "\n".join(lines)
                moved = res.get("moved", [])
                return f"✅ Organized **{len(moved)} files** into category folders"

            if task == "organize_by_date":
                status = res.get("status", "")
                if status == "needs_confirmation":
                    return f"⚠️ {res.get('message', 'Confirm organize by date?')}"
                return f"✅ Organized **{res.get('moved', 0)} files** by date"

            if task == "file_info":
                info = res
                size_kb = round(info.get("size_bytes", 0) / 1024, 1)
                return (
                    f"📄 **{info.get('name', '?')}**\n"
                    f"  Path: `{info.get('path', '?')}`\n"
                    f"  Size: {size_kb} KB\n"
                    f"  Type: {info.get('type', '?')}\n"
                    f"  Modified: {info.get('modified', '?')}"
                )

            if task == "search_content":
                matches = res.get("matches", [])
                count   = res.get("count", 0)
                if count == 0:
                    return f"🔍 No matches for **'{res.get('keyword', '')}'**"
                lines = [f"🔍 Found **{count} match(es)** for '{res.get('keyword', '')}'"]
                for m in matches[:5]:
                    lines.append(f"  📄 {m['file'].split(os.sep)[-1]}:{m['line_no']} — {m['line'][:80]}")
                return "\n".join(lines)

            if task == "disk_usage":
                return f"💾 **{res.get('path', '?')}**: {res.get('total_mb', 0)} MB ({res.get('file_count', 0)} files)"

            if task == "open_file":
                return f"📂 Opened: `{res.get('file', '?')}`"

            return f"✅ File operation '{task}' complete"

        if agent_name == "messaging":
            if task == "send_whatsapp":
                status = res.get("status", "")
                if status == "needs_confirmation":
                    return f"⚠️ **Confirmation needed:** {res.get('message', 'Are you sure?')}"
                if status == "success":
                    method = res.get("method", "browser")
                    has_media = res.get("has_media", False)
                    media_str = " 📎 (with media)" if has_media else ""
                    return f"✅ WhatsApp message sent to **{res.get('contact', '?')}** via {method}{media_str}"
            if task == "read_whatsapp":
                msgs = res.get("messages", [])
                if not msgs:
                    return f"📭 No recent messages found from **{res.get('contact', '?')}**"
                lines = [f"📬 **Recent messages from {res.get('contact', '?')}:**"]
                for i, m in enumerate(msgs, 1):
                    lines.append(f"  {i}. {m}")
                return "\n".join(lines)
            if task == "schedule_whatsapp":
                return f"⏰ Scheduled message to **{res.get('contact', '?')}** in {res.get('delay_seconds', 0)} seconds."
            if task == "start_auto_reply":
                return f"🤖 Auto-Reply monitor started for **{res.get('contact', '?')}**. Listening in the background..."
            if task == "send_email":
                return f"📧 Email sent to **{res.get('to', '?')}**\nSubject: {res.get('subject', '?')}"
            
            return f"✅ Messaging action '{task}' complete"

        return ""


    # ─── Agent Task Execution ─────────────────────────────────────────────────

    async def execute_agent_task(
        self,
        agent_name: str,
        task: str,
        parameters: Dict,
        priority: str = "normal",
        confirm_first: bool = False,
    ) -> Dict:
        """Execute a task through the specified agent."""
        print(f"[BRAIN] Executing: {task} via {agent_name} agent")

        agent = self.agents.get(agent_name)
        if agent is None:
            return {
                "agent":     agent_name,
                "task":      task,
                "status":    "unavailable",
                "message":   f"Agent '{agent_name}' is not loaded.",
                "timestamp": datetime.now().isoformat(),
            }

        try:
            # ── Browser ──────────────────────────────────────────────────────
            if agent_name == "browser":
                if task == "search":
                    result = await agent.search(
                        query=parameters.get("query", ""),
                        search_engine=parameters.get("engine", "google"),
                    )
                elif task == "youtube_search":
                    result = await agent.youtube_search(parameters.get("query", ""))

                elif task == "play_song":
                    result = await agent.play_song(
                        song_name=parameters.get("song_name", parameters.get("query", "")),
                        artist=parameters.get("artist", ""),
                    )

                elif task == "navigate":
                    result = await agent.navigate(parameters.get("url", ""))

                elif task == "check_info":
                    result = await agent.check_info(parameters.get("query", ""))

                elif task == "screenshot":
                    result = await agent.take_screenshot(
                        parameters.get("output_path", "screenshot.png")
                    )
                elif task == "extract_text":
                    result = await agent.extract_text(parameters.get("selector"))

                elif task == "page_info":
                    result = await agent.get_page_info()

                elif task == "new_tab":
                    result = await agent.new_tab(parameters.get("url", "about:blank"))

                elif task == "close_tab":
                    result = await agent.close_tab()

                elif task == "go_back":
                    result = await agent.go_back()

                elif task == "go_forward":
                    result = await agent.go_forward()

                elif task == "scroll":
                    result = await agent.scroll(
                        direction=parameters.get("direction", "down"),
                        amount=parameters.get("amount", 500),
                    )
                elif task == "click":
                    result = await agent.click(parameters.get("selector", ""))

                elif task == "fill_form":
                    result = await agent.fill_form(parameters.get("form_data", {}))

                else:
                    result = {"error": f"Unknown browser task: {task}"}

            # ── File ──────────────────────────────────────────────────────────
            elif agent_name == "file":
                if task == "find":
                    result = agent.find_files(
                        directory=parameters.get("directory", "."),
                        pattern=parameters.get("pattern"),
                        file_type=parameters.get("file_type"),
                        recursive=parameters.get("recursive", True),
                        max_results=parameters.get("max_results", 100),
                    )
                elif task == "list":
                    result = agent.list_directory(
                        parameters.get("directory", "."),
                        show_hidden=parameters.get("show_hidden", False),
                        sort_by=parameters.get("sort_by", "name"),
                    )
                elif task == "read":
                    result = agent.read_file(parameters.get("path", ""))
                elif task == "write":
                    result = agent.write_file(
                        file_path=parameters.get("path", ""),
                        content=parameters.get("content", ""),
                        overwrite=parameters.get("overwrite", False),
                        append=parameters.get("append", False),
                    )
                elif task == "copy":
                    result = agent.copy(
                        source=parameters.get("source", ""),
                        destination=parameters.get("destination", ""),
                        overwrite=parameters.get("overwrite", False),
                    )
                elif task == "move":
                    result = agent.move(
                        source=parameters.get("source", ""),
                        destination=parameters.get("destination", ""),
                        overwrite=parameters.get("overwrite", False),
                    )
                elif task == "rename":
                    result = agent.rename(
                        source=parameters.get("source", ""),
                        new_name=parameters.get("new_name", ""),
                    )
                elif task == "delete":
                    result = agent.delete(
                        path=parameters.get("path", ""),
                        confirm=parameters.get("confirm", False),
                    )
                elif task == "bulk_delete":
                    result = agent.bulk_delete(
                        paths=parameters.get("paths", []),
                        confirm=parameters.get("confirm", False),
                    )
                elif task == "bulk_copy":
                    result = agent.bulk_copy(
                        sources=parameters.get("sources", []),
                        destination=parameters.get("destination", ""),
                    )
                elif task == "bulk_move":
                    result = agent.bulk_move(
                        sources=parameters.get("sources", []),
                        destination=parameters.get("destination", ""),
                    )
                elif task == "create_folder":
                    result = agent.create_folder(parameters.get("path", ""))
                elif task == "create_file":
                    result = agent.create_file(
                        file_path=parameters.get("path", ""),
                        content=parameters.get("content", ""),
                    )
                elif task == "organize":
                    result = agent.organize_directory(
                        directory=parameters.get("directory", "."),
                        confirm=parameters.get("confirm", False),
                        dry_run=parameters.get("dry_run", False),
                    )
                elif task == "organize_by_date":
                    result = agent.organize_by_date(
                        directory=parameters.get("directory", "."),
                        confirm=parameters.get("confirm", False),
                    )
                elif task == "file_info":
                    result = agent.get_file_info(parameters.get("path", ""))
                elif task == "disk_usage":
                    result = agent.get_disk_usage(parameters.get("path", "."))
                elif task == "search_content":
                    result = agent.search_by_content(
                        directory=parameters.get("directory", "."),
                        keyword=parameters.get("keyword", ""),
                        file_type=parameters.get("file_type"),
                    )
                elif task == "open_file":
                    result = agent.open_file(parameters.get("path", ""))
                else:
                    result = {"error": f"Unknown file task: {task}"}

            # ── Messaging ─────────────────────────────────────────────────────
            elif agent_name == "messaging":
                if task == "send_whatsapp":
                    result = agent.send_whatsapp(
                        contact=parameters.get("contact", ""),
                        message=parameters.get("message", ""),
                        method=parameters.get("method", "browser"),
                        media_path=parameters.get("media_path", None),
                        phone=parameters.get("phone", None),
                        confirm=not confirm_first,
                    )
                elif task == "schedule_whatsapp":
                    result = agent.schedule_whatsapp(
                        contact=parameters.get("contact", ""),
                        message=parameters.get("message", ""),
                        delay_seconds=parameters.get("delay_seconds", 60),
                        method=parameters.get("method", "browser"),
                        phone=parameters.get("phone", None)
                    )
                elif task == "start_auto_reply":
                    result = agent.start_auto_reply(
                        contact=parameters.get("contact", ""),
                        phone=parameters.get("phone", None)
                    )
                elif task == "read_whatsapp":
                    result = agent.read_whatsapp(
                        contact=parameters.get("contact", ""),
                        limit=parameters.get("limit", 5)
                    )
                elif task == "send_email":
                    result = agent.send_email(
                        to=parameters.get("to", ""),
                        subject=parameters.get("subject", ""),
                        body=parameters.get("body", ""),
                    )
                else:
                    result = {"error": f"Unknown messaging task: {task}"}

            # ── Vision ────────────────────────────────────────────────────────
            elif agent_name == "vision":
                if task == "screenshot":
                    result = agent.take_screenshot(
                        parameters.get("output_path", "screen.png")
                    )
                elif task == "ocr":
                    result = agent.read_screen_text()
                elif task == "describe":
                    result = agent.describe_screen()
                else:
                    result = {"error": f"Unknown vision task: {task}"}

            # ── System ────────────────────────────────────────────────────────
            elif agent_name == "system":
                if task == "volume":
                    result = agent.set_volume(parameters.get("level", 50))
                elif task == "get_volume":
                    result = agent.get_volume()
                elif task == "mute":
                    result = agent.mute(parameters.get("mute", True))
                elif task == "brightness":
                    result = agent.set_brightness(parameters.get("level", 50))
                elif task == "get_brightness":
                    result = agent.get_brightness()
                elif task == "open_app":
                    result = agent.open_application(
                        parameters.get("app", ""),
                        args=parameters.get("args", []),
                    )
                elif task == "open_file":
                    result = agent.open_file(
                        parameters.get("path", ""),
                        app=parameters.get("app"),
                    )
                elif task == "open_vscode":
                    result = agent.open_in_vscode(
                        parameters.get("path", "."),
                        new_window=parameters.get("new_window", False),
                    )
                elif task == "open_editor":
                    result = agent.open_in_editor(
                        path=parameters.get("path", "."),
                        editor=parameters.get("editor", "vscode"),
                    )
                elif task == "open_folder":
                    result = agent.open_folder(parameters.get("path", "."))
                elif task == "open_cmd":
                    result = agent.open_cmd(parameters.get("path"))
                elif task == "open_powershell":
                    result = agent.open_powershell(parameters.get("path"))
                elif task == "run_command":
                    result = agent.run_command(
                        command=parameters.get("command", ""),
                        working_dir=parameters.get("working_dir"),
                        timeout=parameters.get("timeout", 30),
                        open_new_window=parameters.get("open_new_window", False),
                    )
                elif task == "type_text":
                    result = agent.type_text(parameters.get("text", ""))
                elif task == "press_keys":
                    result = agent.press_keys(*parameters.get("keys", []))
                elif task == "media":
                    result = agent.media_control(parameters.get("action", "play_pause"))
                elif task == "system_info":
                    result = agent.get_system_info()
                elif task == "processes":
                    result = agent.get_running_processes(
                        top_n=parameters.get("top_n", 10),
                        sort_by=parameters.get("sort_by", "cpu"),
                    )
                elif task == "kill_process":
                    result = agent.kill_process(parameters.get("name_or_pid", ""))
                elif task == "lock_screen":
                    result = agent.lock_screen()
                elif task == "sleep":
                    result = agent.sleep()
                elif task == "shutdown":
                    result = agent.shutdown(
                        confirm=parameters.get("confirm", False),
                        restart=parameters.get("restart", False),
                    )
                elif task == "clipboard_set":
                    result = agent.set_clipboard(parameters.get("text", ""))
                elif task == "clipboard_get":
                    result = agent.get_clipboard()
                else:
                    result = {"error": f"Unknown system task: {task}"}

            else:
                result = {"error": f"Unknown agent: {agent_name}"}

            return {
                "agent":     agent_name,
                "task":      task,
                "status":    "success",
                "result":    result,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            print(f"[ERROR] Agent task failed ({agent_name}/{task}): {str(e)}")
            return {
                "agent":     agent_name,
                "task":      task,
                "status":    "error",
                "error":     str(e),
                "timestamp": datetime.now().isoformat(),
            }

    # ─── Agent Registry ──────────────────────────────────────────────────────

    def set_agent(self, agent_name: str, agent_instance):
        """Register an agent with the brain."""
        if agent_name in self.agents:
            self.agents[agent_name] = agent_instance
            print(f"[BRAIN] Agent registered: {agent_name}")
        else:
            print(f"[BRAIN] WARN: Unknown agent name: {agent_name}")

    # ─── History ──────────────────────────────────────────────────────────────

    def get_conversation_history(self, user_id: str) -> list:
        return self.conversation_history.get(user_id, [])

    def clear_conversation_history(self, user_id: str):
        if user_id in self.conversation_history:
            del self.conversation_history[user_id]
            print(f"[BRAIN] History cleared for {user_id}")


# ─── Standalone Test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    async def test():
        brain = MEGANBrain()
        await brain.initialize()
        resp = await brain.process_message("test", "Who are you?")
        print(f"\nMEGAN: {resp}")

    asyncio.run(test())
