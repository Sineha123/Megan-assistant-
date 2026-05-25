"""
MEGAN Audio Processor
- Speech-to-Text: Google SpeechRecognition (offline/online)
- Text-to-Speech: edge-tts with Microsoft Neural FEMALE voices
  (en-US-AriaNeural by default -- warm, natural, assistant-like)

edge-tts is FREE and runs without an API key.
It uses Microsoft Edge's neural TTS engine online.
"""

import asyncio
import base64
import os
import io
import tempfile
from typing import Optional

from core.config import VOICE_NAME, VOICE_LANGUAGE, VOICE_RATE, VOICE_PITCH, STT_LANGUAGE


# ─── Available Female Voices ─────────────────────────────────────────────────────
# Hindi / Hinglish voices
FEMALE_VOICES = {
    # ── Hindi (India) ── recommended for Hinglish
    "swara":   "hi-IN-SwaraNeural",    # Warm Hindi female (default MEGAN voice)
    "ananya":  "hi-IN-AnanyaNeural",   # Hindi female, slightly younger
    # ── Indian English (handles Hinglish well)
    "neerja":  "en-IN-NeerjaNeural",   # Indian-English female, natural code-switch
    # ── US English (fallback)
    "aria":    "en-US-AriaNeural",
    "jenny":   "en-US-JennyNeural",
    # ── British/Australian
    "sonia":   "en-GB-SoniaNeural",
    "natasha": "en-AU-NatashaNeural",
}


class AudioProcessor:
    """
    MEGAN's audio I/O module.

    TTS: edge-tts (Microsoft Neural TTS, female voices, no API key)
    STT: SpeechRecognition with Google Web Speech API
    """

    def __init__(self):
        self._recognizer  = None
        self._edgetts_ok  = False
        self._stt_ok      = False
        self._ready       = False
        self.voice_name   = VOICE_NAME
        self.voice_rate   = VOICE_RATE
        self.voice_pitch  = VOICE_PITCH
        self.stt_language = STT_LANGUAGE

    # ─── Initialization ───────────────────────────────────────────────────────

    def initialize(self):
        """Set up TTS and STT modules."""
        print(f"[AUDIO] Initializing Audio Processor...")
        print(f"[AUDIO] Voice    : {self.voice_name}")
        print(f"[AUDIO] STT lang : {self.stt_language}")
        self._init_tts()
        self._init_stt()
        self._ready = True
        print("[AUDIO] Audio Processor ready")

    def _init_tts(self):
        """Check edge-tts availability."""
        try:
            import edge_tts  # noqa
            self._edgetts_ok = True
            print("[AUDIO] edge-tts ready (female neural voice)")
        except ImportError:
            print("[AUDIO] WARN: edge-tts not installed -- run: pip install edge-tts")
            print("[AUDIO] TTS will be disabled until edge-tts is installed")

    def _init_stt(self):
        """Check SpeechRecognition availability."""
        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold         = 300
            self._recognizer.dynamic_energy_threshold = True
            self._stt_ok = True
            print("[AUDIO] SpeechRecognition ready (STT)")
        except ImportError:
            print("[AUDIO] WARN: SpeechRecognition not installed -- STT disabled")

    # ─── Text-to-Speech (edge-tts female neural voice) ───────────────────────

    async def synthesize(self, text: str) -> str:
        """
        Convert text to speech using edge-tts (Microsoft Neural TTS).
        Returns base64-encoded MP3 audio.

        Args:
            text: Text for MEGAN to speak

        Returns:
            Base64-encoded MP3 string, or "" on failure
        """
        if not self._edgetts_ok:
            print(f"[AUDIO] TTS unavailable -- would speak: {text[:60]}")
            return ""

        try:
            import edge_tts

            communicate = edge_tts.Communicate(
                text=text,
                voice=self.voice_name,
                rate=self.voice_rate,
                pitch=self.voice_pitch,
            )

            # Stream audio to bytes
            audio_chunks = []
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_chunks.append(chunk["data"])

            if not audio_chunks:
                print("[AUDIO] WARN: edge-tts returned no audio")
                return ""

            audio_bytes = b"".join(audio_chunks)
            encoded     = base64.b64encode(audio_bytes).decode("utf-8")
            print(f"[AUDIO] Synthesized {len(text)} chars -> {len(audio_bytes)} bytes MP3")
            return encoded

        except Exception as e:
            print(f"[ERROR] edge-tts synthesis failed: {str(e)}")
            return ""

    async def speak_aloud(self, text: str):
        """
        Speak text directly through the system speakers (for local use).
        Saves to a temp file and plays it via edge-tts + system audio.
        """
        if not self._edgetts_ok:
            print(f"[MEGAN speaks]: {text}")
            return

        try:
            import edge_tts

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_path = tmp.name

            communicate = edge_tts.Communicate(
                text=text,
                voice=self.voice_name,
                rate=self.voice_rate,
                pitch=self.voice_pitch,
            )
            await communicate.save(tmp_path)

            # Play on Windows / macOS / Linux
            import sys
            if sys.platform == "win32":
                os.system(f'start /min "" "{tmp_path}"')
            elif sys.platform == "darwin":
                os.system(f'afplay "{tmp_path}"')
            else:
                os.system(f'mpg123 "{tmp_path}" 2>/dev/null || ffplay -nodisp -autoexit "{tmp_path}" 2>/dev/null')

            # Clean up after a short delay
            await asyncio.sleep(0.5)
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

        except Exception as e:
            print(f"[ERROR] speak_aloud failed: {str(e)}")

    # ─── Speech-to-Text ───────────────────────────────────────────────────────

    async def transcribe(self, audio_base64: str, language: str = "en-US") -> str:
        """
        Convert base64-encoded WAV audio to text using Google Speech API.

        Args:
            audio_base64: Base64-encoded WAV audio
            language:     BCP-47 language code

        Returns:
            Transcribed text string
        """
        return await asyncio.to_thread(self._transcribe_sync, audio_base64, language)

    def _transcribe_sync(self, audio_base64: str, language: str) -> str:
        """Synchronous STT (runs in thread pool)."""
        if self._recognizer is None or not self._stt_ok:
            return "[STT unavailable -- SpeechRecognition not installed]"

        try:
            import speech_recognition as sr

            audio_bytes = base64.b64decode(audio_base64)

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            try:
                with sr.AudioFile(tmp_path) as source:
                    audio_data = self._recognizer.record(source)

                # Use the configured STT language (hi-IN for Hinglish)
                text = self._recognizer.recognize_google(
                    audio_data, language=self.stt_language
                )
                print(f"[AUDIO] Transcribed [{self.stt_language}]: {text}")
                return text

            finally:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

        except Exception as e:
            print(f"[ERROR] STT transcription failed: {str(e)}")
            return f"[Could not transcribe audio: {str(e)}]"

    # ─── Voice Listing ────────────────────────────────────────────────────────

    @staticmethod
    async def list_female_voices() -> list:
        """Return all available female voices from edge-tts (Hindi + Indian English first)."""
        try:
            import edge_tts
            voices = await edge_tts.list_voices()
            # Prioritise Hindi India and Indian English
            preferred_locales = ("hi-IN", "en-IN")
            preferred = [
                v for v in voices
                if v.get("Gender") == "Female" and
                   any(v.get("Locale", "").startswith(loc) for loc in preferred_locales)
            ]
            other_english = [
                v for v in voices
                if v.get("Gender") == "Female" and
                   v.get("Locale", "").startswith("en-") and
                   not any(v.get("Locale", "").startswith(loc) for loc in preferred_locales)
            ]
            return preferred + other_english
        except Exception as e:
            print(f"[ERROR] Could not list voices: {e}")
            return []

    # ─── Properties ───────────────────────────────────────────────────────────

    @property
    def is_ready(self) -> bool:
        return self._ready

    @property
    def tts_available(self) -> bool:
        return self._edgetts_ok

    @property
    def stt_available(self) -> bool:
        return self._stt_ok


# ─── Standalone Test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    async def test():
        audio = AudioProcessor()
        audio.initialize()
        print(f"Voice: {audio.voice_name}")
        print(f"STT:   {audio.stt_language}")
        print("Speaking Hinglish test phrase...")
        await audio.speak_aloud(
            "Namaste! Main MEGAN hun, aapki personal AI assistant. "
            "Aaj main aapki kya help kar sakti hun?"
        )
        print("Done.")

    asyncio.run(test())
