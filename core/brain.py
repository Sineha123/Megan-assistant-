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

TERE RULES:
1. Pehle samjho, phir karo
2. Delete ya message bhejne se pehle HAMESHA confirm karo
3. Private data permission ke bina mat access karo
4. Apni limitations ke baare mein honest reh
5. Complex kaam ko steps mein tod kar samjhao

AGENT TRIGGERING (CRITICAL):
Agar tumhe koi system action lena ho (jaise brightness change, browser search, music play karna), toh tumhe apne response ke END mein ek XML tag zaroor likhna hai.
Format: <agent name="agent_name" task="task_name">{"key": "value"}</agent>

Examples:
- Brightness tez karne ke liye: <agent name="system" task="brightness">{"level": 100}</agent>
- Brightness kam karne ke liye: <agent name="system" task="brightness">{"level": 30}</agent>
- YouTube pe song play karne ke liye: <agent name="browser" task="navigate">{"url": "https://www.youtube.com/results?search_query=dhun+song"}</agent>
- Google search karne ke liye: <agent name="browser" task="search">{"query": "weather in delhi"}</agent>

RESPONSE FORMAT:
- Simple sawaal: 1-2 lines mein jawab
- Complex task: Step-by-step batao"""

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
When you need to perform an action using an agent, you MUST append an XML tag at the very end of your response.
Format: <agent name="agent_name" task="task_name">{"key": "value"}</agent>

Examples:
- To increase brightness: <agent name="system" task="brightness">{"level": 100}</agent>
- To play a song on YouTube: <agent name="browser" task="navigate">{"url": "https://www.youtube.com/results?search_query=song+name"}</agent>
- To search Google: <agent name="browser" task="search">{"query": "current news"}</agent>

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
        pattern = r'<agent\s+name="([^"]+)"\s+task="([^"]+)">([^<]+)</agent>'
        match = re.search(pattern, response)
        if match:
            agent_name = match.group(1)
            task = match.group(2)
            try:
                params = json.loads(match.group(3))
            except Exception:
                params = {}
            
            print(f"[BRAIN] Intercepted agent command: {agent_name} -> {task} with params: {params}")
            # Run the agent task asynchronously without blocking the chat reply
            asyncio.create_task(self.execute_agent_task(agent_name, task, params))
            
            # Clean the response string so the XML is hidden from the user
            response = re.sub(pattern, '', response).strip()

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
                elif task == "navigate":
                    result = await agent.navigate(parameters.get("url", ""))
                elif task == "screenshot":
                    result = await agent.take_screenshot(
                        parameters.get("output_path", "screenshot.png")
                    )
                elif task == "extract_text":
                    result = await agent.extract_text(parameters.get("selector"))
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
                    )
                elif task == "list":
                    result = agent.list_directory(parameters.get("directory", "."))
                elif task == "read":
                    result = agent.read_file(parameters.get("path", ""))
                elif task == "write":
                    result = agent.write_file(
                        file_path=parameters.get("path", ""),
                        content=parameters.get("content", ""),
                        overwrite=parameters.get("overwrite", False),
                    )
                elif task == "delete":
                    result = agent.delete_file(
                        parameters.get("path", ""),
                        confirm=not confirm_first,
                    )
                elif task == "organize":
                    result = agent.organize_directory(
                        parameters.get("directory", "."),
                        confirm=not confirm_first,
                    )
                else:
                    result = {"error": f"Unknown file task: {task}"}

            # ── Messaging ─────────────────────────────────────────────────────
            elif agent_name == "messaging":
                if task == "send_whatsapp":
                    result = agent.send_whatsapp(
                        contact=parameters.get("contact", ""),
                        message=parameters.get("message", ""),
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
                elif task == "brightness":
                    result = agent.set_brightness(parameters.get("level", 50))
                elif task == "open_app":
                    result = agent.open_application(parameters.get("app", ""))
                elif task == "type_text":
                    result = agent.type_text(parameters.get("text", ""))
                elif task == "system_info":
                    result = agent.get_system_info()
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
