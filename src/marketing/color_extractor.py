"""Extract dominant brand colors from a logo and generate harmonious palettes."""

import colorsys
import logging
from collections import Counter
from PIL import Image

logger = logging.getLogger(__name__)


def _rgb_distance(c1: tuple, c2: tuple) -> float:
    return sum((a - b) ** 2 for a, b in zip(c1, c2)) ** 0.5


def _rgb_to_hsl(r: int, g: int, b: int) -> tuple:
    """Convert RGB (0-255) to HSL (0-360, 0-100, 0-100)."""
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    return (h * 360, s * 100, l * 100)


def _hsl_to_rgb(h: float, s: float, l: float) -> tuple:
    """Convert HSL (0-360, 0-100, 0-100) to RGB (0-255)."""
    r, g, b = colorsys.hls_to_rgb(h / 360, l / 100, s / 100)
    return (int(r * 255), int(g * 255), int(b * 255))


def _complementary(color: tuple) -> tuple:
    """Generate complementary color (opposite on color wheel)."""
    h, s, l = _rgb_to_hsl(*color)
    return _hsl_to_rgb((h + 180) % 360, s, l)


def _analogous(color: tuple, offset: float = 30) -> tuple:
    """Generate analogous color (nearby on color wheel)."""
    h, s, l = _rgb_to_hsl(*color)
    return _hsl_to_rgb((h + offset) % 360, s, l)


def _ensure_contrast(fg: tuple, bg: tuple, min_ratio: float = 3.0) -> tuple:
    """Adjust foreground color to ensure readable contrast against background."""
    def luminance(c):
        vals = []
        for v in c[:3]:
            v = v / 255
            vals.append(v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4)
        return 0.2126 * vals[0] + 0.7152 * vals[1] + 0.0722 * vals[2]

    l1 = luminance(fg)
    l2 = luminance(bg)
    ratio = (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)

    if ratio >= min_ratio:
        return fg

    # If contrast is poor, return white or dark based on bg
    bg_lum = luminance(bg)
    return (255, 255, 255) if bg_lum < 0.5 else (30, 30, 30)


def extract_palette(logo_path: str, num_colors: int = 4) -> dict:
    """
    Extract a brand color palette from a logo image.

    Extracts dominant colors, then generates harmonious secondary/accent
    if the logo doesn't have enough distinct colors.

    Returns dict with:
        primary, secondary, accent, text_on_primary,
        text_dark, text_light, bg_light, bg_dark
    """
    img = Image.open(logo_path).convert("RGBA")
    img = img.resize((150, 150), Image.Resampling.LANCZOS)

    pixels = []
    for r, g, b, a in img.getdata():
        if a < 128:
            continue
        if r > 240 and g > 240 and b > 240:
            continue
        if r < 15 and g < 15 and b < 15:
            continue
        pixels.append((r // 16 * 16, g // 16 * 16, b // 16 * 16))

    if not pixels:
        logger.warning("No usable colors found in logo, using defaults")
        return _default_palette()

    counter = Counter(pixels)
    candidates = [color for color, _ in counter.most_common(50)]

    selected = [candidates[0]]
    for color in candidates[1:]:
        if all(_rgb_distance(color, s) > 60 for s in selected):
            selected.append(color)
        if len(selected) >= num_colors:
            break

    primary = selected[0]

    # Generate harmonious secondary & accent if not enough extracted colors
    if len(selected) >= 2:
        secondary = selected[1]
    else:
        secondary = _analogous(primary, 30)

    if len(selected) >= 3:
        accent = selected[2]
    else:
        accent = _complementary(primary)

    # Smart text color with contrast check
    text_on_primary = _ensure_contrast((255, 255, 255), primary)

    # Generate tinted bg_light from primary (subtle brand feel)
    h, s, l = _rgb_to_hsl(*primary)
    bg_light = _hsl_to_rgb(h, max(s * 0.08, 3), 96)
    bg_dark = _hsl_to_rgb(h, max(s * 0.15, 5), 10)

    palette = {
        "primary": primary,
        "secondary": secondary,
        "accent": accent,
        "text_on_primary": text_on_primary,
        "text_dark": (30, 30, 30),
        "text_light": (250, 250, 250),
        "bg_light": bg_light,
        "bg_dark": bg_dark,
    }

    logger.info(
        "Extracted palette: primary=%s secondary=%s accent=%s bg_light=%s",
        primary, secondary, accent, bg_light,
    )
    return palette


def _default_palette() -> dict:
    return {
        "primary": (41, 98, 255),
        "secondary": (0, 200, 150),
        "accent": (255, 107, 53),
        "text_on_primary": (255, 255, 255),
        "text_dark": (30, 30, 30),
        "text_light": (250, 250, 250),
        "bg_light": (240, 242, 255),
        "bg_dark": (20, 22, 40),
    }
