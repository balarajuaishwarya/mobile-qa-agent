"""
Vision Tools using OpenRouter API
Supports: Gemini, GPT-4o, Claude, and many others
"""
import os
import time
import base64
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class VisionTools:
    def __init__(self, calls_per_minute=60):
        """
        Initialize Vision Tools with OpenRouter API
        
        Set in .env:
        OPENROUTER_API_KEY=your_key_here
        OPENROUTER_MODEL=google/gemini-flash-1.5-8b (or any model from OpenRouter)
        """
        
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not found in .env file")
        
        # Get model from env or use default
        self.model = os.getenv('OPENROUTER_MODEL', 'google/gemini-flash-1.5-8b')
        
        # Initialize OpenAI client pointing to OpenRouter
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        
        # Rate limiting
        self.calls_per_minute = calls_per_minute
        self.min_interval = 60.0 / calls_per_minute
        self.last_call_time = 0
        
        print(f"✅ Vision Tools initialized with OpenRouter")
        print(f"   Model: {self.model}")
        print(f"   Rate limit: {calls_per_minute} calls/min")
    
    def _wait_for_rate_limit(self):
        """Ensure we don't exceed rate limits"""
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time
        
        if time_since_last_call < self.min_interval:
            wait_time = self.min_interval - time_since_last_call
            print(f"   ⏳ Vision rate limit: waiting {wait_time:.1f}s...")
            time.sleep(wait_time)
        
        self.last_call_time = time.time()
    
    def _encode_image_to_base64(self, pil_image):
        """Convert PIL Image to base64 string"""
        # Resize if too large
        max_size = 2048
        if max(pil_image.size) > max_size:
            ratio = max_size / max(pil_image.size)
            new_size = tuple(int(dim * ratio) for dim in pil_image.size)
            pil_image = pil_image.resize(new_size, Image.LANCZOS)
        
        # Convert to RGB if needed
        if pil_image.mode in ('RGBA', 'LA', 'P'):
            rgb_image = Image.new('RGB', pil_image.size, (255, 255, 255))
            if pil_image.mode == 'P':
                pil_image = pil_image.convert('RGBA')
            if 'A' in pil_image.mode:
                rgb_image.paste(pil_image, mask=pil_image.split()[-1])
            else:
                rgb_image.paste(pil_image)
            pil_image = rgb_image
        
        # Encode to base64
        buffered = BytesIO()
        pil_image.save(buffered, format="JPEG", quality=85)
        img_bytes = buffered.getvalue()
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
        
        print(f"   📸 Image encoded: {len(img_base64)} chars, size: {pil_image.size}")
        
        return img_base64
    
    def analyze_screen(self, image, prompt, max_retries=3):
        """Analyze screenshot with custom prompt"""
        
        # Validate image
        if image is None:
            return "Error: No image provided"
        
        if not isinstance(image, Image.Image):
            return "Error: Invalid image type (must be PIL Image)"
        
        # Encode image
        try:
            base64_image = self._encode_image_to_base64(image)
        except Exception as e:
            return f"Error encoding image: {str(e)}"
        
        for attempt in range(max_retries):
            try:
                self._wait_for_rate_limit()
                
                # Make API call through OpenRouter
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": prompt
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=1000,
                    temperature=0.3,
                    # OpenRouter specific headers
                    extra_headers={
                        "HTTP-Referer": "https://github.com/your-username/mobile-qa-agent",
                        "X-Title": "Mobile QA Agent"
                    }
                )
                
                result = response.choices[0].message.content
                
                # Check if model claims it can't see the image
                error_phrases = [
                    "unable to see",
                    "can't see",
                    "cannot view",
                    "no image",
                    "can't access"
                ]
                
                if any(phrase in result.lower() for phrase in error_phrases):
                    print(f"   ⚠️  Model claims it can't see image (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                    else:
                        return f"Error: Model unable to process image. Response: {result[:200]}"
                
                return result
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # Handle rate limit errors
                if '429' in error_msg or 'rate_limit' in error_msg or 'rate limit' in error_msg:
                    if attempt < max_retries - 1:
                        wait_time = 10 * (2 ** attempt)
                        print(f"   ⚠️  Rate limit hit (attempt {attempt + 1}/{max_retries})")
                        print(f"   Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                        continue
                    else:
                        return "Error: Rate limit exceeded after retries"
                else:
                    print(f"   ❌ Vision API error: {e}")
                    
                    if attempt < max_retries - 1:
                        print(f"   Retrying... (attempt {attempt + 2}/{max_retries})")
                        time.sleep(3)
                        continue
                    else:
                        return f"Error: {str(e)}"
        
        return "Error: Failed to analyze image after all retries"
    
    def describe_screen(self, image):
        """Get detailed description of the screen"""
        prompt = """You are analyzing a mobile app screenshot. Describe EXACTLY and SPECIFICALLY what you see.

Provide:
1. **App identification**: What app is this? What screen/page?
2. **All visible buttons**: List each button with its exact text and approximate position (top/middle/bottom, left/center/right)
3. **All text fields**: Any input fields, their labels, and content
4. **All visible text**: Every piece of text you can see
5. **Icons and images**: Describe any icons or graphics
6. **Overall layout**: Describe the layout and visual hierarchy

Be extremely detailed and specific. If you see a button, tell me its exact text."""
        
        return self.analyze_screen(image, prompt)
    
    def find_element(self, image, element_description):
        """Find specific element and return its approximate coordinates"""
        prompt = f"""Look at this mobile app screenshot very carefully.

TASK: Find this element: "{element_description}"

If you CAN see this element:
1. State: "FOUND"
2. Describe exactly what it looks like
3. Give its position as percentages from top-left corner (0-100% for both x and y)
4. Format your position as: "COORDINATES: x=XX%, y=YY%"

Example response if found:
"FOUND
The element is a blue button with white text that says 'Create New Vault'
It is located in the center of the screen
COORDINATES: x=50%, y=40%"

If you CANNOT find it:
1. State: "NOT_FOUND"
2. Explain why (not visible, different name, etc.)
3. List what similar elements you DO see

Be precise and only say FOUND if you actually see it."""
        
        return self.analyze_screen(image, prompt)
    
    def verify_text(self, image, expected_text):
        """Verify if specific text is visible on screen"""
        prompt = f"""Look at this screenshot carefully and search for this specific text:

SEARCH FOR: "{expected_text}"

Check every part of the screen including buttons, labels, titles, and body text.

Respond in exactly this format:
FOUND: Yes or No
EXACT_MATCH: Yes or No (if found)
SIMILAR_TEXT: [list any similar text you see, or "None"]
LOCATION: [where on screen - be specific]

Be thorough and accurate."""
        
        return self.analyze_screen(image, prompt)
    
    def verify_color(self, image, element_description, expected_color):
        """Verify if element has expected color"""
        prompt = f"""Look at this screenshot carefully.

STEP 1: Find this element: {element_description}
STEP 2: Check if it is this color: {expected_color}

Respond in exactly this format:
ELEMENT_FOUND: Yes or No
ACTUAL_COLOR: [describe the exact color you see - be specific like "dark blue", "light gray", "bright red", etc.]
COLOR_MATCH: Yes or No
CONFIDENCE: High, Medium, or Low

Be accurate about colors. Don't guess."""
        
        return self.analyze_screen(image, prompt)
    
    def check_element_exists(self, image, element_description):
        """Simple check if element exists"""
        prompt = f"""Look at this screenshot.

Question: Does this element exist on the screen? "{element_description}"

Respond with exactly 2 lines:
Line 1: "EXISTS" or "NOT_EXISTS"
Line 2: One sentence explaining what you see (or don't see)

Be honest - only say EXISTS if you clearly see it."""
        
        return self.analyze_screen(image, prompt)