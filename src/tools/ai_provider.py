"""
AI Provider - OpenRouter Integration
Supports both Gemini and OpenRouter with unified interface
"""

import time
import json
import io
import base64
import requests
from typing import Optional, Union, Dict
from PIL import Image
import config


class AIProvider:
    """
    AI Provider for accessing multiple models
    
    """
    
    def __init__(self):
        """Initialize OpenRouter with proper configuration"""
        if not config.OPENROUTER_API_KEY:
            raise ValueError(
                "OPENROUTER_API_KEY not set. Get free key from: "
                "https://openrouter.ai/keys"
            )
        
        self.api_key = config.OPENROUTER_API_KEY
        self.model = config.OPENROUTER_MODEL
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        
        # Rate limiting
        self.last_call_time = 0
        self.call_count = 0
        self.min_delay = 2.0  # Slightly longer for OpenRouter
        
        print(f" OpenRouter Provider initialized: {self.model}")
    
    def _rate_limit(self):
        """Enforce minimum delay between API calls"""
        if config.RATE_LIMIT_ENABLED:
            elapsed = time.time() - self.last_call_time
            if elapsed < self.min_delay:
                time.sleep(self.min_delay - elapsed)
    
    def _prepare_image(self, image: Image.Image) -> str:
        """
        Prepare image for OpenRouter API
        Convert to base64 JPEG
        """
        # Convert RGBA to RGB
        if image.mode in ('RGBA', 'LA', 'P'):
            rgb_image = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            if image.mode == 'RGBA':
                rgb_image.paste(image, mask=image.split()[-1])
            else:
                rgb_image.paste(image)
            image = rgb_image
        
        # Optimize if needed
        if config.COMPRESS_IMAGES:
            width, height = image.size
            if width > config.MAX_IMAGE_DIMENSION or height > config.MAX_IMAGE_DIMENSION:
                if width > height:
                    new_width = config.MAX_IMAGE_DIMENSION
                    new_height = int(height * (config.MAX_IMAGE_DIMENSION / width))
                else:
                    new_height = config.MAX_IMAGE_DIMENSION
                    new_width = int(width * (config.MAX_IMAGE_DIMENSION / height))
                image = image.resize((new_width, new_height), Image.LANCZOS)
        
        # Convert to base64
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=config.IMAGE_QUALITY)
        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        return image_base64
    
    def generate_response(
        self, 
        prompt: str, 
        image: Optional[Image.Image] = None,
        max_retries: int = None
    ) -> Union[Dict, str]:
        """
        Generate response from OpenRouter with automatic JSON parsing
        
        Args:
            prompt: Text prompt for the model
            image: Optional PIL Image for vision tasks
            max_retries: Number of retry attempts (default from config)
            
        Returns:
            Parsed JSON dict or raw string if parsing fails
        """
        max_retries = max_retries or config.MAX_RETRIES
        
        for attempt in range(max_retries):
            try:
                self._rate_limit()
                
                # Build message content
                content = [{"type": "text", "text": prompt}]
                
                if image:
                    image_b64 = self._prepare_image(image)
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}"
                        }
                    })
                
                # Prepare payload
                payload = {
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": content
                        }
                    ],
                    "temperature": config.TEMPERATURE,
                    "max_tokens": config.MAX_TOKENS,
                }
                
                # Prepare headers
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/mobile-qa-agent",
                    "X-Title": "Mobile QA Agent"
                }
                
                # Make request
                response = requests.post(
                    self.url,
                    headers=headers,
                    json=payload,
                    timeout=config.TIMEOUT
                )
                
                self.last_call_time = time.time()
                self.call_count += 1
                
                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 5))
                    print(f"⚠️  Rate limited. Waiting {retry_after}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_after)
                    continue
                
                # Handle errors
                if response.status_code != 200:
                    error_msg = f"API Error {response.status_code}: {response.text}"
                    print(f"⚠️  {error_msg}")
                    
                    if attempt < max_retries - 1:
                        wait_time = config.RETRY_DELAY * (attempt + 1)
                        print(f"   Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        # Return fallback on final attempt
                        return self._fallback_response(error_msg)
                
                # Parse response
                data = response.json()
                
                # Extract text from response
                if "choices" in data and len(data["choices"]) > 0:
                    message = data["choices"][0].get("message", {})
                    text = message.get("content", "").strip()
                    
                    # Try to parse as JSON
                    return self._parse_json_response(text)
                else:
                    print("⚠️  Unexpected response format")
                    if attempt < max_retries - 1:
                        time.sleep(config.RETRY_DELAY)
                        continue
                    return self._fallback_response("Invalid response format")
                
            except requests.exceptions.Timeout:
                print(f"⚠️  Request timeout (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(config.RETRY_DELAY * (attempt + 1))
                    continue
                return self._fallback_response("Request timeout")
                
            except requests.exceptions.ConnectionError:
                print(f"⚠️  Connection error (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(config.RETRY_DELAY * (attempt + 1))
                    continue
                return self._fallback_response("Connection error")
                
            except Exception as e:
                print(f"⚠️  Unexpected error: {e} (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(config.RETRY_DELAY * (attempt + 1))
                    continue
                return self._fallback_response(f"Unexpected error: {str(e)}")
        
        # If all retries failed
        return self._fallback_response("Max retries exceeded")
    
    def _parse_json_response(self, text: str) -> Union[Dict, str]:
        """
        Parse JSON from model response with robust cleaning
        
        Handles common issues:
        - Markdown code blocks (```json)
        - Extra whitespace
        - Conversational text before/after JSON
        """
        # Remove markdown formatting
        if "```json" in text:
            parts = text.split("```json")
            if len(parts) > 1:
                text = parts[1].split("```")[0].strip()
        elif "```" in text:
            # Generic code block
            parts = text.split("```")
            if len(parts) >= 3:
                text = parts[1].strip()
        
        # Try to extract JSON from mixed content
        text = text.strip()
        
        # Find first { and last }
        start = text.find('{')
        end = text.rfind('}')
        
        if start != -1 and end != -1:
            json_str = text[start:end + 1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        # Try parsing entire text
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Return as string if not valid JSON
            return text
    
    def _fallback_response(self, reason: str) -> Dict:
        """Return safe fallback response when API fails"""
        return {
            "action_type": "wait",
            "parameters": {"seconds": 2},
            "reasoning": f"API error: {reason}"
        }
    
    def ask(self, prompt: str, image: Optional[Image.Image] = None) -> Union[Dict, str]:
        """Alias for generate_response for compatibility"""
        return self.generate_response(prompt, image)
    
    def get_stats(self) -> Dict:
        """Get usage statistics"""
        return {
            "total_calls": self.call_count,
            "model": self.model,
            "provider": "openrouter",
            "rate_limit_enabled": config.RATE_LIMIT_ENABLED
        }
    

class AIProviderFactory:
    """Factory to create AI provider based on config"""
    
    @staticmethod
    def create():
        """Create AI provider instance based on configuration"""
        if config.AI_PROVIDER == "gemini":
            return AIProvider()
        elif config.AI_PROVIDER == "openrouter":
            return AIProvider()
        else:
            raise ValueError(f"Unsupported AI provider: {config.AI_PROVIDER}")

