"""AI Provider - OpenRouter with robust rate limiting"""
import os
import json
import time
import base64
import io
import requests
from PIL import Image
from dotenv import load_dotenv

load_dotenv()


class AIProvider:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError(" OPENROUTER_API_KEY missing in .env")

        self.model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        
        # RATE LIMITING: Conservative for demo reliability
        self.last_call_time = 0
        self.min_delay = 2.5  # 24 calls/min max (safe for any tier)
        self.call_count = 0

        print(" AIProvider initialized (OpenRouter)")
        print(f"   Model: {self.model}")
        print(f"   Rate: {60/self.min_delay:.1f} calls/min (conservative)")

    def _rate_limit(self):
        """Enforce rate limiting"""
        elapsed = time.time() - self.last_call_time
        if elapsed < self.min_delay:
            wait = self.min_delay - elapsed
            print(f"   ⏳ Rate limit: waiting {wait:.1f}s...")
            time.sleep(wait)

    def _encode_image(self, pil_image):
        """Convert PIL image to base64 JPEG (FIXED for RGBA)"""
        # Convert RGBA/P to RGB
        if pil_image.mode in ('RGBA', 'LA', 'P'):
            rgb = Image.new('RGB', pil_image.size, (255, 255, 255))
            if pil_image.mode == 'P':
                pil_image = pil_image.convert('RGBA')
            if 'A' in pil_image.mode:
                rgb.paste(pil_image, mask=pil_image.split()[-1])
            else:
                rgb.paste(pil_image)
            pil_image = rgb
        
        # Resize if too large
        max_size = 2048
        if max(pil_image.size) > max_size:
            ratio = max_size / max(pil_image.size)
            new_size = tuple(int(dim * ratio) for dim in pil_image.size)
            pil_image = pil_image.resize(new_size, Image.LANCZOS)
        
        buffer = io.BytesIO()
        pil_image.save(buffer, format="JPEG", quality=85)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def generate_response(self, prompt, image=None, max_retries=3):
        """Generate response with retry logic"""
        
        for attempt in range(max_retries):
            try:
                self._rate_limit()
                
                # Build messages
                content = [{"type": "text", "text": prompt}]
                
                if image:
                    image_b64 = self._encode_image(image)
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}
                    })
                
                payload = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": content}],
                    "max_tokens": 600,
                    "temperature": 0.3
                }
                
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/mobile-qa-agent",
                    "X-Title": "Mobile QA Agent"
                }
                
                response = requests.post(self.url, headers=headers, json=payload, timeout=30)
                self.last_call_time = time.time()
                self.call_count += 1
                
                # Handle errors
                if response.status_code == 429:
                    if attempt < max_retries - 1:
                        wait = 10 * (2 ** attempt)  # 10s, 20s, 40s
                        print(f" Rate limit (attempt {attempt+1}), waiting {wait}s...")
                        time.sleep(wait)
                        continue
                    else:
                        raise RuntimeError("Rate limit exceeded after retries")
                
                if response.status_code != 200:
                    raise RuntimeError(f"API error {response.status_code}: {response.text}")
                
                # Parse response
                data = response.json()
                text = data["choices"][0]["message"]["content"].strip()
                
                # Clean markdown
                if text.startswith("```json"):
                    text = text[7:]
                elif text.startswith("```"):
                    text = text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()
                
                # Try to parse as JSON
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    # Return as string if not JSON
                    return text
                    
            except Exception as e:
                print(f" API error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(3)
                    continue
                else:
                    raise

        raise RuntimeError("Failed after all retries")