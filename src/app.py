from langgraph.graph import StateGraph, END
import json
import os

from tools.adb import ADBInterface
from tools.ai_provider import AIProviderFactory
from tools.vision import VisionAnalyzer
from agents.planner import PlannerAgent
from agents.executor import ExecutorAgent
from agents.state import AgentState, get_initial_state

adb = ADBInterface()
ai = AIProviderFactory.create()
vision = VisionAnalyzer(ai)
planner = PlannerAgent(ai)
executor = ExecutorAgent(adb)

# --- Define Node Functions ---

def vision_node(state: AgentState):
    """Captures screenshot and analyzes UI elements"""
    print(f"\n--- [VISION] Step {state['step_count'] + 1} ---")
    screenshot = adb.get_screenshot()
    
    analysis = vision.analyze_screen(screenshot)
    ui_context = vision.format_for_planner(analysis)
    
    return {
        "ui_context": ui_context, 
        "screenshot": screenshot,
        "step_count": state['step_count'] + 1
    }

def planner_node(state: AgentState):
    """Decides the next action based on current screen and history"""
    print("--- [PLANNER] Deciding next move ---")
  
    plan = planner.plan_next_action(
        goal=state['goal'], 
        ui_context=state['ui_context'], 
        history=state['history']
    )
    return {"last_plan": plan}

def executor_node(state: AgentState):
    """Performs the action on the Pixel 6"""
    plan = state['last_plan']
    print(f"--- [EXECUTOR] Action: {plan.get('action_type')} ---")
    
    result = executor.execute(plan)
    
    history_entry = {
        "step": state['step_count'],
        "action": plan['action_type'],
        "status": result["status"],
        "reason": plan.get("reasoning", "")
    }
    return {"history": [history_entry]}

def should_continue(state: AgentState):
    plan = state["last_plan"]
  
    if plan.get("action_type") == "complete" or state["step_count"] >= 12:
        print("\n🏁 TASK FINISHED: Goal reached or step limit hit.")
        return "end"
    return "continue"

# --- Build the Graph ---

workflow = StateGraph(AgentState)

workflow.add_node("vision", vision_node)
workflow.add_node("planner", planner_node)
workflow.add_node("executor", executor_node)

workflow.set_entry_point("vision")
workflow.add_edge("vision", "planner")

workflow.add_conditional_edges(
    "planner",
    should_continue,
    {
        "continue": "executor",
        "end": END
    }
)

# Crucial: Loop back to vision after execution to see the new screen state
workflow.add_edge("executor", "vision")

app = workflow.compile()


def run_test_suite(file_path: str):
    # 1. Load the test cases
    if not os.path.exists(file_path):
        print(f" Error: {file_path} not found.")
        return

    with open(file_path, 'r') as f:
        test_cases = json.load(f)

    print(f" Loaded {len(test_cases)} test cases from {file_path}\n")

    # 2. Loop through each test case
    for test in test_cases:
        print(f" RUNNING TEST: [{test['id']}] {test['name']}")
        print(f" Description: {test['description']}")
    
        state = get_initial_state(goal=test['description'])
        
        # 3. Execute the Graph
        final_state = None
        for output in app.stream(state):
            for node_name, state_update in output.items():
                final_state = state_update # Track the last update
                if "last_plan" in state_update:
                    print(f" Agent Reasoning: {state_update['last_plan'].get('reasoning')}")

        print(f" Finished Test: {test['id']}\n" + "="*40 + "\n")

if __name__ == "__main__":
    
    adb.launch_app("md.obsidian")
    
    json_path = os.path.join("tests", "test_cases.json")
    
    run_test_suite(json_path)