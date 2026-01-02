"""Executor Agent - Fixed version"""


class ExecutorAgent:
    def __init__(self, adb):
        self.adb = adb

    def execute(self, action):
        """Execute action safely"""
        action_type = action.get("action_type")
        params = action.get("parameters", {})

        print(f"   Executing: {action_type}")
        print(f"   Params: {params}")

        try:
            if action_type == "tap":
                x = params.get("x")
                y = params.get("y")
                if x and y:
                    self.adb.tap(x, y)
                else:
                    raise ValueError("Missing x or y for tap")

            elif action_type == "type":
                text = params.get("text", "")
                if text:
                    self.adb.type_text(text)
                else:
                    raise ValueError("Missing text for type")

            elif action_type == "press_key":
                key = params.get("key", "enter")
                self.adb.press_key(key)

            elif action_type == "swipe":
                self.adb.swipe(
                    params.get("start_x", 540),
                    params.get("start_y", 1500),
                    params.get("end_x", 540),
                    params.get("end_y", 500)
                )

            elif action_type == "wait":
                import time
                time.sleep(params.get("seconds", 2))
            
            elif action_type == "complete":
                pass  # No execution needed

            return {
                "action": action_type,
                "status": "success",
                "params": params
            }

        except Exception as e:
            print(f" Execution error: {e}")
            return {
                "action": action_type,
                "status": "failed",
                "error": str(e)
            }