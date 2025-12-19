import os
import time
import json
import base64
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv

from tools.ai_provider import AIProviderManager

load_dotenv()


class PlannerAgent:
    def __init__(self, calls_per_minute=60):
        """Initialize Planner and AI provider manager."""

        # Use the central AIProviderManager (prefers OpenAI when configured)
        self.provider = AIProviderManager()

        # Keep model config for informational/debug uses; provider manages actual model selection
        self.model = os.getenv('OPENROUTER_MODEL') or os.getenv('OPENAI_MODEL')
        
        # Rate limiting
        self.calls_per_minute = calls_per_minute
        self.min_interval = 60.0 / calls_per_minute
        self.last_call_time = 0
        
        print(f"Planner initialized with OpenRouter")
        print(f"   Model: {self.model}")
        print(f"   Rate limit: {calls_per_minute} calls/min")
    
    def _wait_for_rate_limit(self):
        """Ensure we don't exceed rate limits"""
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time
        
        if time_since_last_call < self.min_interval:
            wait_time = self.min_interval - time_since_last_call
            print(f"   Planner rate limit: waiting {wait_time:.1f}s...")
            time.sleep(wait_time)
        
        self.last_call_time = time.time()
    
    def _encode_image_to_base64(self, pil_image):
        """Convert PIL Image to base64 string"""
        max_size = 2048
        if max(pil_image.size) > max_size:
            ratio = max_size / max(pil_image.size)
            new_size = tuple(int(dim * ratio) for dim in pil_image.size)
            pil_image = pil_image.resize(new_size, Image.LANCZOS)
        
        if pil_image.mode in ('RGBA', 'LA', 'P'):
            rgb_image = Image.new('RGB', pil_image.size, (255, 255, 255))
            if pil_image.mode == 'P':
                pil_image = pil_image.convert('RGBA')
            if 'A' in pil_image.mode:
                rgb_image.paste(pil_image, mask=pil_image.split()[-1])
            else:
                rgb_image.paste(pil_image)
            pil_image = rgb_image
        
        buffered = BytesIO()
        pil_image.save(buffered, format="JPEG", quality=85)
        img_bytes = buffered.getvalue()
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
        
        return img_base64
    
    def plan_next_action(self, test_case, current_state, action_history, screenshot, max_retries=3):
        """Decide the next action based on current state and goal"""
        
        recent_actions = action_history[-3:] if len(action_history) > 3 else action_history
        history_summary = "\n".join([
            f"Step {a['step']}: {a['action']['action_type']} - {a['action'].get('reasoning', 'N/A')}"
            for a in recent_actions
        ])
        
        system_prompt = """You are a mobile app testing expert AI. Analyze screenshots and decide the NEXT SINGLE ACTION.

AVAILABLE ACTIONS:
1. tap: {"action_type": "tap", "parameters": {"x_percent": 50, "y_percent": 30}, "reasoning": "..."}
2. type: {"action_type": "type", "parameters": {"text": "InternVault"}, "reasoning": "..."}
3. press_key: {"action_type": "press_key", "parameters": {"key": "enter"}, "reasoning": "..."}
4. swipe: {"action_type": "swipe", "parameters": {"start_x_percent": 50, "start_y_percent": 80, "end_x_percent": 50, "end_y_percent": 20}, "reasoning": "..."}
5. wait: {"action_type": "wait", "parameters": {"seconds": 2}, "reasoning": "..."}
6. complete: {"action_type": "complete", "parameters": {}, "reasoning": "..."}

RULES:
- Coordinates are PERCENTAGES (0-100) from top-left
- Only act on what you ACTUALLY SEE
- If stuck after 3 similar actions, use "complete"
- Respond with ONLY valid JSON - no markdown, no explanations"""

        user_prompt = f"""GOAL: {test_case}

HISTORY:
{history_summary if history_summary else "First step"}

CURRENT SCREEN:
{current_state}

Decide the NEXT action. Respond with ONLY JSON."""

        base64_image = self._encode_image_to_base64(screenshot)
        
        base64_image = self._encode_image_to_base64(screenshot)

        # Build a single text prompt (system + user) and include the image as a data URL
        full_prompt = system_prompt + "\n\n" + user_prompt + "\n\nImage: data:image/jpeg;base64," + base64_image

        for attempt in range(max_retries):
            try:
                self._wait_for_rate_limit()
                resp = self.provider.generate_content(full_prompt, image=None, max_tokens=500, temperature=0.3)
                response_text = resp.text.strip() if resp and hasattr(resp, 'text') else ''
                
                # Clean response
                if response_text.startswith('```json'):
                    response_text = response_text[7:]
                if response_text.startswith('```'):
                    response_text = response_text[3:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
                
                response_text = response_text.strip()
                
                action = json.loads(response_text)
                
                if "action_type" not in action:
                    raise ValueError("Missing 'action_type'")
                
                if "parameters" not in action:
                    action["parameters"] = {}
                
                if "reasoning" not in action:
                    action["reasoning"] = "No reasoning provided"
                
                return action
                
            except json.JSONDecodeError as e:
                print(f"   JSON parse error (attempt {attempt + 1}/{max_retries})")
                print(f"   Response: {response_text[:300]}...")
                
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                else:
                    return {
                        "action_type": "complete",
                        "parameters": {},
                        "reasoning": "Failed to parse response"
                    }
                    
            except Exception as e:
                error_msg = str(e).lower()
                
                if '429' in error_msg or 'rate_limit' in error_msg:
                    if attempt < max_retries - 1:
                        wait_time = 15 * (2 ** attempt)
                        print(f"   Rate limit (attempt {attempt + 1}/{max_retries})")
                        print(f"   Waiting {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        return {
                            "action_type": "wait",
                            "parameters": {"seconds": 30},
                            "reasoning": "Rate limit exceeded"
                        }
                else:
                    print(f"Error: {e}")
                    
                    if attempt < max_retries - 1:
                        time.sleep(3)
                        continue
                    else:
                        return {
                            "action_type": "complete",
                            "parameters": {},
                            "reasoning": f"Error: {str(e)}"
                        }
        
        return {
            "action_type": "complete",
            "parameters": {},
            "reasoning": "Failed after retries"
        }