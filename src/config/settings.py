import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

ADB_PATH = "adb"  # assumes adb in PATH
SCREENSHOT_DIR = "screenshots"
LOG_DIR = "logs"
