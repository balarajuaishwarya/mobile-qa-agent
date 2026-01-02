"""Planner Agent - Robust version"""
import json


class PlannerAgent:
    def __init__(self, ai):
        self.ai = ai

    def plan(self, goal, screen_context, history):
        """Plan next action"""
        
        # Build history summary
        recent = history[-3:] if len(history) > 3 else history
        history_str = "\n".join([
            f"Step {i+1}: {h.get('action', 'unknown')}"
            for i, h in enumerate(recent)
        ]) if recent else "No actions yet"
        
        prompt = f"""You are a mobile UI automation planner.

GOAL: {goal}

CURRENT SCREEN:
{screen_context}

RECENT ACTIONS:
{history_str}

Plan the NEXT SINGLE ACTION to achieve the goal.

ALLOWED ACTIONS:
- tap: Tap at coordinates {{"action_type": "tap", "parameters": {{"x": 540, "y": 1200}}, "reasoning": "..."}}
- type: Type text {{"action_type": "type", "parameters": {{"text": "InternVault"}}, "reasoning": "..."}}
- press_key: Press key {{"action_type": "press_key", "parameters": {{"key": "enter"}}, "reasoning": "..."}}
- swipe: Swipe {{"action_type": "swipe", "parameters": {{"start_x": 500, "start_y": 1500, "end_x": 500, "end_y": 500}}, "reasoning": "..."}}
- wait: Wait {{"action_type": "wait", "parameters": {{"seconds": 2}}, "reasoning": "..."}}
- complete: Task done {{"action_type": "complete", "parameters": {{}}, "reasoning": "..."}}

CRITICAL RULES:
1. Use ACTUAL pixel coordinates (not percentages) - screen is typically 1080x2400
2. Respond with ONLY valid JSON
3. If stuck or goal achieved, use "complete"

Respond with ONE action as JSON:"""

        try:
            response = self.ai.generate_response(prompt)
            
            # Handle string response
            if isinstance(response, str):
                try:
                    response = json.loads(response)
                except:
                    return {
                        "action_type": "complete",
                        "parameters": {},
                        "reasoning": "Could not parse planner response"
                    }
            
            # Validate
            if not isinstance(response, dict) or "action_type" not in response:
                return {
                    "action_type": "complete",
                    "parameters": {},
                    "reasoning": "Invalid planner response format"
                }
            
            response.setdefault("parameters", {})
            response.setdefault("reasoning", "No reasoning provided")
            
            return response
            
        except Exception as e:
            print(f" Planner error: {e}")
            return {
                "action_type": "complete",
                "parameters": {},
                "reasoning": f"Planner failed: {str(e)}"
            }