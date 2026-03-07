#!/usr/bin/env python3
"""
Nights2 - TikTok Carousel Video Generator

Workflow:
    1. Generate slide text + image keywords + voiceover via DeepSeek API
    2. Download matching images from Pexels/Pixabay (free)
    3. Add text overlays with Pillow
    4. Generate AI voiceover with Edge-TTS (free)
    5. Assemble into a 9:16 video with MoviePy + FFmpeg

Usage:
    python main.py "Les bienfaits du sommeil"
    python main.py --slides 8 --music audio/chill.mp3 "Crypto pour débutants"
    python main.py --no-voice "Recette rapide"
    python main.py --voice remy "Les bienfaits du sport"
"""

import argparse
import logging
import random
import sys
from pathlib import Path

from src.utils.config import TEMP_DIR, OUTPUT_DIR, AUDIO_DIR, DEFAULT_VOICE, VOICE_RATE
from src.content.generator import generate_carousel_content
from src.images.downloader import download_images
from src.images.text_overlay import add_text_to_image
from src.video.assembler import create_carousel_video
from src.voice import generate_voiceover_for_slides, list_voices

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def find_background_music() -> Path | None:
    """Find a random music file from the audio directory."""
    audio_files = list(AUDIO_DIR.glob("*.mp3")) + list(AUDIO_DIR.glob("*.wav"))
    if audio_files:
        return random.choice(audio_files)
    return None


def run(
    topic: str,
    num_slides: int = 6,
    music_path: Path | None = None,
    voice_name: str = DEFAULT_VOICE,
    enable_voice: bool = True,
) -> Path:
    """
    Run the full carousel generation pipeline.

    Args:
        topic: Subject for the carousel.
        num_slides: Number of slides to generate.
        music_path: Optional path to background music.
        voice_name: Voice to use for narration.
        enable_voice: Whether to generate voiceover.

    Returns:
        Path to the generated video.
    """
    total_steps = 5 if enable_voice else 4
    step = 0

    # Step 1: Generate content with DeepSeek
    step += 1
    logger.info("Step %d/%d: Generating content for '%s'", step, total_steps, topic)
    content = generate_carousel_content(topic, num_slides)
    slides_text = content["slides"]
    keywords = content["keywords"]
    voiceover_texts = content.get("voiceover", slides_text)

    logger.info("Generated %d slides:", len(slides_text))
    for i, text in enumerate(slides_text):
        logger.info("  Slide %d: %s (keyword: %s)", i + 1, text, keywords[i])

    # Step 2: Download images
    step += 1
    logger.info("Step %d/%d: Downloading images", step, total_steps)
    raw_images = download_images(keywords)

    # Step 3: Add text overlays
    step += 1
    logger.info("Step %d/%d: Adding text overlays", step, total_steps)
    final_images = []
    for i, (img_path, text) in enumerate(zip(raw_images, slides_text)):
        output = TEMP_DIR / f"final_{i}.png"
        add_text_to_image(img_path, text, output)
        final_images.append(output)

    # Step 4: Generate voiceover (free with edge-tts)
    voice_data = None
    if enable_voice:
        step += 1
        logger.info("Step %d/%d: Generating AI voiceover (voice: %s)", step, total_steps, voice_name)
        voice_data = generate_voiceover_for_slides(
            voiceover_texts,
            voice_name=voice_name,
            rate=VOICE_RATE,
        )
        total_voice_duration = sum(v["duration"] for v in voice_data)
        logger.info("Total voiceover duration: %.1fs", total_voice_duration)

    # Step 5: Assemble video
    step += 1
    logger.info("Step %d/%d: Assembling video", step, total_steps)
    if music_path is None:
        music_path = find_background_music()

    output_video = create_carousel_video(
        final_images,
        voice_data=voice_data,
        music_path=music_path,
    )

    logger.info("Done! Video saved to: %s", output_video)
    return output_video


def main():
    available_voices = list_voices()

    parser = argparse.ArgumentParser(
        description="Generate TikTok carousel videos from a topic",
    )
    parser.add_argument("topic", help="Subject for the carousel")
    parser.add_argument(
        "--slides", type=int, default=6, help="Number of slides (default: 6)"
    )
    parser.add_argument(
        "--music", type=Path, default=None, help="Path to background music file"
    )
    parser.add_argument(
        "--output", type=Path, default=None, help="Output video path"
    )
    parser.add_argument(
        "--voice",
        type=str,
        default=DEFAULT_VOICE,
        choices=list(available_voices.keys()),
        help=f"Voice for narration (default: {DEFAULT_VOICE})",
    )
    parser.add_argument(
        "--no-voice",
        action="store_true",
        help="Disable AI voiceover",
    )
    args = parser.parse_args()

    try:
        video_path = run(
            args.topic,
            args.slides,
            args.music,
            voice_name=args.voice,
            enable_voice=not args.no_voice,
        )
        print(f"\nVideo generated: {video_path}")
    except ValueError as e:
        logger.error("Configuration error: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("Failed to generate video: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
