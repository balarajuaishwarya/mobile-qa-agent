"""
Configuration Settings for Mobile QA Multi-Agent System
Centralized config for easy tuning and deployment
"""

import os
from pathlib import Path
try:
    # Optional: load .env from repo root if python-dotenv is available
    from dotenv import load_dotenv
    dotenv_path = Path(__file__).parent.parent / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path)
except Exception:
    # dotenv not required; environment variables will still be used
    pass

# ============================================================================
# PROJECT PATHS
# ============================================================================
BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / "logs"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
RESULTS_DIR = BASE_DIR / "results"

# Create directories
for dir_path in [LOGS_DIR, SCREENSHOTS_DIR, RESULTS_DIR]:
    dir_path.mkdir(exist_ok=True)

# ============================================================================
# AI MODEL CONFIGURATION
# ============================================================================
# Choose provider: "gemini" or "openrouter"
AI_PROVIDER = "openrouter"  # Change to "gemini" if you want to use Gemini directly

# OpenRouter Configuration (RECOMMENDED - supports multiple models)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL")


# Gemini Direct Configuration 
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash-exp"  # Direct Gemini

# Model parameters
TEMPERATURE = 0.1  # Lower = more consistent JSON outputs
MAX_TOKENS = 4096
TIMEOUT = 45  # API timeout in seconds

# ============================================================================
# AGENT BEHAVIOR SETTINGS
# ============================================================================
MAX_STEPS_PER_TEST = 15  # Maximum actions before forcing evaluation
ACTION_DELAY = 1.5  # Seconds between actions (UI settling time)
SCREENSHOT_DELAY = 0.5  # Seconds after screenshot
TEST_DELAY = 3.0  # Seconds between different tests

# Retry configuration
MAX_RETRIES = 3  # Retry failed API calls
RETRY_DELAY = 2  # Seconds between retries

# ============================================================================
# ADB SETTINGS
# ============================================================================
ADB_TIMEOUT = 30  # Command timeout
DEFAULT_DEVICE = None  # Auto-detect or specify "emulator-5554"
OBSIDIAN_PACKAGE = "md.obsidian"
APP_LAUNCH_WAIT = 4  # Seconds to wait after launching app

# Screen configuration
COORDINATE_SCALE = 1000  # Normalized coordinate system (0-1000)
DEFAULT_SCREEN_SIZE = (1080, 2400)  # Fallback if detection fails

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
SAVE_SCREENSHOTS = True  # Keep screenshots after test
SAVE_LOGS = True  # Save detailed logs
VERBOSE_OUTPUT = True  # Print agent reasoning

# ============================================================================
# RATE LIMITING
# ============================================================================
MIN_API_DELAY = 1.0  # Minimum seconds between API calls
RATE_LIMIT_ENABLED = True

# ============================================================================
# TEST CONFIGURATION
# ============================================================================
TEST_CASES_FILE = BASE_DIR / "tests" / "test_cases.json"

# Default test suite
DEFAULT_TESTS = [
    {
        "id": "test_1",
        "name": "Create Vault",
        "goal": "Open Obsidian, create a new Vault named 'InternVault', and enter the vault.",
        "expected": "PASS",
        "max_steps": 12
    },
    {
        "id": "test_2", 
        "name": "Create Note",
        "goal": "Create a new note titled 'Meeting Notes' and type 'Daily Standup' into the body.",
        "expected": "PASS",
        "max_steps": 10
    },
    {
        "id": "test_3",
        "name": "Verify Appearance Color",
        "goal": "Go to Settings and verify that the 'Appearance' tab icon is Red.",
        "expected": "FAIL",  # It's actually gray/default
        "max_steps": 10
    },
    {
        "id": "test_4",
        "name": "Find Print to PDF",
        "goal": "Find and click the 'Print to PDF' button in the main file menu.",
        "expected": "FAIL",  # Doesn't exist in mobile
        "max_steps": 10
    }
]

# ============================================================================
# FEATURE FLAGS
# ============================================================================
ENABLE_VISION_ANALYSIS = True  # Use AI vision for UI element detection
ENABLE_SMART_RETRY = True  # Retry with different strategy on failure
ENABLE_HISTORY_LEARNING = True  # Use execution history for planning
ENABLE_PARALLEL_TESTS = False  # Run tests in parallel (experimental)

# ============================================================================
# PERFORMANCE OPTIMIZATION
# ============================================================================
CACHE_SCREEN_SIZE = True  # Cache device screen dimensions
BATCH_SCREENSHOTS = False  # Experimental: batch screenshot analysis
COMPRESS_IMAGES = True  # Reduce image size for API calls
IMAGE_QUALITY = 85  # JPEG quality (1-100)
MAX_IMAGE_DIMENSION = 1920  # Resize large images


def validate_config() -> list:
    """Return a list of configuration error messages (empty if OK).

    This function is used by the main runner to fail fast when required
    API keys or settings are missing.
    """
    errors = []
    # Validate provider-specific keys
    if AI_PROVIDER == "openrouter":
        if not OPENROUTER_API_KEY:
            errors.append("OPENROUTER_API_KEY not set. Get free key from: https://openrouter.ai/keys")
    elif AI_PROVIDER == "gemini":
        if not GEMINI_API_KEY:
            errors.append("GEMINI_API_KEY not set. Please provide GEMINI_API_KEY in environment or .env")

    return errors


