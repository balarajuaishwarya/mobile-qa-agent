"""Main Test Runner - Production Version"""
from tools.ai_provider import AIProvider
from tools.adb import ADBTools
from tools.vision import VisionTools
from agents.planner import PlannerAgent
from agents.executor import ExecutorAgent
from agents.supervisor import SupervisorAgent
import time


def run_test(goal, max_steps=10):
    """Run a single test"""
    
    print("\n" + "="*70)
    print(f" TEST: {goal}")
    print("="*70 + "\n")
    
    # Initialize (shared provider for rate limiting)
    provider = AIProvider()
    adb = ADBTools()
    vision = VisionTools(provider)
    planner = PlannerAgent(provider)
    executor = ExecutorAgent(adb)
    supervisor = SupervisorAgent(provider)

    history = []
    
    # Launch app
    print(" Launching Obsidian...")
    adb.launch_app("md.obsidian")
    time.sleep(3)
    
    # Test loop
    for i in range(max_steps):
        print(f"\n{'─'*70}")
        print(f"STEP {i+1}/{max_steps}")
        print(f"{'─'*70}")
        
        # Get screenshot
        img = adb.get_screenshot()
        if img is None:
            print(" Screenshot failed, stopping")
            break
        
        # Describe screen
        print(" Analyzing screen...")
        context = vision.describe_screen(img)
        print(f"   {context[:150]}...")
        
        # Plan action
        print("\n Planning next action...")
        plan = planner.plan(goal, context, history)
        
        action_type = plan.get("action_type", "unknown")
        print(f"   Action: {action_type}")
        print(f"   Reason: {plan.get('reasoning', 'N/A')[:100]}")
        
        # Check if complete
        if action_type == "complete":
            print("\n Planner indicates completion")
            break
        
        # Execute
        result = executor.execute(plan)
        history.append(result)
        
        # Add delay between steps
        time.sleep(1.5)
    
    # Final evaluation
    print("\n" + "="*70)
    print(" FINAL EVALUATION")
    print("="*70 + "\n")
    
    final_img = adb.get_screenshot()
    report = supervisor.evaluate(goal, final_img, history)
    
    # Display result
    result_emoji = "✅" if report["result"] == "PASS" else "❌"
    print(f"\n{result_emoji} RESULT: {report['result']}")
    print(f" Reason: {report['reason']}")
    print(f" Bug found: {report['bug_found']}")
    print(f" Steps taken: {len(history)}")
    print(f" API calls: ~{provider.call_count}")
    
    # Go home
    print("\n Returning to home screen...")
    adb.press_home()
    
    return report


if __name__ == "__main__":
    # Test case
    test_goal = "Open Obsidian and create a new vault named 'InternVault'"
    
    result = run_test(test_goal, max_steps=10)
    
    print("\n" + "="*70)
    print("✨ TEST COMPLETE")
    print("="*70)