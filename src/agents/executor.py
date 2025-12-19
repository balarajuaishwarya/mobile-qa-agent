"""
Executor Agent - Executes planned actions
"""
from tools.adb import ADBTools
from tools.vision import VisionTools
import time


class ExecutorAgent:
    def __init__(self, adb_tools, vision_tools):
        self.adb = adb_tools
        self.vision = vision_tools
    
    def execute_action(self, action):
        """
        Execute the planned action
        
        Returns: dict with execution result
        {
            "success": bool,
            "message": str,
            "details": dict
        }
        """
        
        action_type = action.get("action_type")
        parameters = action.get("parameters", {})
        
        print(f"\nEXECUTOR: Executing {action_type}")
        print(f"   Parameters: {parameters}")
        print(f"   Reasoning: {action.get('reasoning', 'N/A')}")
        
        try:
            if action_type == "tap":
                return self._execute_tap(parameters)
            
            elif action_type == "type":
                return self._execute_type(parameters)
            
            elif action_type == "press_key":
                return self._execute_press_key(parameters)
            
            elif action_type == "swipe":
                return self._execute_swipe(parameters)
            
            elif action_type == "wait":
                return self._execute_wait(parameters)
            
            elif action_type == "verify":
                return self._execute_verify(parameters)
            
            elif action_type == "complete":
                return {
                    "success": True,
                    "message": "Test execution complete, ready for evaluation",
                    "details": {}
                }
            
            else:
                return {
                    "success": False,
                    "message": f"Unknown action type: {action_type}",
                    "details": {}
                }
        
        except Exception as e:
            return {
                "success": False,
                "message": f"Execution error: {str(e)}",
                "details": {"error": str(e)}
            }
    
    def _execute_tap(self, params):
        """Execute tap action"""
        x_percent = params.get("x_percent", 50)
        y_percent = params.get("y_percent", 50)
        
        # Get screen size
        width, height = self.adb.get_screen_size()
        
        # Convert percentage to actual coordinates
        x = int((x_percent / 100) * width)
        y = int((y_percent / 100) * height)
        
        success = self.adb.tap(x, y)
        
        return {
            "success": success,
            "message": f"Tapped at ({x}, {y}) - {x_percent}%, {y_percent}%",
            "details": {"x": x, "y": y, "x_percent": x_percent, "y_percent": y_percent}
        }
    
    def _execute_type(self, params):
        """Execute type action"""
        text = params.get("text", "")
        
        if not text:
            return {
                "success": False,
                "message": "No text provided to type",
                "details": {}
            }
        
        success = self.adb.type_text(text)
        
        return {
            "success": success,
            "message": f"Typed text: '{text}'",
            "details": {"text": text}
        }
    
    def _execute_press_key(self, params):
        """Execute press key action"""
        key = params.get("key", "").lower()
        
        key_map = {
            "back": 4,
            "home": 3,
            "enter": 66,
            "backspace": 67
        }
        
        if key not in key_map:
            return {
                "success": False,
                "message": f"Unknown key: {key}",
                "details": {}
            }
        
        success = self.adb.press_key(key_map[key])
        
        return {
            "success": success,
            "message": f"Pressed {key} key",
            "details": {"key": key}
        }
    
    def _execute_swipe(self, params):
        """Execute swipe action"""
        start_x_percent = params.get("start_x_percent", 50)
        start_y_percent = params.get("start_y_percent", 80)
        end_x_percent = params.get("end_x_percent", 50)
        end_y_percent = params.get("end_y_percent", 20)
        duration = params.get("duration", 300)
        
        width, height = self.adb.get_screen_size()
        
        start_x = int((start_x_percent / 100) * width)
        start_y = int((start_y_percent / 100) * height)
        end_x = int((end_x_percent / 100) * width)
        end_y = int((end_y_percent / 100) * height)
        
        success = self.adb.swipe(start_x, start_y, end_x, end_y, duration)
        
        return {
            "success": success,
            "message": f"Swiped from ({start_x}, {start_y}) to ({end_x}, {end_y})",
            "details": {
                "start": (start_x, start_y),
                "end": (end_x, end_y)
            }
        }
    
    def _execute_wait(self, params):
        """Execute wait action"""
        seconds = params.get("seconds", 2)
        time.sleep(seconds)
        
        return {
            "success": True,
            "message": f"Waited {seconds} seconds",
            "details": {"seconds": seconds}
        }
    
    def _execute_verify(self, params):
        """Execute verification action"""
        verification_type = params.get("verification_type")
        target = params.get("target")
        expected = params.get("expected")
        
        # Take screenshot for verification
        screenshot = self.adb.get_screenshot()
        
        if verification_type == "text":
            result = self.vision.verify_text(screenshot, expected)
        elif verification_type == "element":
            result = self.vision.check_element_exists(screenshot, target)
        elif verification_type == "color":
            result = self.vision.verify_color(screenshot, target, expected)
        else:
            return {
                "success": False,
                "message": f"Unknown verification type: {verification_type}",
                "details": {}
            }
        
        return {
            "success": True,
            "message": f"Verification completed: {verification_type}",
            "details": {
                "verification_type": verification_type,
                "result": result
            }
        }