"""Assemble images into a video with transitions, voiceover, and optional music."""

import logging
from pathlib import Path
from moviepy.editor import (
    ImageClip,
    AudioFileClip,
    CompositeAudioClip,
    concatenate_audioclips,
    concatenate_videoclips,
)
from src.utils.config import OUTPUT_SIZE, FPS, DURATION_PER_SLIDE, CROSSFADE_DURATION, OUTPUT_DIR

logger = logging.getLogger(__name__)

# Minimum slide duration even with short voiceover
MIN_SLIDE_DURATION = 2.0
# Extra padding after voice finishes before next slide
VOICE_PADDING = 0.8


def create_carousel_video(
    image_paths: list[Path],
    voice_data: list[dict] | None = None,
    music_path: Path | None = None,
    output_path: Path | None = None,
    duration_per_slide: float = DURATION_PER_SLIDE,
) -> Path:
    """
    Assemble slide images into a video with voiceover and background music.

    Args:
        image_paths: Ordered list of slide image paths.
        voice_data: List of dicts from voice module with 'audio_path' and 'duration'.
                    If provided, slide durations adapt to voice length.
        music_path: Optional background music file.
        output_path: Output video path.
        duration_per_slide: Fallback duration if no voice data.

    Returns:
        Path to the generated video file.
    """
    if not image_paths:
        raise ValueError("No images provided for video assembly")

    output_path = output_path or OUTPUT_DIR / "carousel.mp4"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Assembling %d slides into video", len(image_paths))

    # Build video clips with durations adapted to voiceover
    clips = []
    voice_clips = []
    current_time = 0.0

    for i, img_path in enumerate(image_paths):
        # Determine slide duration
        if voice_data and i < len(voice_data):
            # Slide lasts as long as the voice + padding
            slide_duration = max(
                voice_data[i]["duration"] + VOICE_PADDING,
                MIN_SLIDE_DURATION,
            )
        else:
            slide_duration = duration_per_slide

        clip = ImageClip(str(img_path), duration=slide_duration)
        clip = clip.resize(OUTPUT_SIZE)

        if i > 0:
            clip = clip.crossfadein(CROSSFADE_DURATION)

        clips.append(clip)

        # Prepare voice audio clip positioned at the right time
        if voice_data and i < len(voice_data):
            v_clip = AudioFileClip(str(voice_data[i]["audio_path"]))
            v_clip = v_clip.set_start(current_time)
            voice_clips.append(v_clip)

        current_time += slide_duration

    final = concatenate_videoclips(clips, method="compose")

    # Mix audio layers
    audio_layers = []

    # Layer 1: Voiceover (full volume)
    if voice_clips:
        logger.info("Adding voiceover narration")
        audio_layers.extend(voice_clips)

    # Layer 2: Background music (low volume)
    if music_path and music_path.exists():
        logger.info("Adding background music: %s", music_path)
        music = AudioFileClip(str(music_path))
        # Loop music if needed
        if music.duration < final.duration:
            loops = int(final.duration / music.duration) + 1
            music = concatenate_audioclips([music] * loops)
        music = music.subclip(0, final.duration)
        # Lower volume when voice is present, slightly louder otherwise
        music_volume = 0.15 if voice_clips else 0.3
        music = music.volumex(music_volume)
        # Fade out last 2 seconds
        music = music.audio_fadeout(2.0)
        audio_layers.append(music)

    # Combine audio layers
    if audio_layers:
        final_audio = CompositeAudioClip(audio_layers)
        final = final.set_audio(final_audio)

    final.write_videofile(
        str(output_path),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        logger="bar",
    )

    logger.info("Video saved: %s", output_path)
    return output_path
