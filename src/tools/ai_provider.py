"""
AI Provider Abstraction

Provides a pluggable manager that can try multiple AI providers in order
and return the first successful response. Providers supported: gemini, openai,
mock. Configure provider order via the MODEL_PROVIDER_CHAIN env var (comma sep).

The manager exposes generate_content(prompt, image=None) and returns a small
object with a `.text` attribute to match existing call sites.
"""
import os
import json
from dataclasses import dataclass

try:
    import openai
except Exception:
    openai = None

@dataclass
class ProviderResponse:
    text: str


class AIProviderManager:
    def __init__(self, chain=None):
        # chain is comma-separated provider names, e.g. 'openai,mock'
        # Default to OpenAI first, then mock fallback.
        self.chain = (chain or os.getenv('MODEL_PROVIDER_CHAIN') or 'openai,mock')
        self.providers = [p.strip().lower() for p in self.chain.split(',') if p.strip()]
        # configure openai if available
        self.openai_key = os.getenv('OPENAI_API_KEY')
        if openai and self.openai_key:
            openai.api_key = self.openai_key

    def generate_content(self, prompt, image=None, max_retries=1):
        """Try providers in order; return ProviderResponse on first success."""
        last_err = None
        for provider in self.providers:
            try:
                if provider == 'openai':
                    if openai and self.openai_key:
                        # Basic text-only fallback: include note if image present
                        final_prompt = prompt
                        if image is not None:
                            final_prompt = f"[IMAGE ATTACHED]\n{prompt}"

                        # Use ChatCompletion (most compatible). This will work for text prompts.
                        try:
                            resp = openai.ChatCompletion.create(
                                model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
                                messages=[{'role': 'user', 'content': final_prompt}],
                                max_tokens=1024,
                                temperature=0.2,
                            )
                            text = resp.choices[0].message.content
                            return ProviderResponse(text=text)
                        except Exception as e:
                            # Try Responses API if ChatCompletion fails
                            try:
                                resp = openai.responses.create(model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'), input=final_prompt)
                                text = resp.output_text
                                return ProviderResponse(text=text)
                            except Exception as e2:
                                last_err = e2
                    else:
                        last_err = Exception('OpenAI not configured or SDK missing')

                elif provider == 'mock' or provider == 'fallback':
                    # Provide a harmless mock response: echo a short excerpt
                    snippet = (prompt[:500] + '...') if len(prompt) > 500 else prompt
                    text = f"MOCK_RESPONSE: No provider available. Prompt excerpt:\n{snippet}"
                    return ProviderResponse(text=text)

                else:
                    last_err = Exception(f'Unknown provider: {provider}')

            except Exception as e:
                last_err = e
                # try next provider
                continue

        # If we reach here, nothing worked
        raise RuntimeError(f'All providers failed. Last error: {last_err}')
