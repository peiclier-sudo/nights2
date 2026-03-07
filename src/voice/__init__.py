"""Text-to-Speech generation using edge-tts (free, high quality)."""

import asyncio
import logging
from pathlib import Path

import edge_tts

from src.utils.config import TEMP_DIR

logger = logging.getLogger(__name__)

# Best English voices on Edge TTS (natural sounding)
VOICES = {
    "andrew": "en-US-AndrewMultilingualNeural",   # Male, natural & modern
    "ava": "en-US-AvaMultilingualNeural",         # Female, very natural
    "brian": "en-US-BrianMultilingualNeural",     # Male, warm & engaging
    "emma": "en-US-EmmaMultilingualNeural",       # Female, clear & friendly
}

DEFAULT_VOICE = "andrew"


async def _generate_speech(
    text: str,
    output_path: Path,
    voice: str,
    rate: str = "+0%",
) -> Path:
    """Generate speech audio from text using edge-tts."""
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(str(output_path))
    return output_path


async def _generate_speech_with_timing(
    text: str,
    output_path: Path,
    voice: str,
    rate: str = "+0%",
) -> tuple[Path, list[dict]]:
    """Generate speech and capture word-level timing for subtitle sync."""
    subtitles = []
    communicate = edge_tts.Communicate(text, voice, rate=rate)

    with open(str(output_path), "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                subtitles.append({
                    "text": chunk["text"],
                    "offset": chunk["offset"] / 10_000_000,  # Convert to seconds
                    "duration": chunk["duration"] / 10_000_000,
                })

    return output_path, subtitles


def generate_voiceover_for_slides(
    slide_texts: list[str],
    voice_name: str = DEFAULT_VOICE,
    rate: str = "+0%",
) -> list[dict]:
    """
    Generate a voiceover audio file for each slide.

    Args:
        slide_texts: List of text for each slide.
        voice_name: Voice key from VOICES dict.
        rate: Speed adjustment (e.g., "+10%", "-5%").

    Returns:
        List of dicts with 'audio_path', 'duration', and 'subtitles' per slide.
    """
    voice = VOICES.get(voice_name, VOICES[DEFAULT_VOICE])
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Generating voiceover with voice: %s (%s)", voice_name, voice)

    results = []

    for i, text in enumerate(slide_texts):
        audio_path = TEMP_DIR / f"voice_{i}.mp3"

        logger.info("  Slide %d: '%s'", i + 1, text[:50])

        # Generate audio with word timing
        audio_file, subtitles = asyncio.run(
            _generate_speech_with_timing(text, audio_path, voice, rate)
        )

        # Get duration using moviepy (reliable)
        from moviepy.editor import AudioFileClip
        clip = AudioFileClip(str(audio_file))
        duration = clip.duration
        clip.close()

        results.append({
            "audio_path": audio_file,
            "duration": duration,
            "subtitles": subtitles,
        })

        logger.info("  -> %.1fs audio generated", duration)

    return results


def list_voices() -> dict[str, str]:
    """Return available voice options."""
    return VOICES.copy()
