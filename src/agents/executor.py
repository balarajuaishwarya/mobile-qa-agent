import time

class ExecutorAgent:
    def __init__(self, adb):
        self.adb = adb
        # Cache screen size to avoid calling ADB every single tap
        self.screen_width, self.screen_height = self.adb.get_screen_size()

    def _scale_coords(self, x_norm, y_norm):
        """Converts 0-1000 coordinates to actual device pixels."""
        real_x = int((x_norm / 1000) * self.screen_width)
        real_y = int((y_norm / 1000) * self.screen_height)
        return real_x, real_y

    def execute(self, action):
        """Execute action safely with coordinate scaling"""
        action_type = action.get("action_type")
        params = action.get("parameters", {})

        print(f"    Executing: {action_type}")
        if "reasoning" in action:
            print(f"    Reason: {action['reasoning']}")

        try:
            if action_type == "tap":
                x_norm = params.get("x")
                y_norm = params.get("y")
                
                if x_norm is not None and y_norm is not None:
                   
                    real_x, real_y = self._scale_coords(x_norm, y_norm)
                    print(f"  Scaling: ({x_norm}, {y_norm}) -> Pixel: ({real_x}, {real_y})")
                    self.adb.tap(real_x, real_y)
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
                # Map common names to ADB keycodes if your ADB tool needs them
                self.adb.press_key(key)

            elif action_type == "swipe":
                # Scale swipe coordinates too
                s_x, s_y = self._scale_coords(params.get("start_x", 500), params.get("start_y", 800))
                e_x, e_y = self._scale_coords(params.get("end_x", 500), params.get("end_y", 200))
                self.adb.swipe(s_x, s_y, e_x, e_y)

            elif action_type == "wait":
                time.sleep(params.get("seconds", 2))
            
            elif action_type == "complete":
                print("  Task flagged as complete.")

            return {
                "action": action_type,
                "status": "success",
                "params": params
            }

        except Exception as e:
            print(f"  Execution error: {e}")
            return {
                "action": action_type,
                "status": "failed",
                "error": str(e)
            }


    def execute_action(self, action):
        """Compatibility wrapper for execute() used by TestRunner"""
        return self.execute(action)