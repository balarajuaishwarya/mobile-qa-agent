"""Supervisor Agent - Robust version"""
import json


class SupervisorAgent:
    def __init__(self, ai):
        self.ai = ai

    def evaluate(self, goal, image, history=None):
        """Evaluate test result"""
        
        if image is None:
            return {
                "result": "FAIL",
                "reason": "No screenshot for evaluation",
                "bug_found": False
            }
        
        history_summary = ""
        if history:
            history_summary = f"\nActions taken: {len(history)} steps"
        
        prompt = f"""You are a QA supervisor evaluating a mobile test.

TEST GOAL:
{goal}
{history_summary}

Look at the final screenshot and decide if the test PASSED or FAILED.

EVALUATION RULES:
- PASS: Goal achieved successfully
- FAIL: Goal not achieved or error occurred

Respond with ONLY this JSON format:
{{
  "result": "PASS" or "FAIL",
  "reason": "brief explanation",
  "bug_found": true or false
}}"""

        try:
            response = self.ai.generate_response(prompt, image)
            
            # Handle string response
            if isinstance(response, str):
                try:
                    response = json.loads(response)
                except:
                    return {
                        "result": "FAIL",
                        "reason": "Could not parse evaluation",
                        "bug_found": False
                    }
            
            # Validate and set defaults
            if not isinstance(response, dict):
                return {
                    "result": "FAIL",
                    "reason": "Invalid evaluation format",
                    "bug_found": False
                }
            
            response.setdefault("result", "FAIL")
            response.setdefault("reason", "No reason provided")
            response.setdefault("bug_found", False)
            
            # Validate result value
            if response["result"] not in ["PASS", "FAIL"]:
                response["result"] = "FAIL"
            
            return response
            
        except Exception as e:
            print(f" Supervisor error: {e}")
            return {
                "result": "FAIL",
                "reason": f"Evaluation failed: {str(e)}",
                "bug_found": False
            }