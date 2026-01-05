
# mobile-qa-agent

Lightweight multi-agent mobile QA automation framework.

This repository implements a compact, provider-agnostic multi-agent system that uses screenshots + LLM/vision models to plan and execute mobile UI tests via ADB. The project centralizes model calls in `src/tools/ai_provider.py` and uses `VisionTools` screenshots for model input.

## Key changes reflected in this repo

- The AI provider encodes screenshots as data URLs and sends them with prompts when provider-native image attachments aren't available.
- Conservative built-in rate limiting and retry/backoff are applied in `AIProvider` to help avoid API throttling.

## Features

- Supervisor, Planner snd Executor agent pattern
- VisionTools for screenshot encoding and visual prompts
- Centralized AI provider (`src/tools/ai_provider.py`) with retries and rate limiting. This helps switching the models easily when needed.

## Quick start

1. Create and activate a Python virtual environment and install dependencies:

	python3 -m venv .venv
	source .venv/bin/activate
	pip install -r requirements.txt

2. Populate `.env` with API keys.

3. Run a quick import check:

	python3 -c "import tools.vision, tools.ai_provider, agents.planner, agents.supervisor, agents.executor, main; print('IMPORT_OK')"

4. Run the orchestrator (example):

	python3 src/main.py 

Note: `adb` is required on PATH for real device interactions. Use dry-run mode or mock ADB for development without a device.

## Provider behavior

- `src/tools/ai_provider.py` centralizes model calls. The screenshots along with prompts are input to the model.
- `AIProvider` implements conservative rate limiting (default min delay ~2.5s) and retries with backoff for transient errors.

## Troubleshooting

- adb not found: install Android platform-tools and ensure `adb` is on your PATH.
- API errors / rate limits: check `.env`, switch provider via `MODEL_PROVIDER_CHAIN`, and adjust retry/backoff in `src/tools/ai_provider.py` if needed.

