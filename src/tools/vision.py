"""
Vision Tools using AIProviderManager
This module wraps image pre-processing and delegates LLM calls to `tools.ai_provider.AIProviderManager`.
"""
import os
import time
import base64
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv

from tools.ai_provider import AIProviderManager

load_dotenv()


class VisionTools:
    def __init__(self, calls_per_minute=60):
        """Initialize VisionTools and the AI provider manager."""

        self.provider = AIProviderManager()

        # Rate limiting for provider calls
        self.calls_per_minute = calls_per_minute
        self.min_interval = 60.0 / calls_per_minute
        self.last_call_time = 0

        print("Vision Tools initialized (using AIProviderManager)")

    def _wait_for_rate_limit(self):
        now = time.time()
        elapsed = now - self.last_call_time
        if elapsed < self.min_interval:
            to_wait = self.min_interval - elapsed
            print(f"   Vision rate limit: waiting {to_wait:.1f}s...")
            time.sleep(to_wait)
        self.last_call_time = time.time()

    def _encode_image_to_base64(self, pil_image):
        """Encode a PIL image to a base64 JPEG data URI (returns base64 string)."""
        max_size = 2048
        if max(pil_image.size) > max_size:
            ratio = max_size / max(pil_image.size)
            new_size = tuple(int(dim * ratio) for dim in pil_image.size)
            pil_image = pil_image.resize(new_size, Image.LANCZOS)

        if pil_image.mode in ("RGBA", "LA", "P"):
            rgb = Image.new("RGB", pil_image.size, (255, 255, 255))
            if pil_image.mode == "P":
                pil_image = pil_image.convert("RGBA")
            if "A" in pil_image.mode:
                rgb.paste(pil_image, mask=pil_image.split()[-1])
            else:
                rgb.paste(pil_image)
            pil_image = rgb

        buf = BytesIO()
        pil_image.save(buf, format="JPEG", quality=85)
        img_bytes = buf.getvalue()
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")
        print(f"   Image encoded: {len(img_b64)} chars, size: {pil_image.size}")
        return img_b64

    def analyze_screen(self, image, prompt, max_retries=3):
        """Analyze screenshot with a prompt. Delegates to AIProviderManager.

        The image is encoded as base64 and appended to the prompt so
        providers without native image attachments can still receive it.
        """
        if image is None:
            return "Error: No image provided"
        if not isinstance(image, Image.Image):
            return "Error: Invalid image type (must be PIL Image)"

        try:
            img_b64 = self._encode_image_to_base64(image)
        except Exception as e:
            return f"Error encoding image: {e}"

        full_prompt = prompt + "\n\nImage (base64): data:image/jpeg;base64," + img_b64

        for attempt in range(max_retries):
            try:
                self._wait_for_rate_limit()
                resp = self.provider.generate_content(full_prompt)
                return resp.text
            except Exception as e:
                err = str(e).lower()
                if ("429" in err or "rate_limit" in err or "rate limit" in err) and attempt < max_retries - 1:
                    wait = 5 * (2 ** attempt)
                    print(f"   Rate limit hit (attempt {attempt + 1}/{max_retries}), waiting {wait}s...")
                    time.sleep(wait)
                    continue
                if attempt < max_retries - 1:
                    print(f"   Vision provider error: {e}. Retrying...")
                    time.sleep(2)
                    continue
                return f"Error: {e}"

        return "Error: Failed to analyze image after retries"

    def describe_screen(self, image):
        prompt = """You are analyzing a mobile app screenshot. Describe EXACTLY and SPECIFICALLY what you see.

Provide:
1. App identification: What app and which screen/page
2. All visible buttons: exact text and approximate position
3. All input fields: labels and content
4. All visible text
5. Icons and images
6. Overall layout and hierarchy
Be very specific."""
        return self.analyze_screen(image, prompt)

    def find_element(self, image, element_description):
        prompt = f"""Look at this mobile app screenshot and find this element: {element_description}
If found, respond with: FOUND\nDescription...\nCOORDINATES: x=XX%, y=YY%\nIf not found, respond with NOT_FOUND and a short reason."""
        return self.analyze_screen(image, prompt)

    def verify_text(self, image, expected_text):
        prompt = f"""Search for this exact text on the screen: {expected_text}\nRespond with FOUND: Yes/No, EXACT_MATCH: Yes/No, LOCATION: short description."""
        return self.analyze_screen(image, prompt)

    def verify_color(self, image, element_description, expected_color):
        prompt = f"""Find the element: {element_description} and verify if its color matches {expected_color}. Respond: ELEMENT_FOUND: Yes/No, COLOR_MATCH: Yes/No, CONFIDENCE: High/Medium/Low."""
        return self.analyze_screen(image, prompt)

    def check_element_exists(self, image, element_description):
        prompt = f"""Does this element exist on the screen: {element_description}? Reply: EXISTS or NOT_EXISTS and one-line explanation."""
        return self.analyze_screen(image, prompt)