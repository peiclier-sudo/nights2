"""Assemble images into a video with transitions and optional audio."""

import logging
from pathlib import Path
from moviepy.editor import (
    ImageClip,
    AudioFileClip,
    concatenate_videoclips,
)
from src.utils.config import OUTPUT_SIZE, FPS, DURATION_PER_SLIDE, CROSSFADE_DURATION, OUTPUT_DIR

logger = logging.getLogger(__name__)


def create_carousel_video(
    image_paths: list[Path],
    audio_path: Path | None = None,
    output_path: Path | None = None,
    duration_per_slide: float = DURATION_PER_SLIDE,
) -> Path:
    """
    Assemble slide images into a video with crossfade transitions.

    Args:
        image_paths: Ordered list of slide image paths.
        audio_path: Optional background music file.
        output_path: Output video path. Defaults to output/carousel.mp4.
        duration_per_slide: Duration of each slide in seconds.

    Returns:
        Path to the generated video file.
    """
    if not image_paths:
        raise ValueError("No images provided for video assembly")

    output_path = output_path or OUTPUT_DIR / "carousel.mp4"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Assembling %d slides into video", len(image_paths))

    clips = []
    for i, img_path in enumerate(image_paths):
        clip = ImageClip(str(img_path), duration=duration_per_slide)
        clip = clip.resize(OUTPUT_SIZE)

        if i > 0:
            clip = clip.crossfadein(CROSSFADE_DURATION)

        clips.append(clip)

    final = concatenate_videoclips(clips, method="compose")

    # Add background music if provided
    if audio_path and audio_path.exists():
        logger.info("Adding background music: %s", audio_path)
        audio = AudioFileClip(str(audio_path))
        # Loop or trim audio to match video duration
        if audio.duration < final.duration:
            loops = int(final.duration / audio.duration) + 1
            from moviepy.editor import concatenate_audioclips
            audio = concatenate_audioclips([audio] * loops)
        audio = audio.subclip(0, final.duration)
        audio = audio.volumex(0.3)  # Lower volume for background
        final = final.set_audio(audio)

    final.write_videofile(
        str(output_path),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        logger="bar",
    )

    logger.info("Video saved: %s", output_path)
    return output_path
