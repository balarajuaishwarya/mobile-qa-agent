import time
import json
from typing import Optional, Union, Dict
from PIL import Image
from openai import OpenAI  
import config

class AIProvider:
    def __init__(self):
        """Initialize OpenRouter with proper configuration"""
        if not config.OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY not set in config.")
        
        # Initialize the OpenAI client pointing to OpenRouter
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=config.OPENROUTER_API_KEY,
        )
        
        self.model_id = config.OPENROUTER_MODEL  
        self.call_count = 0
        self.last_call_time = 0
        
        print(f" OpenRouter Provider initialized: {self.model_id}")

    def generate_response(
        self, 
        prompt: str, 
        image: Optional[Image.Image] = None,
        max_retries: int = 3
    ) -> Union[Dict, str]:
        """Generate response from OpenRouter using OpenAI-compatible client"""
        for attempt in range(max_retries):
            try:
                # OpenRouter supports images via standard multimodal format (base64 or URL)
                messages = [{"role": "user", "content": prompt}]
                
                # Note: Multimodal handling for images requires converting PIL to base64
                if image:
                    # Logic to attach image would go here as an image_url content part
                    pass

                response = self.client.chat.completions.create(
                    model=self.model_id,
                    messages=messages,
                    temperature=config.TEMPERATURE,
                )

                self.call_count += 1
                text = response.choices[0].message.content.strip()
                return self._parse_json_response(text)

            except Exception as e:
                print(f" OpenRouter Error: {e} (attempt {attempt + 1})")
                time.sleep(2)
        return "Failed after retries."

    def _parse_json_response(self, text: str):
        # Cleans and extracts JSON as defined in your earlier VisionAnalyzer code
        try:
            start = text.find('{')
            end = text.rfind('}')
            return json.loads(text[start:end + 1]) if start != -1 else text
        except:
            return text

# import time
# import json
# from typing import Optional, Union, Dict
# from PIL import Image
# from google import genai
# from google.genai import types
# from openai import OpenAI
# import config

# class AIProvider:
    
#     def __init__(self):
#         """Initialize Gemini with proper configuration"""
#         if not config.GEMINI_API_KEY:
#             raise ValueError(
#                 "GEMINI_API_KEY not set. Get your key from: "
#                 "https://aistudio.google.com/app/apikey"
#             )
        
#         self.client = genai.Client(api_key=config.GEMINI_API_KEY)
#         self.model_id = config.GEMINI_MODEL  
        
#         # Stats & Rate Limiting
#         self.call_count = 0
#         self.last_call_time = 0
#         self.min_delay = 1.0  
        
#         print(f" Gemini Provider initialized: {self.model_id}")

#     def _rate_limit(self):
#         """Enforce minimum delay between API calls"""
#         if config.RATE_LIMIT_ENABLED:
#             elapsed = time.time() - self.last_call_time
#             if elapsed < self.min_delay:
#                 time.sleep(self.min_delay - elapsed)

#     def generate_response(
#         self, 
#         prompt: str, 
#         image: Optional[Image.Image] = None,
#         max_retries: int = None
#     ) -> Union[Dict, str]:
#         """
#         Generate response from Gemini with native multimodal support
#         """
#         max_retries = max_retries or config.MAX_RETRIES
        
#         for attempt in range(max_retries):
#             try:
#                 self._rate_limit()
                
#                 # Build content list (supports text and images)
#                 contents = [prompt]
#                 if image:
#                     contents.append(image)

#                 response = self.client.models.generate_content(
#                     model=self.model_id,
#                     contents=contents,
#                     config=types.GenerateContentConfig(
#                         temperature=config.TEMPERATURE,
#                         max_output_tokens=config.MAX_TOKENS,
#                     )
#                 )

#                 self.last_call_time = time.time()
#                 self.call_count += 1
                
#                 text = response.text.strip()
                
#                 # Attempt to parse JSON if the prompt requested it
#                 return self._parse_json_response(text)

#             except Exception as e:
#                 print(f"  Gemini Error: {e} (attempt {attempt + 1}/{max_retries})")
#                 if attempt < max_retries - 1:
#                     time.sleep(config.RETRY_DELAY * (attempt + 1))
#                     continue
#                 return self._fallback_response(str(e))
        
#         return self._fallback_response("Max retries exceeded")

#     def _parse_json_response(self, text: str) -> Union[Dict, str]:
#         """Robustly extract JSON from Gemini's response"""
#         # Remove markdown wrappers if present
#         if "```json" in text:
#             text = text.split("```json")[1].split("```")[0].strip()
#         elif "```" in text:
#             text = text.split("```")[1].split("```")[0].strip()
            
#         try:
#             # Find first { and last } to isolate JSON
#             start = text.find('{')
#             end = text.rfind('}')
#             if start != -1 and end != -1:
#                 return json.loads(text[start:end + 1])
#             return json.loads(text)
#         except:
#             return text

    def _fallback_response(self, reason: str) -> Dict:
        return {
            "action_type": "wait",
            "parameters": {"seconds": 2},
            "reasoning": f"Gemini failure: {reason}"
        }

    def ask(self, prompt: str, image: Optional[Image.Image] = None) -> Union[Dict, str]:
        return self.generate_response(prompt, image)

class AIProviderFactory:
    @staticmethod
    def create():
        return AIProvider()