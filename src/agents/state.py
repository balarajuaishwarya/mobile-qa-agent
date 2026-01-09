import operator
from typing import Annotated, Dict, List, TypedDict, Optional
from PIL import Image

class AgentState(TypedDict):
    goal: str
    ui_context: str
    history: Annotated[List[Dict], operator.add]
    last_plan: Dict
    screenshot: Optional[Image.Image]
    step_count: int
    is_complete: bool

def get_initial_state(goal: str) -> AgentState:
    return {
        "goal": goal,
        "ui_context": "",
        "history": [],
        "last_plan": {},
        "screenshot": None,
        "step_count": 0,
        "is_complete": False
    }