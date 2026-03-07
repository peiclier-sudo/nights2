"""Add text overlays to images using Pillow."""

import logging
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from src.utils.config import OUTPUT_SIZE, FONTS_DIR, DEFAULT_FONT_SIZE, DEFAULT_FONT_FILE

logger = logging.getLogger(__name__)

# Maximum characters per line before wrapping
MAX_CHARS_PER_LINE = 25


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load the configured font, falling back to default if not found."""
    font_path = FONTS_DIR / DEFAULT_FONT_FILE
    if font_path.exists():
        return ImageFont.truetype(str(font_path), size)
    logger.warning("Font %s not found, using default font", font_path)
    return ImageFont.load_default()


def _create_solid_background(color: tuple = (30, 30, 60)) -> Image.Image:
    """Create a solid-color background image for slides without photos."""
    return Image.new("RGBA", OUTPUT_SIZE, (*color, 255))


def add_text_to_image(
    image_path: Path | None,
    text: str,
    output_path: Path,
    font_size: int = DEFAULT_FONT_SIZE,
    text_color: tuple = (255, 255, 255, 255),
    bg_opacity: int = 180,
) -> Path:
    """
    Add text overlay on an image with a semi-transparent background.

    If image_path is None, a solid-color background is used as fallback.

    Args:
        image_path: Source image path (or None for fallback).
        text: Text to overlay.
        output_path: Where to save the result.
        font_size: Font size in pixels.
        text_color: RGBA text color.
        bg_opacity: Opacity of the text background rectangle (0-255).

    Returns:
        The output path.
    """
    if image_path and image_path.exists():
        img = Image.open(image_path).convert("RGBA")
        img = img.resize(OUTPUT_SIZE, Image.Resampling.LANCZOS)
    else:
        img = _create_solid_background()

    font = _load_font(font_size)
    wrapped_text = textwrap.fill(text, width=MAX_CHARS_PER_LINE)

    # Create text layer
    txt_layer = Image.new("RGBA", OUTPUT_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(txt_layer)

    # Calculate text bounding box
    bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font, align="center")
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Position: centered horizontally, near the bottom
    margin = 30
    center_x = OUTPUT_SIZE[0] // 2
    text_y = OUTPUT_SIZE[1] - 250 - text_height // 2

    # Draw semi-transparent background rectangle
    rect_x0 = center_x - text_width // 2 - margin
    rect_y0 = text_y - text_height // 2 - margin
    rect_x1 = center_x + text_width // 2 + margin
    rect_y1 = text_y + text_height // 2 + margin

    draw.rounded_rectangle(
        [rect_x0, rect_y0, rect_x1, rect_y1],
        radius=15,
        fill=(0, 0, 0, bg_opacity),
    )

    # Draw text
    draw.multiline_text(
        (center_x, text_y),
        wrapped_text,
        font=font,
        fill=text_color,
        anchor="mm",
        align="center",
    )

    # Composite
    result = Image.alpha_composite(img, txt_layer)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.save(str(output_path), "PNG")
    logger.info("Created slide: %s", output_path)
    return output_path
