"""
Supervisor Agent - Using OpenRouter API
"""
import os
import time
import json
import base64
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv

from tools.ai_provider import AIProviderManager

load_dotenv()


class SupervisorAgent:
    def __init__(self, calls_per_minute=60):
        """Initialize Supervisor and AI provider manager."""

        # Use central provider manager (prefers OpenAI when configured)
        self.provider = AIProviderManager()

        # Keep model setting for diagnostics; provider will use configured model
        self.model = os.getenv('OPENROUTER_MODEL') or os.getenv('OPENAI_MODEL')

        self.calls_per_minute = calls_per_minute
        self.min_interval = 60.0 / calls_per_minute
        self.last_call_time = 0
        print(f"Supervisor initialized with OpenRouter")
        print(f"   Model: {self.model}")
        print(f"   Rate limit: {calls_per_minute} calls/min")
    
    def _wait_for_rate_limit(self):
        """Ensure we don't exceed rate limits"""
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time
        if time_since_last_call < self.min_interval:
            wait_time = self.min_interval - time_since_last_call
            print(f"   Supervisor rate limit: waiting {wait_time:.1f}s...")
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
    
    def should_continue(self, test_case, action_history, current_screenshot, max_retries=3):
        """Decide if testing should continue"""
        
        system_prompt = """You are a QA test supervisor. Decide if test should continue.

Respond with ONLY JSON:
{
    "continue": true or false,
    "reasoning": "brief explanation"
}

CRITERIA:
- Continue: More steps needed for test objective
- Stop: Objective achieved OR stuck OR 12+ actions taken"""

        recent_history = action_history[-5:] if len(action_history) > 5 else action_history
        user_prompt = f"""TEST: {test_case}

ACTIONS: {len(action_history)} steps

HISTORY:
{json.dumps(recent_history, indent=2)}

Continue or stop? ONLY JSON."""

        base64_image = self._encode_image_to_base64(current_screenshot)

        # Build full text prompt including the image as a data URL
        full_prompt = system_prompt + "\n\n" + user_prompt + "\n\nImage: data:image/jpeg;base64," + base64_image

        for attempt in range(max_retries):
            try:
                self._wait_for_rate_limit()

                resp = self.provider.generate_content(full_prompt, image=None, max_tokens=200, temperature=0.2)
                response_text = resp.text.strip() if resp and hasattr(resp, 'text') else ''

                if response_text.startswith('```json'):
                    response_text = response_text[7:]
                if response_text.startswith('```'):
                    response_text = response_text[3:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]

                decision = json.loads(response_text.strip())
                
                if "continue" not in decision:
                    decision["continue"] = len(action_history) < 12
                if "reasoning" not in decision:
                    decision["reasoning"] = "No reasoning"
                
                return decision
                
            except Exception as e:
                print(f"Decision error (attempt {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                else:
                    return {
                        "continue": len(action_history) < 12,
                        "reasoning": "Default due to error"
                    }
        
        return {"continue": False, "reasoning": "Failed after retries"}
    
    def evaluate_test_result(self, test_case, action_history, final_screenshot, max_retries=3):
        """Final evaluation: PASS or FAIL"""
        
        system_prompt = """You are a QA supervisor. Evaluate test result.

Respond with ONLY JSON:
{
    "result": "PASS" or "FAIL",
    "reason": "brief explanation",
    "bug_found": true or false,
    "details": "detailed explanation"
}

RULES:
- PASS: All objectives completed
- FAIL: Objective not completed or element not found
- bug_found: true if expected feature genuinely missing"""

        user_prompt = f"""TEST: {test_case}

HISTORY:
{json.dumps(action_history, indent=2)}

Evaluate. ONLY JSON."""

        base64_image = self._encode_image_to_base64(final_screenshot)

        full_prompt = system_prompt + "\n\n" + user_prompt + "\n\nImage: data:image/jpeg;base64," + base64_image

        for attempt in range(max_retries):
            try:
                self._wait_for_rate_limit()

                resp = self.provider.generate_content(full_prompt, image=None, max_tokens=600, temperature=0.2)
                response_text = resp.text.strip() if resp and hasattr(resp, 'text') else ''

                if response_text.startswith('```json'):
                    response_text = response_text[7:]
                if response_text.startswith('```'):
                    response_text = response_text[3:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]

                evaluation = json.loads(response_text.strip())
                
                if "result" not in evaluation or evaluation["result"] not in ["PASS", "FAIL"]:
                    evaluation["result"] = "FAIL"
                if "reason" not in evaluation:
                    evaluation["reason"] = "No reason"
                if "bug_found" not in evaluation:
                    evaluation["bug_found"] = False
                if "details" not in evaluation:
                    evaluation["details"] = "No details"
                
                return evaluation
                
            except Exception as e:
                print(f"Evaluation error (attempt {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                else:
                    return {
                        "result": "FAIL",
                        "reason": "Evaluation failed",
                        "bug_found": False,
                        "details": f"Error: {str(e)}"
                    }
        
        return {
            "result": "FAIL",
            "reason": "Failed after retries",
            "bug_found": False,
            "details": "Evaluation failed"
        }
    
    def format_test_report(self, test_case, evaluation, action_count):
        """Format test report"""

        bug_status = "BUG FOUND" if evaluation.get("bug_found", False) else "NO BUG"
        
        report = f"""
{'='*70}
TEST RESULT: {evaluation['result']}
{'='*70}

TEST CASE:
{test_case}

RESULT: {evaluation['result']}
STATUS: {bug_status}

REASON:
{evaluation.get('reason', 'N/A')}

DETAILS:
{evaluation.get('details', 'N/A')}

ACTIONS TAKEN: {action_count}
{'='*70}
"""
        return report