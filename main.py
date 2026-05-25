"""
MEGAN - Main FastAPI Backend Server
Orchestrates all agents and handles API requests
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
import asyncio
from datetime import datetime

# ─── Core systems ─────────────────────────────────────────────────────────────
from core.config  import HOST, PORT, validate_config
from core.brain   import MEGANBrain
from core.memory  import MemoryManager
from utils.audio  import AudioProcessor

# ─── Agents ───────────────────────────────────────────────────────────────────
from agents.browser_agent   import BrowserAgent
from agents.file_agent      import FileAgent
from agents.messaging_agent import MessagingAgent
from agents.vision_agent    import VisionAgent
from agents.system_agent    import SystemAgent

# ─── FastAPI app ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="MEGAN Assistant",
    description="MEGAN -- AI assistant inspired by JARVIS",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Global instances ─────────────────────────────────────────────────────────
brain     = MEGANBrain()
memory    = MemoryManager()
audio     = AudioProcessor()

# Agent instances
_browser   = BrowserAgent()
_file      = FileAgent(safe_mode=True)
_messaging = MessagingAgent()
_vision    = VisionAgent(brain=brain)
_system    = SystemAgent()

# ============================================================== DATA MODELS ==

class ChatMessage(BaseModel):
    """User chat message"""
    user_id:      str
    content:      str
    message_type: str = "text"          # text | voice | command
    timestamp:    Optional[str] = None

class VoiceData(BaseModel):
    """Voice input (base64-encoded WAV)"""
    user_id:      str
    audio_base64: str
    language:     str = "en"

class TaskRequest(BaseModel):
    """Direct agent task execution"""
    agent:        str
    task:         str
    parameters:   Dict[str, Any] = {}
    priority:     str  = "normal"
    confirm_first: bool = False

class UserProfile(BaseModel):
    """User profile data"""
    user_id:       str
    name:          str
    voice_profile: Optional[str]  = None
    preferences:   Dict[str, Any] = {}

# ================================================================== ROUTES ==

@app.get("/", tags=["health"])
async def root():
    """Health check endpoint"""
    return {
        "status":    "active",
        "system":    "MEGAN",
        "version":   "1.0.0",
        "timestamp": datetime.now().isoformat(),
    }

# ─── Chat ────────────────────────────────────────────────────────────────────

@app.post("/chat", tags=["chat"])
async def chat_endpoint(message: ChatMessage):
    """
    Main chat endpoint.
    Processes user message through MEGAN Brain and returns a response.
    """
    try:
        print(f"[CHAT] {message.user_id}: {message.content[:80]}")

        user_context = memory.get_user_context(message.user_id)
        response = await brain.process_message(
            user_id=message.user_id,
            content=message.content,
            message_type=message.message_type,
            context=user_context,
        )

        memory.save_interaction(
            user_id=message.user_id,
            message=message.content,
            response=response,
            message_type=message.message_type,
        )

        return {
            "status":    "success",
            "response":  response,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        print(f"[ERROR] Chat endpoint: {str(e)}")
        return {
            "status":    "error",
            "error":     str(e),
            "timestamp": datetime.now().isoformat(),
        }

# ─── Voice ───────────────────────────────────────────────────────────────────

@app.post("/voice/upload", tags=["voice"])
async def voice_upload(data: VoiceData):
    """
    Voice input endpoint.
    Converts speech to text, processes through brain, returns text + audio response.
    """
    try:
        text = await audio.transcribe(data.audio_base64, data.language)

        user_context = memory.get_user_context(data.user_id)
        response = await brain.process_message(
            user_id=data.user_id,
            content=text,
            message_type="voice",
            context=user_context,
        )

        audio_response = await audio.synthesize(response)

        memory.save_interaction(
            user_id=data.user_id,
            message=f"[VOICE] {text}",
            response=response,
            message_type="voice",
        )

        return {
            "status":          "success",
            "transcribed_text": text,
            "response":        response,
            "audio_response":  audio_response,
            "timestamp":       datetime.now().isoformat(),
        }

    except Exception as e:
        print(f"[ERROR] Voice endpoint: {str(e)}")
        return {"status": "error", "error": str(e)}

# ─── Task Execution ──────────────────────────────────────────────────────────

@app.post("/task", tags=["agents"])
async def execute_task(task: TaskRequest):
    """
    Execute a specific task through a designated agent.
    Brain dispatches to the correct agent based on task.agent.
    """
    try:
        result = await brain.execute_agent_task(
            agent_name=task.agent,
            task=task.task,
            parameters=task.parameters,
            priority=task.priority,
            confirm_first=task.confirm_first,
        )
        return {
            "status":    "success",
            "result":    result,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}

# ─── User Profile ────────────────────────────────────────────────────────────

@app.post("/user/profile", tags=["user"])
async def set_user_profile(profile: UserProfile):
    """Save or update a user profile."""
    try:
        memory.save_user_profile(profile.dict())
        return {"status": "success", "message": "Profile saved"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/user/{user_id}/context", tags=["user"])
async def get_user_context(user_id: str):
    """Retrieve user context and memory."""
    try:
        context = memory.get_user_context(user_id)
        return {
            "status":    "success",
            "context":   context,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.delete("/user/{user_id}/history", tags=["user"])
async def clear_user_history(user_id: str):
    """Clear conversation history for a user."""
    brain.clear_conversation_history(user_id)
    return {"status": "success", "message": f"History cleared for {user_id}"}

# ─── System Status ───────────────────────────────────────────────────────────

@app.get("/system/status", tags=["system"])
async def system_status():
    """Get overall system status."""
    sys_info = _system.get_system_info()
    return {
        "status": "active",
        "brain":  "online" if brain._client else "echo_mode",
        "agents": {
            "browser":   "standby" if not _browser.is_connected else "connected",
            "messaging": "standby",
            "file":      "ready",
            "vision":    "ready" if _vision.is_ready else "limited",
            "voice":     "ready" if audio.is_ready   else "limited",
            "system":    "ready",
        },
        "memory":    "active",
        "system_info": sys_info,
        "timestamp": datetime.now().isoformat(),
    }

# ─── WebSocket ───────────────────────────────────────────────────────────────

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """
    WebSocket endpoint for real-time streaming communication.
    Useful for streaming responses and live updates.
    """
    await websocket.accept()
    print(f"[WS] Client connected: {user_id}")

    try:
        while True:
            data    = await websocket.receive_text()
            message = json.loads(data)

            user_context = memory.get_user_context(user_id)
            response = await brain.process_message(
                user_id=user_id,
                content=message.get("content", ""),
                message_type=message.get("type", "text"),
                context=user_context,
            )

            await websocket.send_json({
                "status":    "success",
                "response":  response,
                "timestamp": datetime.now().isoformat(),
            })

    except WebSocketDisconnect:
        print(f"[WS] Client disconnected: {user_id}")
    except Exception as e:
        print(f"[ERROR] WebSocket {user_id}: {str(e)}")
        try:
            await websocket.send_json({"status": "error", "error": str(e)})
        except Exception:
            pass

# =========================================================== STARTUP / SHUTDOWN ==

@app.on_event("startup")
async def startup_event():
    """Initialize all systems on startup."""
    print("=" * 54)
    print("MEGAN ASSISTANT SYSTEM STARTING...")
    print("=" * 54)

    # Config validation
    issues = validate_config()
    for issue in issues:
        print(f"WARN   {issue}")

    # Core systems
    await brain.initialize()
    print("OK  Brain initialized")

    memory.initialize()
    print("OK  Memory system initialized")

    audio.initialize()
    print("OK  Audio processor initialized")

    # Register agents with brain
    brain.set_agent("browser",   _browser)
    brain.set_agent("file",      _file)
    brain.set_agent("messaging", _messaging)
    brain.set_agent("vision",    _vision)
    brain.set_agent("system",    _system)
    print("OK  All agents registered")

    print("=" * 54)
    print("MEGAN Ready! -> http://localhost:8000")
    print("=" * 54)


@app.on_event("shutdown")
async def shutdown_event():
    """Save memory and clean up on shutdown."""
    print("\nMEGAN SYSTEM SHUTTING DOWN...")
    memory.save_all()
    memory.close()
    print("OK  Memory saved")
    if _browser.is_connected:
        await _browser.close()
        print("OK  Browser closed")
    print("OK  MEGAN Offline")

# ============================================================= ENTRY POINT ==

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        log_level="info",
        reload=False,
    )
