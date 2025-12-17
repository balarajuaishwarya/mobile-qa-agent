
"""
Main Orchestrator - Coordinates all agents to execute tests
"""
import json
import os
import sys
import time
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.adb import ADBTools
from tools.vision import VisionTools
from config import settings
import shutil
from datetime import timedelta
from agents.supervisor import SupervisorAgent
from agents.planner import PlannerAgent
from agents.executor import ExecutorAgent


class TestOrchestrator:
    def __init__(self):
        print("🚀 Initializing Test Orchestrator...")
        
        self.adb = ADBTools()
        self.vision = VisionTools()
        self.supervisor = SupervisorAgent()
        self.planner = PlannerAgent()
        self.executor = ExecutorAgent(self.adb, self.vision)
        
        self.max_actions = 20
        
        print("✅ All agents initialized!")
    
    def run_test(self, test_case_dict):
        """Run a single test case"""
        
        test_id = test_case_dict['id']
        test_description = test_case_dict['description']
        
        print(f"\n{'='*70}")
        print(f"🧪 Starting Test: {test_id}")
        print(f"📝 Description: {test_description}")
        print(f"{'='*70}\n")
        
        # Initialize test state
        action_history = []
        step_count = 0
        
        # Cleanup old screenshot directories according to settings
        try:
            retention = settings.SCREENSHOT_RETENTION_DAYS
        except Exception:
            retention = None

        if retention and retention > 0:
            cutoff = datetime.now() - timedelta(days=retention)
            screenshots_root = os.path.abspath(settings.SCREENSHOT_DIR)
            if os.path.isdir(screenshots_root):
                for name in os.listdir(screenshots_root):
                    path = os.path.join(screenshots_root, name)
                    try:
                        mtime = datetime.fromtimestamp(os.path.getmtime(path))
                        if mtime < cutoff and os.path.isdir(path):
                            print(f"🧹 Removing old screenshot directory: {path}")
                            shutil.rmtree(path)
                    except Exception:
                        continue

        # Create screenshot directory for this test
        test_screenshot_dir = os.path.join(settings.SCREENSHOT_DIR, f"{test_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        os.makedirs(test_screenshot_dir, exist_ok=True)
        
        # Launch Obsidian app
        print("📱 Launching Obsidian app...")
        self.adb.launch_app("md.obsidian")
        time.sleep(3)
        
        # Main test loop
        while step_count < self.max_actions:
            step_count += 1
            
            print(f"\n--- Step {step_count} ---")
            
            # Take screenshot (optionally save per-step based on settings)
            if getattr(settings, 'SAVE_STEP_SCREENSHOTS', False):
                screenshot_path = os.path.join(test_screenshot_dir, f"step_{step_count:02d}.png")
                screenshot = self.adb.get_screenshot(screenshot_path)
            else:
                screenshot_path = None
                screenshot = self.adb.get_screenshot()
            
            if screenshot is None:
                print("❌ Failed to take screenshot")
                break
            
            # Get screen description
            screen_state = self.vision.describe_screen(screenshot)
            print(f"👁️  Screen State: {screen_state[:200]}...")
            
            # Check if we should continue
            if step_count > 3:  # After a few steps, ask supervisor
                decision = self.supervisor.should_continue(
                    test_description,
                    action_history,
                    screenshot
                )
                
                print(f"🎯 Supervisor Decision: {'Continue' if decision['continue'] else 'Stop'}")
                print(f"   Reasoning: {decision['reasoning']}")
                
                if not decision['continue']:
                    break
            
            # Plan next action
            print(f"🤔 Planner: Deciding next action...")
            action = self.planner.plan_next_action(
                test_description,
                screen_state,
                action_history,
                screenshot
            )
            
            print(f"📋 Planned Action: {action['action_type']}")
            print(f"   Reasoning: {action.get('reasoning', 'N/A')}")
            
            # Check if test is complete
            if action['action_type'] == 'complete':
                print("✅ Planner indicates test is complete")
                break
            
            # Execute action
            execution_result = self.executor.execute_action(action)
            
            print(f"{'✅' if execution_result['success'] else '❌'} Execution: {execution_result['message']}")
            
            # Record action in history
            action_history.append({
                "step": step_count,
                "action": action,
                "execution_result": execution_result,
                "screenshot_path": screenshot_path,
                "timestamp": datetime.now().isoformat()
            })
            
            # Small delay between actions
            time.sleep(1)
        
        # Final evaluation
        print(f"\n🎬 Test execution complete. Taking final screenshot...")
        final_screenshot_path = os.path.join(test_screenshot_dir, 'final.png')
        final_screenshot = self.adb.get_screenshot(final_screenshot_path)
        
        print(f"⚖️  Supervisor: Evaluating test results...")
        evaluation = self.supervisor.evaluate_test_result(
            test_description,
            action_history,
            final_screenshot
        )
        
        # Generate report
        report = self.supervisor.format_test_report(
            test_description,
            evaluation,
            len(action_history)
        )
        
        print(report)
        
        # Save detailed results
        result_file = f"{test_screenshot_dir}/result.json"
        with open(result_file, 'w') as f:
            json.dump({
                "test_id": test_id,
                "test_description": test_description,
                "expected_result": test_case_dict.get('expected_result'),
                "evaluation": evaluation,
                "action_history": action_history,
                "total_steps": len(action_history),
                "timestamp": datetime.now().isoformat()
            }, f, indent=2)
        
        print(f"💾 Detailed results saved to: {result_file}")
        
        return evaluation
    
    def run_all_tests(self, test_cases_file=None):
        """Run all test cases from file

        If test_cases_file is not provided, resolve it relative to this
        script's location to reliably find the repository `tests/` folder
        regardless of current working directory.
        """

        print("\n" + "="*70)
        print("🚀 MOBILE QA MULTI-AGENT TEST SUITE")
        print("="*70 + "\n")

        # Resolve default test cases file relative to this file
        if not test_cases_file:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            test_cases_file = os.path.normpath(os.path.join(base_dir, '..', 'tests', 'test_cases.json'))

        # Load test cases
        if not os.path.exists(test_cases_file):
            raise FileNotFoundError(f"Test cases file not found: {test_cases_file}")

        with open(test_cases_file, 'r') as f:
            test_cases = json.load(f)
        
        print(f"📋 Loaded {len(test_cases)} test cases\n")
        
        results = []
        
        for test_case in test_cases:
            try:
                evaluation = self.run_test(test_case)
                results.append({
                    "test_id": test_case['id'],
                    "result": evaluation['result'],
                    "bug_found": evaluation.get('bug_found', False)
                })
            except Exception as e:
                print(f"❌ Test {test_case['id']} failed with error: {e}")
                results.append({
                    "test_id": test_case['id'],
                    "result": "ERROR",
                    "error": str(e)
                })
            
            # Go back to home screen between tests
            print("\n🏠 Returning to home screen...")
            self.adb.press_home()
            time.sleep(2)
        
        # Summary
        print("\n" + "="*70)
        print("📊 TEST SUITE SUMMARY")
        print("="*70)
        
        passed = sum(1 for r in results if r['result'] == 'PASS')
        failed = sum(1 for r in results if r['result'] == 'FAIL')
        errors = sum(1 for r in results if r['result'] == 'ERROR')
        
        print(f"\nTotal Tests: {len(results)}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Errors: {errors}")
        
        print("\nDetailed Results:")
        for r in results:
            status_emoji = "✅" if r['result'] == 'PASS' else "❌" if r['result'] == 'FAIL' else "⚠️"
            bug_indicator = " 🐛" if r.get('bug_found', False) else ""
            print(f"  {status_emoji} {r['test_id']}: {r['result']}{bug_indicator}")
        
        print("\n" + "="*70 + "\n")
        
        return results


def main():
    """Main entry point"""
    
    # Check if emulator is running
    import subprocess
    result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
    
    if 'emulator' not in result.stdout and 'device' not in result.stdout:
        print("❌ No Android device/emulator detected!")
        print("Please start the emulator first:")
        print("  emulator -avd TestDevice -no-snapshot")
        return
    
    print("✅ Android device detected!")
    
    # Initialize orchestrator
    orchestrator = TestOrchestrator()
    
    # Run all tests
    orchestrator.run_all_tests()


if __name__ == "__main__":
    main()
