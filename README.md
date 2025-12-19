
# mobile-qa-agent

Lightweight multi-agent mobile QA automation framework (Supervisor → Planner → Executor).

This repository implements a small, provider-agnostic multi-agent system that uses screenshots + LLM/vision models to plan and execute mobile UI tests via ADB. The project uses an AI provider abstraction (`src/tools/ai_provider.py`) so you can run with OpenAI (recommended) or OpenRouter as a fallback.

## Features

- Supervisor / Planner / Executor agent pattern
- VisionTools for screenshot encoding and visual prompts
- Centralized AI provider manager (`AIProviderManager`) 
- Percentage-based coordinates so tests scale across devices
- Rate limiting, retries with exponential backoff, and basic screenshot retention support

## Quick start

1. Create a Python virtual environment and install dependencies:

	python3 -m venv .venv
	source .venv/bin/activate
	pip install -r requirements.txt

2. Populate `.env` with API keys (do not commit real keys):

If you prefer OpenRouter, set `OPENROUTER_API_KEY` and `MODEL_PROVIDER_CHAIN=openrouter`.

3. Run a quick import check (developer sanity):

	export PYTHONPATH=src
	python3 -c "import tools.vision, tools.ai_provider, agents.planner, agents.supervisor, agents.executor, main; print('IMPORT_OK')"

4. Run the orchestrator (example):

	export PYTHONPATH=src
	python3 src/main.py --test-cases tests/test_cases.json

Note: The orchestrator requires `adb` on PATH for device interactions. If you don't have a device, use the dry-run mode or mock ADB during development.

## Provider behavior

- `src/tools/ai_provider.py` centralizes model calls. By default it prefers OpenAI when `OPENAI_API_KEY` is present. If you want to use OpenRouter, either set `MODEL_PROVIDER_CHAIN=openrouter` or only provide `OPENROUTER_API_KEY`.
- VisionTools encodes images as base64 and appends them to prompts when the provider doesn't support native image attachments. We can add provider-native image attachments later if desired.

## Troubleshooting

- adb not found: ensure Android platform-tools are installed and `adb` is on your PATH.
- API errors / rate limits: set `MODEL_PROVIDER_CHAIN` to a different provider if available, and configure sensible retries in `src/tools/ai_provider.py`.
- If tests fail with JSON parse errors in Planner/Supervisor responses, inspect the AI output in logs — the agents expect valid JSON only.

## Testing and development

- Add unit tests that mock `AIProviderManager` to avoid real API calls.
- Use small sample screenshots (in `tests/` or `screenshots/`) to exercise VisionTools local encoding.

## Contributing

Feel free to open issues or PRs. Small, focused changes (add tests, improve provider handling, add native image support) are welcome.

## License

MIT-style (update as appropriate for your project).

