"""Vision Tools"""
from tools.ai_provider import AIProvider


class VisionTools:
    #Dependency Injection of AI Provider
    def __init__(self, provider: AIProvider):
        self.ai = provider

    def describe_screen(self, image):
        """Get screen description"""
        if image is None:
            return "Error: No screenshot available"
        
        prompt = """
You are a mobile UI automation vision engine.

You are given a screenshot of a mobile app.
Your task is to extract ONLY actionable UI information for automation.

INSTRUCTIONS (FOLLOW STRICTLY):
1. Identify all VISIBLE and CLICKABLE UI elements only.
2. Clickable elements include: buttons, links, selectable cards, input fields.
3. Ignore decorative text, icons without labels, images, or background content.
4. For each clickable element:
   - Extract the EXACT visible text (empty string if no text).
   - Identify its type (button | input | link | card | toggle | unknown).
   - Estimate the tap coordinate (x, y) in SCREEN PIXELS.
5. Coordinates must be within the element’s visible bounds.
6. If the screen blocks progress (e.g., onboarding, permissions, sync screens),
   explicitly mark it as "blocking_screen": true.
7. DO NOT guess elements that are not clearly visible.

OUTPUT RULES (VERY IMPORTANT):
- Output MUST be VALID JSON.
- DO NOT include markdown, explanations, or comments.
- DO NOT wrap JSON in ``` blocks.
- If no clickable elements exist, return an empty list.

OUTPUT FORMAT:
{
  "screen_name": "<short descriptive name>",
  "blocking_screen": true | false,
  "elements": [
    {
      "text": "<visible text or empty string>",
      "type": "<button|input|link|card|toggle|unknown>",
      "x": number,
      "y": number
    }
  ]
}
"""
        try:
            result = self.ai.generate_response(prompt, image)
            # Handle both string and dict responses
            if isinstance(result, dict):
                return result.get('description', str(result))
            return str(result)
        except Exception as e:
            return f"Error: {str(e)}"