"""
Simple AI provider manager (OpenAI primary, mock fallback)
"""
import os

try:
    import openai
except Exception:
    openai = None


class ProviderResponse:
    def __init__(self, text):
        self.text = text


class AIProviderManager:
    def __init__(self, chain=None):
        # chain is unused for now; keep for compatibility
        self.chain = chain or os.getenv('MODEL_PROVIDER_CHAIN', 'openai')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if openai and self.openai_api_key:
            openai.api_key = self.openai_api_key

    def generate_content(self, prompt, image=None, max_tokens=1024, temperature=0.2):
        """Return ProviderResponse with .text containing model output."""
        # Prefer OpenAI if SDK available and API key present
        if openai and self.openai_api_key:
            try:
                resp = openai.ChatCompletion.create(
                    model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
                    messages=[{'role': 'user', 'content': prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                # Extract text
                content = ''
                if resp and 'choices' in resp and len(resp.choices) > 0:
                    content = resp.choices[0].message.get('content') if hasattr(resp.choices[0], 'message') else resp.choices[0].get('message', {}).get('content', '')
                    if not content:
                        # Older openai versions
                        content = resp.choices[0].get('text', '')
                return ProviderResponse(content or '')
            except Exception as e:
                # fallback to mock
                return ProviderResponse(f"MOCK_RESPONSE: OpenAI call failed: {e}")

        # Mock response when no provider configured
        excerpt = prompt[:200].replace('\n', ' ')
        return ProviderResponse(f"MOCK_RESPONSE: No provider available. Prompt excerpt: {excerpt}")
