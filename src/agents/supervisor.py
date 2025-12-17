"""
Supervisor Agent - Evaluates test results and makes final decision
"""
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json

load_dotenv()


class SupervisorAgent:
    def __init__(self):
        api_key = os.getenv('GEMINI_API_KEY')
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    def should_continue(self, test_case, action_history, current_screenshot):
        """
        Decide if testing should continue or if we can make final evaluation
        
        Returns: dict
        {
            "continue": bool,
            "reasoning": str
        }
        """
        
        prompt = f"""
You are a QA test supervisor. Decide if the test execution should continue or if it's ready for final evaluation.

TEST CASE: {test_case}

ACTION HISTORY:
{json.dumps(action_history, indent=2)}

Look at the current screenshot and action history.

DECISION CRITERIA:
- Continue if: More steps are needed to complete the test objective
- Stop if: Test objective is achieved (ready to verify pass/fail)
- Stop if: Stuck in a loop or unable to proceed after multiple attempts
- Stop if: More than 15 actions have been taken

Respond with ONLY a valid JSON object:
{{
    "continue": true/false,
    "reasoning": "brief explanation"
}}
"""
        
        try:
            response = self.model.generate_content([prompt, current_screenshot])
            response_text = response.text.strip()
            
            # Clean up response
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            decision = json.loads(response_text)
            return decision
        
        except Exception as e:
            print(f"Supervisor decision error: {e}")
            # Default to stop after 15 actions
            return {
                "continue": len(action_history) < 15,
                "reasoning": "Default decision due to error"
            }
    
    def evaluate_test_result(self, test_case, action_history, final_screenshot):
        """
        Make final evaluation: PASS or FAIL
        
        Returns: dict
        {
            "result": "PASS" or "FAIL",
            "reason": str,
            "bug_found": bool,
            "details": str
        }
        """
        
        prompt = f"""
You are a QA test supervisor. Evaluate whether this test PASSED or FAILED.

TEST CASE: {test_case}

COMPLETE ACTION HISTORY:
{json.dumps(action_history, indent=2)}

Look at the final screenshot and action history.

EVALUATION RULES:
1. Test PASSES if:
   - All test objectives were successfully completed
   - All verifications passed
   - No errors or missing elements when they should exist

2. Test FAILS if:
   - Test objective could not be completed
   - An expected element was not found
   - A verification failed (wrong text, wrong color, missing feature)
   - An error occurred that prevented completion

IMPORTANT DISTINCTIONS:
- "Failed step" (technical issue like couldn't click) vs "Failed assertion" (bug found)
- If an element genuinely doesn't exist as expected → Test FAILS (bug found)
- If we just had trouble finding it but it exists → Test PASSES

Respond with ONLY a valid JSON object:
{{
    "result": "PASS" or "FAIL",
    "reason": "brief explanation of why",
    "bug_found": true/false,
    "details": "detailed explanation with evidence from actions"
}}
"""
        
        try:
            response = self.model.generate_content([prompt, final_screenshot])
            response_text = response.text.strip()
            
            # Clean up response
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            evaluation = json.loads(response_text)
            
            # Validate response
            if "result" not in evaluation:
                evaluation["result"] = "FAIL"
            if evaluation["result"] not in ["PASS", "FAIL"]:
                evaluation["result"] = "FAIL"
            
            return evaluation
        
        except Exception as e:
            print(f"Supervisor evaluation error: {e}")
            return {
                "result": "FAIL",
                "reason": "Evaluation error",
                "bug_found": False,
                "details": f"Error during evaluation: {str(e)}"
            }
    
    def format_test_report(self, test_case, evaluation, action_count):
        """Format a nice test report"""

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