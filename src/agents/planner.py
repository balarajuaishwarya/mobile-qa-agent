"""
Planner Agent - Decides what action to take next
"""
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json

load_dotenv()


class PlannerAgent:
    def __init__(self):
        api_key = os.getenv('GEMINI_API_KEY')
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    def plan_next_action(self, test_case, current_state, action_history, screenshot):
        """
        Decide the next action based on current state and goal
        
        Returns: dict with action details
        """
        
        # Build context from history
        recent_actions = action_history[-3:] if len(action_history) > 3 else action_history
        history_summary = "\n".join([
            f"Step {a['step']}: {a['action']['action_type']} - {a['action'].get('reasoning', 'N/A')}"
            for a in recent_actions
        ])
        
        prompt = f"""You are a mobile app testing expert. Analyze this screenshot and decide the NEXT SINGLE ACTION.

GOAL: {test_case}

WHAT WE'VE DONE SO FAR:
{history_summary if history_summary else "Nothing yet - this is the first step"}

CURRENT SCREEN DESCRIPTION:
{current_state}

Look at the screenshot carefully. Identify ALL visible UI elements (buttons, text fields, icons, menus).

IMPORTANT RULES:
1. If this is Obsidian's first-time setup screen, look for:
   - "Create new vault" or "New vault" button
   - "Skip" or "Get Started" button  
   - Any setup wizard buttons
2. Focus on VISIBLE, CLICKABLE elements in the screenshot
3. Provide coordinates as PERCENTAGES (0-100) from top-left
4. If you see a text input field, you may need to tap it first before typing
5. Be specific about what you see and where it is located
6. If stuck after 3 similar attempts, use "complete" to let supervisor evaluate

AVAILABLE ACTIONS:

1. **tap** - Tap at coordinates
   Use when: You see a button, icon, or clickable element
   Example: {{"action_type": "tap", "parameters": {{"x_percent": 50, "y_percent": 30}}, "reasoning": "Tapping the 'Create Vault' button visible at center-top of screen"}}

2. **type** - Type text
   Use when: A text field is active/focused (usually has cursor or is highlighted)
   Example: {{"action_type": "type", "parameters": {{"text": "InternVault"}}, "reasoning": "Typing vault name into focused text field"}}

3. **press_key** - Press special key (back, enter, home)
   Use when: Need to confirm input or go back
   Example: {{"action_type": "press_key", "parameters": {{"key": "enter"}}, "reasoning": "Confirming the vault name"}}

4. **swipe** - Swipe gesture
   Use when: Need to scroll to see more options
   Example: {{"action_type": "swipe", "parameters": {{"start_x_percent": 50, "start_y_percent": 80, "end_x_percent": 50, "end_y_percent": 20}}, "reasoning": "Scrolling down to find more options"}}

5. **wait** - Wait for UI to settle
   Use when: App might be loading or transitioning
   Example: {{"action_type": "wait", "parameters": {{"seconds": 2}}, "reasoning": "Waiting for vault creation to complete"}}

6. **complete** - Declare this step complete, ready for supervisor evaluation
   Use when: 
   - Goal appears to be achieved
   - Stuck and can't proceed after several attempts
   - Need supervisor to evaluate if test passed/failed
   Example: {{"action_type": "complete", "parameters": {{}}, "reasoning": "Vault creation UI not found after multiple attempts, needs evaluation"}}

STEP-BY-STEP THINKING:
1. What do I see on this screen right now?
2. What does the test goal require next?
3. Which visible element should I interact with?
4. Where exactly is it located (estimate percentages)?

Respond with ONLY a valid JSON object, nothing else.
"""
        
        try:
            response = self.model.generate_content([prompt, screenshot])
            response_text = response.text.strip()
            
            # Clean up response
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            # Try to parse JSON
            action = json.loads(response_text)
            
            # Validate action structure
            if "action_type" not in action:
                raise ValueError("Missing action_type in response")
            
            return action
        
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse Planner response as JSON: {e}")
            print(f"📄 Raw response:\n{response_text}\n")
            return {
                "action_type": "complete",
                "parameters": {},
                "reasoning": "Failed to parse planner response - completing step"
            }
        except Exception as e:
            print(f"❌ Planner error: {e}")
            return {
                "action_type": "complete",
                "parameters": {},
                "reasoning": f"Error occurred: {str(e)}"
            }