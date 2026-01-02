"""Vision Tools"""
from tools.ai_provider import AIProvider


class VisionTools:
    def __init__(self, provider: AIProvider):
        self.ai = provider

    def describe_screen(self, image):
        """Get screen description"""
        if image is None:
            return "Error: No screenshot available"
        
        prompt = """Describe this mobile app screenshot concisely.
Include:
- App name and current screen
- Visible buttons (with text labels)
- Text fields
- Current state

Be specific and brief."""
        
        try:
            result = self.ai.generate_response(prompt, image)
            # Handle both string and dict responses
            if isinstance(result, dict):
                return result.get('description', str(result))
            return str(result)
        except Exception as e:
            return f"Error: {str(e)}"