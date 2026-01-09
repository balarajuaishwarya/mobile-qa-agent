import json
from typing import Dict, List, Optional
from PIL import Image
import config


class SupervisorAgent:
    """
    Supervises test execution and provides final verdict
    
    Critical Distinctions:
    1. PASS: Goal achieved, all assertions met
    2. FAIL (Bug Found): Expected element/state not present
    3. FAIL (Execution): Agent couldn't complete actions
    
    This distinction is crucial for QA reporting!
    """
    
    EVALUATION_PROMPT = """You are a Senior Mobile QA Supervisor.

YOUR ROLE:
Evaluate whether the test automation successfully completed its goal.

EVALUATION CRITERIA:
1. Compare final screen state with test goal
2. Review execution history for critical failures
3. Determine if goal was achieved OR if a bug was found

POSSIBLE VERDICTS:
- PASS: Goal fully achieved, no issues
- FAIL: Goal not achieved (bug found OR execution blocked)

OUTPUT FORMAT (JSON ONLY):
{{
  "result": "PASS" or "FAIL",
  "reason": "Detailed explanation of verdict",
  "bug_found": true/false
}}

IMPORTANT DISTINCTIONS:
- bug_found=true: Expected feature/element missing or incorrect (ACTUAL BUG)
  Example: "Button should be red but is gray" → FAIL, bug_found=true
  
- bug_found=false: Execution couldn't complete due to technical issues
  Example: "Couldn't find element after 10 tries" → FAIL, bug_found=false

ANALYSIS STEPS:
1. Read the test goal carefully
2. Examine the final screenshot
3. Review what actions were taken
4. Determine if goal requirements are met
5. If not met, determine WHY (bug vs execution issue)

Be thorough but concise in your reasoning.
"""
    
    def __init__(self, ai_provider):
        """
        Initialize supervisor agent
        
        Args:
            ai_provider: AI provider instance
        """
        self.ai = ai_provider
        self.evaluation_count = 0
    
    def evaluate_test(
        self, 
        goal: str, 
        final_screenshot: Optional[Image.Image],
        execution_history: List[Dict]
    ) -> Dict:
        """
        Evaluate test execution and provide final verdict
        
        Args:
            goal: Test objective
            final_screenshot: Last screenshot captured
            execution_history: List of all actions taken
            
        Returns:
            Evaluation result with verdict and reasoning
        """
        self.evaluation_count += 1
        
        if final_screenshot is None:
            return self._error_verdict("No final screenshot available")
        
        history_summary = self._format_history(execution_history)

        prompt = f"""{self.EVALUATION_PROMPT}

TEST GOAL:
{goal}

EXECUTION HISTORY:
{history_summary}

Examine the final screenshot and provide your verdict as JSON.
"""
        
        try:
            response = self.ai.generate_response(prompt, final_screenshot)
            verdict = self._validate_verdict(response)
            
            if config.VERBOSE_OUTPUT:
                print(f"\n Supervisor: {verdict['result']} - {verdict['reason'][:70]}...")
            
            return verdict
            
        except Exception as e:
            print(f" Supervisor error: {e}")
            return self._error_verdict(f"Evaluation error: {str(e)}")
    
    def verify_step(
        self,
        execution_result: Dict,
    ) -> Dict:
        """
        Quick verification after each step (optional, for continuous monitoring)
        
        Args:
            action: Action that was taken
            execution_result: Result from executor
            screenshot: Screenshot after action
            
        Returns:
            Quick status check
        """
        # Simple check: did execution succeed?
        if execution_result.get("status") == "failed":
            return {
                "continue": False,
                "reason": f"Execution failed: {execution_result.get('message', 'Unknown')}"
            }
        
        # For most cases, continue
        return {
            "continue": True,
            "reason": "Step completed successfully"
        }
    
    def _format_history(self, history: List[Dict]) -> str:
        """Format execution history for prompt"""
        if not history:
            return "No actions recorded"
        
        lines = []
        for i, entry in enumerate(history, 1):
            if isinstance(entry, dict):
                action = entry.get('action', entry.get('action_type', 'unknown'))
                status = entry.get('status', 'unknown')
                message = entry.get('message', entry.get('reason', ''))
                
                lines.append(f"{i}. {action} → {status}: {message}")
            else:
                lines.append(f"{i}. {str(entry)}")
        
        return "\n".join(lines)
    
    def _validate_verdict(self, response: any) -> Dict:
        """
        Validate and normalize verdict response
        
        Ensures verdict has required fields with correct types
        """
        # Parse string to dict if needed
        if isinstance(response, str):
            try:
                response = json.loads(self._clean_json(response))
            except json.JSONDecodeError:
                return self._error_verdict(f"Invalid JSON: {response[:100]}")
        
        # Ensure dict
        if not isinstance(response, dict):
            return self._error_verdict("Response not a JSON object")
        
        # Normalize verdict
        result = str(response.get("result", "FAIL")).upper()
        if result not in ["PASS", "FAIL"]:
            result = "FAIL"
        
        verdict = {
            "result": result,
            "reason": str(response.get("reason", "No explanation provided")),
            "bug_found": bool(response.get("bug_found", False))
        }
        
        return verdict
    
    def _clean_json(self, text: str) -> str:
        """Remove markdown and find JSON object"""
        text = text.strip()
        
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        
        start = text.find('{')
        end = text.rfind('}')
        
        if start != -1 and end != -1:
            return text[start:end + 1]
        
        return text
    
    def _error_verdict(self, error_msg: str) -> Dict:
        """Return error verdict"""
        return {
            "result": "FAIL",
            "reason": error_msg,
            "bug_found": False
        }
    
    def get_stats(self) -> Dict:
        """Get supervisor statistics"""
        return {
            "total_evaluations": self.evaluation_count
        }