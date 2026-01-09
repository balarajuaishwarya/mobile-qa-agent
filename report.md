# Framework Decision Memo

## Selected Framework: Custom Multi-Agent System with Gemini Vision

### Executive Summary
After evaluating multiple agentic frameworks for mobile QA automation, I chose to implement a **custom multi-agent orchestration system** using **Google's Gemini 2.0 Flash with Vision API** rather than using pre-built frameworks like Agent S or Google ADK.

---
## Framework Options Evaluated

### 1. **Simular's Agent S**
- **Pros**: Specifically designed for mobile UI automation, handles Android interactions natively
- **Cons**: Less flexibility for custom agent roles, steeper learning curve, limited documentation
- **Verdict**: Good for pure automation but overkill for this specific supervisor-planner-executor pattern

### 2. **Google's Agent Development Kit (ADK)**
- **Pros**: Well-documented, integrates with Gemini, general-purpose agent framework
- **Cons**: More complex than needed, adds unnecessary abstraction layers
- **Verdict**: Powerful but overengineered for a 3-agent system

### 3. **LangGraph**
- **Pros**: Excellent for multi-agent workflows, state management, clear graph-based architecture
- **Cons**: Requires additional dependencies, adds complexity to simple coordination
- **Verdict**: Very Strong candidate but adds overhead for straightforward sequential flow

### 4. **Custom Implementation with Gemini Vision API (SELECTED)**
- **Pros**: 
  - Direct control over agent behavior and prompts
  - Minimal dependencies (just google-generativeai)
  - Gemini 2.0 Flash is free and excellent for vision tasks, although rate limited on free tier
  - Easy to debug and modify
  - Perfect for the supervisor-planner-executor pattern
- **Cons**: 
  - No built-in state management (handled manually)
  - No automatic retries or error handling (implemented custom)
- **Verdict**: Best fit for this project as of now

State Management Control: While LangGraph offers built-in state, for a 3-agent mobile system, "state" is mostly the current screenshot, the task history, and the next planned coordinate. Managing this in a simple Python dictionary or a TypedDict is often cleaner than learning the "StateGraph" syntax.

Latency & Overhead: Mobile automation is already slow (ADB + Screenshot + AI Processing). Adding a heavy framework layer can add 500ms–1s of overhead per turn. Direct call to Gemini 2.0 Flash minimizes this "framework tax."

Vision Precision: Gemini 2.0 Flash has significantly improved Spatial Understanding. By writing our own prompts, we can tune the model specifically to recognize mobile UI patterns (like the difference between a "hamburger menu" and a "back button") better than a generic framework might.

## Decision Rationale

### Why Custom Implementation?

1. **Simplicity**: The supervisor-planner-executor pattern is inherently sequential. We don't need complex graph-based routing or parallel agent execution.

2. **Vision-First Approach**: Mobile QA fundamentally requires understanding screenshots. Gemini 2.0 Flash excels at vision tasks and is free to use (though has heavy rate limitor for the free tier).

3. **Prompt Engineering Control**: Custom implementation gives us full control over agent prompts, which is critical for:
   - Planner: Generating precise action coordinates
   - Supervisor: Distinguishing between bugs vs execution failures
   - Executor: Handling edge cases gracefully

4. **Modularity**: Clean separation between:
   - `adb.py`: Android device control
   - `vision.py`: Vision API wrappers
   - Agent classes: Pure business logic
   - `main.py`: Orchestration - Custom
   - `app.py`: Also implemented the lanGraph flow as it is a next strong candidate in case we really decide to use an Agentic framework.
   - `ai_provider.py`: This will allow us to easily switch the models.

5. **Easy Model Swapping**: The architecture allows easy replacement of Gemini with Claude, GPT-4V, or any other vision model by changing a single configuration.

---

## Implementation Architecture

**Supervisor**:
- Receives: Test case, action history, current screenshot
- Decides: Continue testing OR evaluate final result
- Outputs: Pass/Fail with bug classification

**Planner**:
- Receives: Test goal, screen state, action history
- Analyzes: Screenshot using Gemini Vision
- Outputs: Structured action (tap, type, swipe, verify)

**Executor**:
- Receives: Planned action
- Executes: ADB commands
- Outputs: Success/failure status

---

## Key Technical Decisions

### 1. **Coordinate System: Percentage-Based**
- Planner outputs coordinates
- Handles different screen sizes automatically

### 2. **Action Types**
- `tap`: Click at coordinates
- `type`: Input text
- `press_key`: Back, enter, home buttons
- `swipe`: Gestures
- `verify`: Assertions (text, element, color)
- `complete`: Signal test end

### 3. **Error Handling Strategy**
- Distinguish "technical failure" (couldn't click) from "test failure" (element missing)
- Supervisor makes final determination based on context
- All actions logged with screenshots for debugging

## Conclusion

The custom multi-agent approach implemented in this repo is intentionally lightweight and provider-agnostic. It focuses on clarity, debuggability, and easy substitution of the underlying AI provider.  This matches the code in the repository and avoids adding unused frameworks or unnecessary complexity.