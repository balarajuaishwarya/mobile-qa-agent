"""
AI provider manager using OpenRouter with Google Gemini models only.

"""

import os
import base64
from typing import Optional

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


class ProviderResponse:
    def __init__(self, text: str):
        self.text = text


class AIProviderManager:
    def __init__(self):
        if not OpenAI:
            raise RuntimeError("openai package is not installed")

        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.model = os.getenv("OPENROUTER_MODEL")

        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is not set")

        if not self.model:
            raise ValueError(
                "OPENROUTER_MODEL must be set (e.g., google/gemini-2.0-flash)"
            )

        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://openrouter.ai/api/v1",
        )

    def _encode_image(self, image) -> Optional[str]:
        """Accept bytes or PIL.Image and return base64 JPEG string."""
        try:
            from PIL import Image
            from io import BytesIO
        except Exception:
            Image = None

        if isinstance(image, (bytes, bytearray)):
            return base64.b64encode(image).decode("utf-8")

        if Image and isinstance(image, Image.Image):
            buf = BytesIO()
            image.save(buf, format="JPEG", quality=85)
            return base64.b64encode(buf.getvalue()).decode("utf-8")

        return None

    def _build_messages(self, prompt: str, image=None):
        """Build OpenAI-compatible messages with optional image."""
        if image is None:
            return [{"role": "user", "content": prompt}]

        img_b64 = self._encode_image(image)
        if not img_b64:
            return [{"role": "user", "content": prompt}]

        return [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{img_b64}"
                        },
                    },
                ],
            }
        ]

    def _extract_text(self, response) -> str:
        """Safely extract text from OpenRouter response."""
        try:
            return response.choices[0].message.content or ""
        except Exception:
            return ""

    def generate_content(
        self,
        prompt: str,
        image=None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> ProviderResponse:
        messages = self._build_messages(prompt, image)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return ProviderResponse(self._extract_text(response))

        except Exception as e:
            return ProviderResponse(
                f"MOCK_RESPONSE: OpenRouter Gemini call failed: {e}"
            )
