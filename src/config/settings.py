import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

ADB_PATH = "adb"  # assumes adb in PATH
SCREENSHOT_DIR = "screenshots"
LOG_DIR = "logs"
# Whether to save per-step screenshots (can generate many files). Set to False to
# only save final screenshots and result.json per test.
SAVE_STEP_SCREENSHOTS = False

# Number of days to retain screenshot test directories. Older directories will be
# removed at test start. Set to 0 or None to disable automatic cleanup.
SCREENSHOT_RETENTION_DAYS = 7
