"""
Mobile QA Multi-Agent System - Main Test Runner
Complete orchestration of Supervisor-Planner-Executor architecture
"""

import time
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict

import config
from tools.adb import ADBInterface
from tools.ai_provider import AIProviderFactory
from tools.vision import VisionAnalyzer
from agents.planner import PlannerAgent
from agents.executor import ExecutorAgent
from agents.supervisor import SupervisorAgent


class TestRunner:
    """
    Orchestrates the multi-agent test execution system
    
    Architecture:
    1. Vision analyzes screenshot → UI elements
    2. Planner decides next action → action plan
    3. Executor performs action → result
    4. Supervisor monitors progress → continue/stop
    5. Repeat until goal achieved or max steps
    """
    
    def __init__(self):
        """Initialize all components"""
        print("\n" + "="*70)
        print("🚀 MOBILE QA MULTI-AGENT SYSTEM")
        print("="*70 + "\n")
        
        # Initialize components
        print("Initializing system...")
        
        self.adb = ADBInterface()
        print("✓ ADB interface ready")
        
        self.ai = AIProviderFactory.create()
        print("✓ AI provider ready")
        
        self.vision = VisionAnalyzer(self.ai)
        print("✓ Vision analyzer ready")
        
        self.planner = PlannerAgent(self.ai)
        print("✓ Planner agent ready")
        
        self.executor = ExecutorAgent(self.adb)
        print("✓ Executor agent ready")
        
        self.supervisor = SupervisorAgent(self.ai)
        print("✓ Supervisor agent ready")
        
        # Results tracking
        self.all_results = []
        
        print("\n" + "="*70 + "\n")
    
    def run_single_test(self, test_case: Dict) -> Dict:
        """
        Execute a single test case
        
        Args:
            test_case: Dictionary with goal, name, expected result, etc.
            
        Returns:
            Test result dictionary
        """
        goal = test_case.get("goal", test_case.get("description", ""))
        test_name = test_case.get("name", goal[:50])
        max_steps = test_case.get("max_steps", config.MAX_STEPS_PER_TEST)
        
        print("\n" + "="*70)
        print(f"🧪 TEST: {test_name}")
        print("="*70)
        print(f"Goal: {goal}")
        print(f"Max Steps: {max_steps}")
        print("="*70 + "\n")
        
        # Launch app
        print("📱 Launching Obsidian...")
        self.adb.wake_device()  # Ensure screen is on
        self.adb.launch_app(config.OBSIDIAN_PACKAGE)
        
        # Execution tracking
        execution_history = []
        start_time = time.time()
        
        # Main execution loop
        for step in range(1, max_steps + 1):
            print(f"\n{'─'*70}")
            print(f"📍 STEP {step}/{max_steps}")
            print(f"{'─'*70}")
            
            # 1. Capture current state
            screenshot = self.adb.get_screenshot()
            if screenshot is None:
                print("❌ Screenshot failed, aborting test")
                break
            
            # Save screenshot
            if config.SAVE_SCREENSHOTS:
                screenshot_path = config.SCREENSHOTS_DIR / f"test_{test_case.get('id', 'unknown')}_step_{step}.png"
                screenshot.save(screenshot_path)
            
            # 2. Analyze UI
            print("👁️  Analyzing screen...")
            vision_analysis = self.vision.analyze_screen(screenshot)
            ui_context = self.vision.format_for_planner(vision_analysis)
            
            if config.VERBOSE_OUTPUT:
                print(f"\n{ui_context}\n")
            
            # Check for blocking screens
            if vision_analysis.get("blocking_screen"):
                print("⚠️  Blocking screen detected (popup/loading)")
            
            # 3. Plan next action
            print("🧠 Planning next action...")
            action = self.planner.plan_next_action(goal, ui_context, execution_history)
            
            # Check if complete
            if action["action_type"] == "complete":
                print(f"\n🏁 Test execution complete after {step} steps")
                break
            
            # 4. Execute action
            print("⚡ Executing action...")
            result = self.executor.execute_action(action)
            
            # 5. Record history
            history_entry = {
                "step": step,
                "action": action["action_type"],
                "status": result["status"],
                "message": result.get("message", ""),
                "reason": action.get("reasoning", "")
            }
            execution_history.append(history_entry)
            
            # 6. Quick supervisor check (optional)
            if result["status"] == "failed":
                print(f"⚠️  Execution failed: {result.get('message', 'Unknown error')}")
                # Could add smart retry logic here
            
            # Brief pause between steps
            time.sleep(0.5)
        
        # Final evaluation
        print("\n" + "="*70)
        print("📊 FINAL EVALUATION")
        print("="*70 + "\n")
        
        time.sleep(1)  # Let UI settle
        final_screenshot = self.adb.get_screenshot()
        
        if final_screenshot and config.SAVE_SCREENSHOTS:
            final_path = config.SCREENSHOTS_DIR / f"test_{test_case.get('id', 'unknown')}_final.png"
            final_screenshot.save(final_path)
        
        verdict = self.supervisor.evaluate_test(goal, final_screenshot, execution_history)
        
        # Calculate stats
        elapsed_time = time.time() - start_time
        
        # Build result
        test_result = {
            "test_id": test_case.get("id", "unknown"),
            "test_name": test_name,
            "goal": goal,
            "result": verdict["result"],
            "reason": verdict["reason"],
            "bug_found": verdict["bug_found"],
            "expected": test_case.get("expected", ""),
            "steps_executed": len(execution_history),
            "execution_time": round(elapsed_time, 2),
            "timestamp": datetime.now().isoformat(),
            "history": execution_history
        }
        
        # Display result
        self._print_test_result(test_result)
        
        # Return to home
        print("\n🏠 Returning to home screen...")
        self.adb.press_key("home")
        time.sleep(config.TEST_DELAY)
        
        return test_result
    
    def run_test_suite(self, test_cases: List[Dict]) -> List[Dict]:
        """
        Run multiple test cases
        
        Args:
            test_cases: List of test case dictionaries
            
        Returns:
            List of test results
        """
        print("\n" + "="*70)
        print("📋 TEST SUITE EXECUTION")
        print("="*70)
        print(f"Total Tests: {len(test_cases)}")
        print("="*70 + "\n")
        
        results = []
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{'█'*70}")
            print(f"TEST {i}/{len(test_cases)}")
            print(f"{'█'*70}")
            
            result = self.run_single_test(test_case)
            results.append(result)
            
            # Brief pause between tests
            if i < len(test_cases):
                print(f"\n⏳ Next test in {config.TEST_DELAY} seconds...")
                time.sleep(config.TEST_DELAY)
        
        # Final summary
        self._print_suite_summary(results)
        
        # Save results
        self._save_results(results)
        
        return results
    
    def _print_test_result(self, result: Dict):
        """Pretty print single test result"""
        print("\n" + "="*70)
        
        if result["result"] == "PASS":
            print("✅ TEST PASSED")
        else:
            print("❌ TEST FAILED")
        
        print("="*70)
        print(f"Test: {result['test_name']}")
        print(f"Result: {result['result']}")
        print(f"Bug Found: {result['bug_found']}")
        print(f"Steps: {result['steps_executed']}")
        print(f"Time: {result['execution_time']}s")
        print(f"\nReason: {result['reason']}")
        print("="*70)
    
    def _print_suite_summary(self, results: List[Dict]):
        """Pretty print test suite summary"""
        print("\n\n" + "="*70)
        print("📊 TEST SUITE SUMMARY")
        print("="*70 + "\n")
        
        passed = sum(1 for r in results if r["result"] == "PASS")
        failed = sum(1 for r in results if r["result"] == "FAIL")
        bugs_found = sum(1 for r in results if r.get("bug_found", False))
        
        total_time = sum(r["execution_time"] for r in results)
        total_steps = sum(r["steps_executed"] for r in results)
        
        print(f"Total Tests:    {len(results)}")
        print(f"✅ Passed:      {passed}")
        print(f"❌ Failed:      {failed}")
        print(f"🐛 Bugs Found:  {bugs_found}")
        print(f"\n⏱️  Total Time:  {total_time:.1f}s")
        print(f"📍 Total Steps:  {total_steps}")
        
        print("\nDetailed Results:")
        print("-" * 70)
        for r in results:
            status = "✅" if r["result"] == "PASS" else "❌"
            bug = "🐛" if r.get("bug_found") else "  "
            print(f"{status} {bug} {r['test_name']:<40} {r['result']}")
        
        print("="*70 + "\n")
        
        # System stats
        print("System Statistics:")
        print(f"  AI Calls: {self.ai.get_stats()['total_calls']}")
        print(f"  Plans: {self.planner.get_stats()['total_plans']}")
        print(f"  Executions: {self.executor.get_stats()['total_executions']}")
        print(f"  Evaluations: {self.supervisor.get_stats()['total_evaluations']}")
        print()
    
    def _save_results(self, results: List[Dict]):
        """Save results to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = config.RESULTS_DIR / f"test_results_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"💾 Results saved: {results_file}\n")


def main():
    """Main entry point"""
    try:
        # Initialize test runner
        runner = TestRunner()
        
        # Load test cases
        test_cases = config.DEFAULT_TESTS
        
        # Run test suite
        results = runner.run_test_suite(test_cases)
        
        # Exit with appropriate code
        failed = sum(1 for r in results if r["result"] == "FAIL")
        exit_code = 0 if failed == 0 else 1
        
        print(f"Exiting with code: {exit_code}")
        return exit_code
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        return 130
    
    except Exception as e:
        print(f"\n\n❌ Critical error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())