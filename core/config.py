"""
MEGAN Configuration Module
Loads environment variables and exposes all configuration constants
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_root = Path(__file__).parent.parent
load_dotenv(_root / ".env")

# ─── AI / Gemini ──────────────────────────────────────────────────────────────
GEMINI_API_KEY: str  = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str    = os.getenv("GEMINI_MODEL",   "gemini-2.0-flash")
MAX_TOKENS: int      = int(os.getenv("MAX_TOKENS",  "2048"))

# ─── Server ───────────────────────────────────────────────────────────────────
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8000"))

# ─── Database ────────────────────────────────────────────────────────────────
DB_PATH: str = os.getenv("DATABASE_PATH", str(_root / "megan_memory.db"))

# ─── Browser ─────────────────────────────────────────────────────────────────
BROWSER_PORT: int = int(os.getenv("BROWSER_PORT", "9222"))

# ─── Voice (Hindi female neural voice — edge-tts) ────────────────────────────
VOICE_NAME: str     = os.getenv("VOICE_NAME",     "hi-IN-SwaraNeural")
VOICE_LANGUAGE: str = os.getenv("VOICE_LANGUAGE", "hi-IN")
VOICE_RATE: str     = os.getenv("VOICE_RATE",     "+0%")
VOICE_PITCH: str    = os.getenv("VOICE_PITCH",    "+5Hz")

# ─── Language / Personality ──────────────────────────────────────────────────
# 'hinglish' = Roman Hindi + English mixed responses (default)
# 'english'  = English only
RESPONSE_LANGUAGE: str = os.getenv("RESPONSE_LANGUAGE", "hinglish")
STT_LANGUAGE: str      = os.getenv("STT_LANGUAGE",      "hi-IN")

# ─── Validation ──────────────────────────────────────────────────────────────
def validate_config() -> list:
    """Return list of missing critical config keys."""
    issues = []
    if not GEMINI_API_KEY:
        issues.append("GEMINI_API_KEY is not set -- brain will use echo fallback mode")
    return issues
