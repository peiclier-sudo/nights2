"""Configuration settings for the marketing design pipeline."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
FONTS_DIR = BASE_DIR / "fonts"
OUTPUT_DIR = BASE_DIR / "output"

# API Keys
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

# DeepSeek settings
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

# Font settings
DEFAULT_FONT_FILE = "Roboto-Bold.ttf"
