
"""
Configuration settings for Nirvan AI Assistant
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
ACTIONS_DIR = BASE_DIR / "actions"

# Server configuration
HOST = "0.0.0.0"
PORT = 5000
DEBUG = True

# Speech and Audio settings
SPEECH_RECOGNITION_TIMEOUT = 5
SPEECH_RECOGNITION_PHRASE_TIMEOUT = 1
CONVERSATION_TIMEOUT = 300  # 5 minutes
AUDIO_DEVICE_INDEX = None  # Auto-detect
SAMPLE_RATE = 16000

# Wake word detection
WAKE_WORD_MODEL_PATH = "Nirvan_windows.ppn"
WAKE_WORD_SENSITIVITY = 0.5

# Gemini AI settings
GEMINI_MODEL = "gemini-1.5-flash"
GEMINI_TEMPERATURE = 0.7
GEMINI_MAX_TOKENS = 1000

# Email configuration (optional - set via environment variables)
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

# YouTube settings
YOUTUBE_SEARCH_RESULTS = 5
SELENIUM_HEADLESS = True
SELENIUM_TIMEOUT = 10

# Logging configuration
LOG_LEVEL = "INFO"
LOG_FILE = "nirvan_assistant.log"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Window settings
WINDOW_WIDTH = 380
WINDOW_HEIGHT = 620
WINDOW_RESIZABLE = False
WINDOW_MINIMIZED = True

# UI States
UI_STATES = {
    "WAITING": "waiting",
    "LISTENING": "listening", 
    "THINKING": "thinking",
    "SPEAKING": "speaking"
}

# Assistant states
class AssistantState:
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    ERROR = "error"

# File paths for resources
ICON_PATH = BASE_DIR / "icon.png"
RESPONSE_AUDIO_DIR = BASE_DIR

# API Keys (set via environment variables for security)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
PICOVOICE_ACCESS_KEY = os.getenv("PICOVOICE_ACCESS_KEY", "")

# Retry and timeout settings
MAX_RETRIES = 3
RETRY_DELAY = 1
CONNECTION_TIMEOUT = 30

# Security settings
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")

# Feature flags
ENABLE_EMAIL = True
ENABLE_YOUTUBE = True
ENABLE_SYSTEM_ACTIONS = True
ENABLE_WEB_UI = True
