"""Configuration settings for the video carousel workflow."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
FONTS_DIR = BASE_DIR / "fonts"
AUDIO_DIR = BASE_DIR / "audio"
OUTPUT_DIR = BASE_DIR / "output"
TEMP_DIR = BASE_DIR / "images_temp"

# Video settings (TikTok 9:16)
OUTPUT_SIZE = (1080, 1920)
FPS = 30
DURATION_PER_SLIDE = 3  # seconds
CROSSFADE_DURATION = 0.5

# API Keys
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "")

# DeepSeek settings
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

# Image source priority
IMAGE_SOURCES = ["pexels", "pixabay"]

# Font settings
DEFAULT_FONT_SIZE = 72
DEFAULT_FONT_FILE = "Roboto-Bold.ttf"

# Voice settings (edge-tts, 100% free)
DEFAULT_VOICE = "vivienne"  # Options: vivienne, denise, henri, remy
VOICE_RATE = "+0%"  # Speed: "-10%" slower, "+10%" faster
