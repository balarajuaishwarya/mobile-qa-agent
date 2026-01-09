import json
from typing import Dict, List
import config


class PlannerAgent:
    """
    Plans the next action to take toward achieving test goal
    
    Design Principles:
    1. ONE action at a time (prevents runaway execution)
    2. Uses history to avoid loops
    3. Provides clear reasoning
    4. Structured JSON output for Executor
    """
    
    SYSTEM_PROMPT = """You are a Mobile Test Automation Planner.

YOUR ROLE:
Analyze the current screen state and execution history to decide the SINGLE NEXT ACTION.

AVAILABLE ACTIONS:
1. tap: Click element at coordinates
   {{"action_type": "tap", "parameters": {{"x": 500, "y": 300}}, "reasoning": "Click Create button"}}

2. type: Enter text in focused input
   {{"action_type": "type", "parameters": {{"text": "VaultName"}}, "reasoning": "Enter vault name"}}

3. press_key: Press device key
   {{"action_type": "press_key", "parameters": {{"key": "enter"}}, "reasoning": "Submit form"}}
   Keys: enter, back, home, backspace, menu

4. swipe: Scroll gesture
   {{"action_type": "swipe", "parameters": {{"start_x": 500, "start_y": 800, "end_x": 500, "end_y": 200}}, "reasoning": "Scroll down"}}

5. wait: Pause for UI settling
   {{"action_type": "wait", "parameters": {{"seconds": 2}}, "reasoning": "Wait for loading"}}

6. complete: Mark goal as achieved
   {{"action_type": "complete", "parameters": {{}}, "reasoning": "All steps done, vault created and entered"}}

CRITICAL RULES:
1. COORDINATES: Use the exact 0-1000 normalized coordinates from UI Context
2. MATCH ELEMENTS: Only tap elements that are listed in the UI Context
3. JSON ONLY: Return ONLY valid JSON, no markdown or extra text
4. ONE ACTION: Plan exactly one action, not a sequence
5. BE SPECIFIC: Reference exact element text from UI Context
6. AVOID LOOPS: If action failed twice, try different approach or complete with explanation
7. REASONING: Explain which element you're targeting and why

PLANNING STRATEGY:
- Read the goal carefully
- Check what's on screen (UI Context)
- Review what you've already tried (History)
- Pick the best next step toward the goal
- If stuck or goal reached, use "complete"
"""
    
    def __init__(self, ai_provider):
        """
        Initialize planner agent
        
        Args:
            ai_provider: AI provider instance
        """
        self.ai = ai_provider
        self.plan_count = 0
    
    def plan_next_action(
        self, 
        goal: str, 
        ui_context: str, 
        history: List[Dict]
    ) -> Dict:
        """
        Plan the next action based on current state
        
        Args:
            goal: Test objective (e.g., "Create vault named X")
            ui_context: Formatted string from vision analysis
            history: List of previous actions taken
            
        Returns:
            Action dictionary with action_type, parameters, and reasoning
        """
        self.plan_count += 1
        
        # Build history summary (last 5 actions to save tokens)
        history_summary = self._format_history(history)
        
        # Construct planning prompt
        prompt = f"""{self.SYSTEM_PROMPT}

GOAL: {goal}

UI CONTEXT:
{ui_context}

EXECUTION HISTORY:
{history_summary}

Based on the above, provide the next action as valid JSON.
"""
        
        try:
            response = self.ai.generate_response(prompt)
            action = self._validate_action(response)
            
            if config.VERBOSE_OUTPUT:
                print(f"  Planner: {action.get('action_type')} - {action.get('reasoning', '')[:60]}...")
            
            return action
            
        except Exception as e:
            print(f"  Planner error: {e}")
            return {
                "action_type": "wait",
                "parameters": {"seconds": 2},
                "reasoning": f"Planner error: {str(e)}"
            }
    
    def _format_history(self, history: List[Dict]) -> str:
        """
        Format execution history for prompt
        
        Args:
            history: List of action dictionaries
            
        Returns:
            Formatted string
        """
        if not history:
            return "No actions taken yet."
        
        # Take last N actions
        recent = history[-5:]
        
        lines = []
        for i, action in enumerate(recent, 1):
            if isinstance(action, dict):
                action_type = action.get('action', action.get('action_type', 'unknown'))
                status = action.get('status', '')
                reason = action.get('reason', action.get('reasoning', ''))
                
                lines.append(f"Step {i}: {action_type} ({status}) - {reason}")
            else:
                lines.append(f"Step {i}: {str(action)}")
        
        return "\n".join(lines)
    
    def _validate_action(self, response: any) -> Dict:
        """
        Validate and normalize action response
        
        Ensures action has required fields and valid structure
        """
        # Parse string to dict if needed
        if isinstance(response, str):
            try:
                response = json.loads(self._clean_json(response))
            except json.JSONDecodeError:
                print(f"  Invalid JSON from planner: {response[:100]}")
                return self._fallback_action("JSON parse error")
        
        # Ensure dict
        if not isinstance(response, dict):
            return self._fallback_action("Response not a JSON object")
        
        # Check required fields
        if "action_type" not in response:
            return self._fallback_action("Missing action_type")
        
        # Normalize structure
        action = {
            "action_type": str(response["action_type"]),
            "parameters": response.get("parameters", {}),
            "reasoning": str(response.get("reasoning", "No reasoning provided"))
        }
        
        # Validate action type
        valid_types = ["tap", "type", "press_key", "swipe", "wait", "complete"]
        if action["action_type"] not in valid_types:
            print(f"  Invalid action type: {action['action_type']}")
            return self._fallback_action(f"Unknown action: {action['action_type']}")
        
        # Validate parameters
        if not isinstance(action["parameters"], dict):
            action["parameters"] = {}
        
        return action
    
    def _clean_json(self, text: str) -> str:
        """Remove markdown and find JSON object"""
        text = text.strip()
        
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        
        # Find JSON boundaries
        start = text.find('{')
        end = text.rfind('}')
        
        if start != -1 and end != -1:
            return text[start:end + 1]
        
        return text
    
    def _fallback_action(self, reason: str) -> Dict:
        """Return safe fallback action"""
        return {
            "action_type": "wait",
            "parameters": {"seconds": 1},
            "reasoning": f"Fallback: {reason}"
        }
    
    def get_stats(self) -> Dict:
        """Get planner statistics"""
        return {
            "total_plans": self.plan_count
        }