"""
Vision Agent - Screen capture and OCR
Uses Pillow for screenshots and pytesseract for OCR
"""

import os
import base64
import io
from typing import Dict, Optional
from datetime import datetime


class VisionAgent:
    """
    Vision Module for MEGAN.

    Capabilities:
    - Take full-screen or region screenshots
    - Read text from screen (OCR via pytesseract)
    - Describe screen contents (using Claude Vision API if available)
    - Save screenshots to disk

    Requirements:
    - Pillow         (pip install Pillow)
    - pytesseract    (pip install pytesseract + install Tesseract OCR binary)
    - anthropic      (optional, for AI image description)
    """

    def __init__(self, brain=None):
        """
        Args:
            brain: Optional MEGANBrain instance (used for AI image description)
        """
        self._brain   = brain
        self._pil_ok  = False
        self._ocr_ok  = False
        self._init_modules()

    def _init_modules(self):
        """Lazy-check for required libraries."""
        try:
            import PIL.ImageGrab  # noqa
            self._pil_ok = True
        except ImportError:
            print("[VISION] WARN:  Pillow not installed -- screenshots disabled")

        try:
            import pytesseract  # noqa
            self._ocr_ok = True
        except ImportError:
            print("[VISION] WARN:  pytesseract not installed -- OCR disabled")

    # ─── Screenshots ─────────────────────────────────────────────────────────

    def take_screenshot(
        self,
        output_path: str = "screen.png",
        region: Optional[tuple] = None,
    ) -> Dict:
        """
        Capture the full screen (or a region) and save to file.

        Args:
            output_path: Where to save the PNG
            region:      Optional (left, top, right, bottom) tuple

        Returns:
            {"status": ..., "path": ..., "width": ..., "height": ...}
        """
        if not self._pil_ok:
            return {"error": "Pillow not installed"}

        try:
            from PIL import ImageGrab

            screenshot = ImageGrab.grab(bbox=region)
            screenshot.save(output_path)

            print(f"[VISION] Screenshot saved: {output_path} {screenshot.size}")
            return {
                "status": "success",
                "path":   output_path,
                "width":  screenshot.width,
                "height": screenshot.height,
            }

        except Exception as e:
            print(f"[ERROR] Screenshot failed: {str(e)}")
            return {"error": str(e)}

    def get_screenshot_base64(self, region: Optional[tuple] = None) -> str:
        """Return current screen as a base64 PNG string."""
        if not self._pil_ok:
            return ""
        try:
            from PIL import ImageGrab
            screenshot = ImageGrab.grab(bbox=region)
            buf = io.BytesIO()
            screenshot.save(buf, format="PNG")
            return base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception as e:
            print(f"[ERROR] Screenshot base64 failed: {str(e)}")
            return ""

    # ─── OCR ─────────────────────────────────────────────────────────────────

    def read_screen_text(
        self,
        region: Optional[tuple] = None,
        lang: str = "eng",
    ) -> Dict:
        """
        Extract all visible text from the screen using OCR.

        Args:
            region: Optional (left, top, right, bottom) bounding box
            lang:   Tesseract language code (default 'eng')

        Returns:
            {"status": ..., "text": str}
        """
        if not self._pil_ok:
            return {"error": "Pillow not installed"}
        if not self._ocr_ok:
            return {"error": "pytesseract not installed"}

        try:
            from PIL import ImageGrab
            import pytesseract

            screenshot = ImageGrab.grab(bbox=region)
            text = pytesseract.image_to_string(screenshot, lang=lang)
            print(f"[VISION] OCR extracted {len(text)} characters")
            return {"status": "success", "text": text.strip()}

        except Exception as e:
            print(f"[ERROR] OCR failed: {str(e)}")
            return {"error": str(e)}

    def read_image_text(self, image_path: str, lang: str = "eng") -> Dict:
        """Run OCR on an image file."""
        if not self._ocr_ok:
            return {"error": "pytesseract not installed"}
        try:
            from PIL import Image
            import pytesseract

            img  = Image.open(image_path)
            text = pytesseract.image_to_string(img, lang=lang)
            return {"status": "success", "file": image_path, "text": text.strip()}

        except Exception as e:
            print(f"[ERROR] Image OCR failed: {str(e)}")
            return {"error": str(e)}

    # ─── AI Description ──────────────────────────────────────────────────────

    def describe_screen(self) -> Dict:
        """
        Send the current screenshot to Gemini Vision for a natural-language description.
        Requires GEMINI_API_KEY and the brain to be configured.
        """
        img_b64 = self.get_screenshot_base64()
        if not img_b64:
            return {"error": "Could not capture screenshot"}

        if self._brain is None or self._brain._client is None:
            return {
                "status":  "partial",
                "message": "AI description unavailable (no API key). Use OCR for text.",
            }

        try:
            from google.genai import types
            import base64 as _b64

            img_bytes = _b64.b64decode(img_b64)

            response = self._brain._client.models.generate_content(
                model=self._brain.model,
                contents=[
                    types.Content(parts=[
                        types.Part(
                            inline_data=types.Blob(
                                mime_type="image/png",
                                data=img_bytes,
                            )
                        ),
                        types.Part(text="Describe what you see on this screen in 2-3 sentences."),
                    ])
                ],
                config=types.GenerateContentConfig(max_output_tokens=256),
            )
            description = response.text
            print(f"[VISION] AI description: {description[:80]}")
            return {"status": "success", "description": description}

        except Exception as e:
            print(f"[ERROR] AI description failed: {str(e)}")
            return {"error": str(e)}


    # ─── Helpers ─────────────────────────────────────────────────────────────

    @property
    def is_ready(self) -> bool:
        return self._pil_ok


# ─── Standalone Test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    agent = VisionAgent()
    result = agent.take_screenshot("test_screenshot.png")
    print(result)

    if result.get("status") == "success":
        ocr = agent.read_screen_text()
        print(f"Screen text preview: {ocr.get('text', '')[:200]}")
