"""Extract dominant brand colors from a logo image."""

import logging
from collections import Counter
from PIL import Image

logger = logging.getLogger(__name__)


def _rgb_distance(c1: tuple, c2: tuple) -> float:
    return sum((a - b) ** 2 for a, b in zip(c1, c2)) ** 0.5


def extract_palette(logo_path: str, num_colors: int = 4) -> dict:
    """
    Extract a brand color palette from a logo image.

    Returns dict with:
        primary, secondary, accent, text_color, bg_light, bg_dark
    """
    img = Image.open(logo_path).convert("RGBA")
    # Resize for speed
    img = img.resize((150, 150), Image.Resampling.LANCZOS)

    pixels = []
    for r, g, b, a in img.getdata():
        # Skip transparent / near-white / near-black pixels
        if a < 128:
            continue
        if r > 240 and g > 240 and b > 240:
            continue
        if r < 15 and g < 15 and b < 15:
            continue
        # Quantize to reduce unique colors
        pixels.append((r // 16 * 16, g // 16 * 16, b // 16 * 16))

    if not pixels:
        logger.warning("No usable colors found in logo, using defaults")
        return _default_palette()

    # Get most common colors, filter out similar ones
    counter = Counter(pixels)
    candidates = [color for color, _ in counter.most_common(50)]

    selected = [candidates[0]]
    for color in candidates[1:]:
        if all(_rgb_distance(color, s) > 60 for s in selected):
            selected.append(color)
        if len(selected) >= num_colors:
            break

    # Pad if not enough distinct colors
    while len(selected) < num_colors:
        selected.append(selected[-1])

    primary = selected[0]
    secondary = selected[1]
    accent = selected[2]

    # Determine text color based on primary brightness
    brightness = (primary[0] * 299 + primary[1] * 587 + primary[2] * 114) / 1000
    text_color = (255, 255, 255) if brightness < 128 else (30, 30, 30)

    palette = {
        "primary": primary,
        "secondary": secondary,
        "accent": accent,
        "text_on_primary": text_color,
        "text_dark": (30, 30, 30),
        "text_light": (255, 255, 255),
        "bg_light": (245, 245, 245),
        "bg_dark": (25, 25, 35),
    }

    logger.info("Extracted palette: primary=%s secondary=%s accent=%s", primary, secondary, accent)
    return palette


def _default_palette() -> dict:
    return {
        "primary": (41, 98, 255),
        "secondary": (0, 200, 150),
        "accent": (255, 107, 53),
        "text_on_primary": (255, 255, 255),
        "text_dark": (30, 30, 30),
        "text_light": (255, 255, 255),
        "bg_light": (245, 245, 245),
        "bg_dark": (25, 25, 35),
    }
