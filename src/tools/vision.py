import json
from typing import Dict, Optional
from PIL import Image


class VisionAnalyzer:
    """
    Analyzes mobile screenshots to extract UI elements
    
    Key Features:
    - Normalized coordinates (0-1000) for device independence
    - Element type detection (button, input, link, etc.)
    - Blocking screen detection (popups, loading, etc.)
    - Structured output for agent planning
    """
    
    SYSTEM_PROMPT = """You are a Mobile UI Vision System for test automation.

TASK: Analyze this screenshot and identify ALL interactive UI elements.

COORDINATE SYSTEM:
- Use normalized 0-1000 scale
- (0, 0) = Top-Left corner
- (1000, 1000) = Bottom-Right corner
- Example: Center of screen = (500, 500)

ELEMENT TYPES:
- button: Clickable buttons, icons with actions
- input: Text fields, search boxes
- toggle: Switches, checkboxes, radio buttons
- link: Clickable text, navigation items
- tab: Tab bar items, navigation tabs

REQUIRED JSON OUTPUT:
{
  "screen_summary": "Brief description of current screen (e.g., 'Home screen with app icons')",
  "blocking_screen": false,
  "elements": [
    {
      "text": "Exact visible text or icon description",
      "type": "button",
      "x": 500,
      "y": 300,
      "description": "What clicking this does (e.g., 'Opens settings menu')"
    }
  ]
}

CRITICAL RULES:
1. ONLY valid JSON - no markdown, no commentary
2. Include EVERY clickable element you can see
3. Use descriptive text for icons (e.g., "gear icon" not just "icon")
4. Set blocking_screen=true ONLY for: loading screens, error popups, permission requests
5. Coordinates must be integers 0-1000
6. Be precise with element positions as it is the core of the entire automation testing.

EXAMPLES:
- App icon in middle: {"text": "Obsidian", "type": "button", "x": 500, "y": 400}
- Search bar at top: {"text": "Search", "type": "input", "x": 500, "y": 100}
- Settings gear icon: {"text": "settings gear", "type": "button", "x": 900, "y": 100}
"""
    
    def __init__(self, ai_provider):
        """
        Initialize vision analyzer
        
        Args:
            ai_provider: AI provider instance (GeminiProvider)
        """
        self.ai = ai_provider
        self.analysis_count = 0
    
    def analyze_screen(self, image: Optional[Image.Image]) -> Dict:
        """
        Analyze screenshot and extract UI elements
        
        Args:
            image: PIL Image of screenshot
            
        Returns:
            Dictionary with screen_summary, elements list, and blocking_screen flag
        """
        if image is None:
            return self._error_response("No screenshot provided")
        
        try:
            self.analysis_count += 1
            
            response = self.ai.generate_response(self.SYSTEM_PROMPT, image)
            
            # Validate and clean response
            return self._validate_response(response)
            
        except Exception as e:
            return self._error_response(f"Vision analysis failed: {str(e)}")
    
    def _validate_response(self, response: any) -> Dict:
        """
        Validate and normalize AI response
        
        Ensures response has required fields with correct types
        """
        # If string, try to parse
        if isinstance(response, str):
            try:
                response = json.loads(self._clean_json_string(response))
            except json.JSONDecodeError:
                return self._error_response(f"Invalid JSON: {response[:100]}")
        
        # Ensure it's a dictionary
        if not isinstance(response, dict):
            return self._error_response("Response is not a JSON object")
        
        # Set defaults for missing fields
        validated = {
            "screen_summary": response.get("screen_summary", "Unknown screen"),
            "blocking_screen": bool(response.get("blocking_screen", False)),
            "elements": []
        }
        
        # Validate elements array
        raw_elements = response.get("elements", [])
        if isinstance(raw_elements, list):
            for elem in raw_elements:
                if isinstance(elem, dict):
                    validated_elem = self._validate_element(elem)
                    if validated_elem:
                        validated["elements"].append(validated_elem)
        
        return validated
    
    def _validate_element(self, element: Dict) -> Optional[Dict]:
        """
        Validate a single UI element
        
        Returns None if element is invalid
        """
        try:
            # Required fields
            if "x" not in element or "y" not in element:
                return None
            
            x = int(element["x"])
            y = int(element["y"])
            
            # Coordinate bounds check
            if not (0 <= x <= 1000 and 0 <= y <= 1000):
                print(f"  Coordinates out of bounds: ({x}, {y})")
                return None
            
            return {
                "text": str(element.get("text", "unlabeled")),
                "type": str(element.get("type", "button")),
                "x": x,
                "y": y,
                "description": str(element.get("description", ""))
            }
        except (ValueError, TypeError):
            return None
    
    def _clean_json_string(self, text: str) -> str:
        """Remove markdown and extra text from JSON string"""
        text = text.strip()
        
        # Remove markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        
        # Find JSON object boundaries
        start = text.find('{')
        end = text.rfind('}')
        
        if start != -1 and end != -1:
            return text[start:end + 1]
        
        return text
    
    def _error_response(self, error_msg: str) -> Dict:
        """Return standardized error response"""
        return {
            "screen_summary": f"Error: {error_msg}",
            "blocking_screen": False,
            "elements": [],
            "error": error_msg
        }
    
    def format_for_planner(self, analysis: Dict) -> str:
        """
        Format vision analysis for planner consumption
        
        Returns:
            Human-readable string describing the screen
        """
        if "error" in analysis:
            return f"ERROR: {analysis['error']}"
        
        lines = [
            f"SCREEN: {analysis['screen_summary']}",
            f"BLOCKING: {'Yes' if analysis['blocking_screen'] else 'No'}",
            ""
        ]
        
        if analysis['elements']:
            lines.append(f"FOUND {len(analysis['elements'])} INTERACTIVE ELEMENTS:")
            lines.append("")
            
            for i, elem in enumerate(analysis['elements'], 1):
                lines.append(
                    f"{i}. [{elem['type'].upper()}] '{elem['text']}' "
                    f"at ({elem['x']}, {elem['y']}) - {elem['description']}"
                )
        else:
            lines.append("No interactive elements detected")
        
        return "\n".join(lines)
    
    def get_stats(self) -> Dict:
        """Get analyzer statistics"""
        return {
            "total_analyses": self.analysis_count
        }