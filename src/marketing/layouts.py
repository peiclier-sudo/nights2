"""Layout engine — compose logo, product image, and text into marketing designs."""

import logging
import textwrap
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from src.utils.config import FONTS_DIR, DEFAULT_FONT_FILE
from src.marketing.effects import (
    drop_shadow,
    gradient_background,
    glow_rect,
    text_with_shadow,
    reflection,
    lighten,
    darken,
)

logger = logging.getLogger(__name__)

# Canvas sizes
FORMATS = {
    "square": (1080, 1080),     # Instagram post
    "story": (1080, 1920),      # Instagram/TikTok story
    "banner": (1200, 628),      # Facebook/Twitter banner
}


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_path = FONTS_DIR / DEFAULT_FONT_FILE
    if font_path.exists():
        return ImageFont.truetype(str(font_path), size)
    return ImageFont.load_default()


def _fit_image(img: Image.Image, max_w: int, max_h: int) -> Image.Image:
    """Resize image to fit within bounds, preserving aspect ratio."""
    ratio = min(max_w / img.width, max_h / img.height)
    new_size = (max(1, int(img.width * ratio)), max(1, int(img.height * ratio)))
    return img.resize(new_size, Image.Resampling.LANCZOS)


def _paste_centered(canvas: Image.Image, img: Image.Image, x: int, y: int):
    """Paste image centered at (x, y), handling transparency."""
    px = x - img.width // 2
    py = y - img.height // 2
    if img.mode == "RGBA":
        canvas.paste(img, (px, py), img)
    else:
        canvas.paste(img, (px, py))


def _wrap(text: str, max_width: int = 20) -> str:
    return textwrap.fill(text, width=max_width)


def _cta_bbox(draw, cta, font, cx, cy, pad_x=40, pad_y=18):
    """Calculate CTA button bounding box centered at (cx, cy)."""
    bbox = draw.textbbox((0, 0), cta, font=font)
    bw = bbox[2] - bbox[0] + pad_x * 2
    bh = bbox[3] - bbox[1] + pad_y * 2
    return (cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2)


# ---------------------------------------------------------------------------
# Layout templates — each uses effects for professional output
# ---------------------------------------------------------------------------

def layout_centered(
    canvas_size: tuple,
    product: Image.Image,
    logo: Image.Image,
    palette: dict,
    tagline: str,
    cta: str,
) -> Image.Image:
    """Product centered with drop shadow, gradient bg, glowing CTA."""
    w, h = canvas_size

    # Gradient background (light brand color → white)
    canvas = gradient_background(
        canvas_size,
        lighten(palette["primary"], 0.85),
        (255, 255, 255),
    )
    draw = ImageDraw.Draw(canvas)

    # Accent bar at top
    draw.rectangle([0, 0, w, 6], fill=(*palette["primary"], 255))

    # Logo top-left
    logo_fit = _fit_image(logo, w // 5, h // 8)
    _paste_centered(canvas, logo_fit, 40 + logo_fit.width // 2, 50 + logo_fit.height // 2)

    # Product with drop shadow, centered
    product_fit = _fit_image(product, int(w * 0.55), int(h * 0.4))
    product_shadowed = drop_shadow(product_fit, offset=(6, 8), blur_radius=18, shadow_color=(0, 0, 0, 60))
    _paste_centered(canvas, product_shadowed, w // 2, int(h * 0.48))

    # Tagline with subtle shadow
    font_tag = _load_font(max(38, w // 18))
    text_with_shadow(
        draw, (w // 2, int(h * 0.13)),
        _wrap(tagline), font_tag,
        fill=(*palette["text_dark"], 255),
        shadow_color=(0, 0, 0, 30), shadow_offset=(1, 2),
    )

    # Glowing CTA button
    font_cta = _load_font(max(28, w // 28))
    cta_y = int(h * 0.84)
    btn = _cta_bbox(draw, cta, font_cta, w // 2, cta_y)
    glow_rect(draw, canvas, btn, (*palette["primary"], 255), radius=btn[3] - btn[1])
    draw.text((w // 2, cta_y), cta, font=font_cta, fill=(*palette["text_on_primary"], 255), anchor="mm")

    return canvas


def layout_split(
    canvas_size: tuple,
    product: Image.Image,
    logo: Image.Image,
    palette: dict,
    tagline: str,
    cta: str,
) -> Image.Image:
    """Product left with reflection, gradient brand panel right."""
    w, h = canvas_size

    # Left side: soft neutral gradient
    canvas = gradient_background(canvas_size, (250, 250, 250), (235, 235, 240))
    draw = ImageDraw.Draw(canvas)

    # Right panel: brand gradient
    right_panel = gradient_background(
        (w // 2, h),
        palette["primary"],
        darken(palette["primary"], 0.25),
    )
    canvas.paste(right_panel, (w // 2, 0))
    draw = ImageDraw.Draw(canvas)

    # Product on left with drop shadow
    product_fit = _fit_image(product, int(w * 0.38), int(h * 0.55))
    product_shadowed = drop_shadow(product_fit, offset=(5, 6), blur_radius=14, shadow_color=(0, 0, 0, 50))
    _paste_centered(canvas, product_shadowed, int(w * 0.26), int(h * 0.45))

    # Logo top-right on brand panel
    logo_fit = _fit_image(logo, w // 6, h // 8)
    _paste_centered(canvas, logo_fit, int(w * 0.75), 50 + logo_fit.height // 2)

    # Tagline on right with shadow for readability
    font_tag = _load_font(max(34, w // 20))
    text_with_shadow(
        draw, (int(w * 0.75), int(h * 0.43)),
        _wrap(tagline, 14), font_tag,
        fill=(255, 255, 255, 255),
        shadow_color=(0, 0, 0, 60),
    )

    # CTA button (white on brand)
    font_cta = _load_font(max(26, w // 30))
    cta_y = int(h * 0.72)
    btn = _cta_bbox(draw, cta, font_cta, int(w * 0.75), cta_y, pad_x=32, pad_y=14)
    glow_rect(
        draw, canvas, btn,
        (255, 255, 255, 240),
        glow_color=(*lighten(palette["primary"], 0.3), 60),
        radius=(btn[3] - btn[1]),
    )
    draw.text(
        (int(w * 0.75), cta_y), cta, font=font_cta,
        fill=(*palette["primary"], 255), anchor="mm",
    )

    return canvas


def layout_hero(
    canvas_size: tuple,
    product: Image.Image,
    logo: Image.Image,
    palette: dict,
    tagline: str,
    cta: str,
) -> Image.Image:
    """Full-bleed product bg, blurred + overlaid, bold text + glowing CTA."""
    w, h = canvas_size

    # Product as full background, blurred
    bg = product.convert("RGBA").resize(canvas_size, Image.Resampling.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(6))

    # Gradient overlay (brand-tinted dark)
    overlay = gradient_background(
        canvas_size,
        (*darken(palette["primary"], 0.7), 180),
        (0, 0, 0, 200),
        direction="vertical",
    )
    # Manual alpha composite since overlay has per-pixel alpha
    canvas = Image.alpha_composite(bg, overlay)
    draw = ImageDraw.Draw(canvas)

    # Accent line bottom
    draw.rectangle([0, h - 5, w, h], fill=(*palette["accent"], 255))

    # Logo top-center
    logo_fit = _fit_image(logo, w // 4, h // 7)
    _paste_centered(canvas, logo_fit, w // 2, int(h * 0.1))

    # Big tagline center with strong shadow
    font_tag = _load_font(max(46, w // 14))
    text_with_shadow(
        draw, (w // 2, int(h * 0.45)),
        _wrap(tagline, 16), font_tag,
        fill=(255, 255, 255, 255),
        shadow_color=(0, 0, 0, 150), shadow_offset=(3, 3),
    )

    # Glowing accent CTA
    font_cta = _load_font(max(30, w // 24))
    cta_y = int(h * 0.76)
    btn = _cta_bbox(draw, cta, font_cta, w // 2, cta_y)
    glow_rect(
        draw, canvas, btn,
        (*palette["accent"], 255),
        glow_color=(*palette["accent"], 100),
        radius=(btn[3] - btn[1]),
        glow_radius=16,
    )
    draw.text((w // 2, cta_y), cta, font=font_cta, fill=(255, 255, 255, 255), anchor="mm")

    return canvas


def layout_minimal(
    canvas_size: tuple,
    product: Image.Image,
    logo: Image.Image,
    palette: dict,
    tagline: str,
    cta: str,
) -> Image.Image:
    """Clean minimal — white bg, product with reflection, elegant typography."""
    w, h = canvas_size
    canvas = Image.new("RGBA", canvas_size, (255, 255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    # Subtle top accent line
    draw.rectangle([int(w * 0.3), 0, int(w * 0.7), 3], fill=(*palette["primary"], 180))

    # Product with reflection
    product_fit = _fit_image(product, int(w * 0.35), int(h * 0.3))
    product_reflected = reflection(product_fit, height_ratio=0.25, start_opacity=50)
    _paste_centered(canvas, product_reflected, w // 2, int(h * 0.3))

    # Bold tagline below
    font_tag = _load_font(max(42, w // 16))
    text_with_shadow(
        draw, (w // 2, int(h * 0.6)),
        _wrap(tagline), font_tag,
        fill=(*palette["text_dark"], 255),
        shadow_color=(0, 0, 0, 15), shadow_offset=(1, 1),
    )

    # CTA as accent-colored text (no button, minimal style)
    font_cta = _load_font(max(26, w // 30))
    draw.text(
        (w // 2, int(h * 0.76)), cta, font=font_cta,
        fill=(*palette["primary"], 255), anchor="mm",
    )
    # Underline
    cta_bbox = draw.textbbox((w // 2, int(h * 0.76)), cta, font=font_cta, anchor="mm")
    draw.line(
        [cta_bbox[0], cta_bbox[3] + 4, cta_bbox[2], cta_bbox[3] + 4],
        fill=(*palette["primary"], 120), width=2,
    )

    # Logo bottom-center
    logo_fit = _fit_image(logo, w // 7, h // 12)
    _paste_centered(canvas, logo_fit, w // 2, int(h * 0.92))

    return canvas


def layout_dark(
    canvas_size: tuple,
    product: Image.Image,
    logo: Image.Image,
    palette: dict,
    tagline: str,
    cta: str,
) -> Image.Image:
    """Premium dark — gradient bg, glowing product shadow, neon-style CTA."""
    w, h = canvas_size

    # Dark gradient background
    canvas = gradient_background(
        canvas_size,
        palette["bg_dark"],
        darken(palette["bg_dark"], 0.4),
        direction="diagonal",
    )
    draw = ImageDraw.Draw(canvas)

    # Accent stripe
    draw.rectangle([0, int(h * 0.018), w, int(h * 0.023)], fill=(*palette["accent"], 200))

    # Logo top-right
    logo_fit = _fit_image(logo, w // 5, h // 8)
    _paste_centered(canvas, logo_fit, w - 40 - logo_fit.width // 2, 50 + logo_fit.height // 2)

    # Product with colored glow shadow
    product_fit = _fit_image(product, int(w * 0.42), int(h * 0.45))
    product_shadowed = drop_shadow(
        product_fit, offset=(0, 4), blur_radius=25,
        shadow_color=(*palette["accent"], 70),
    )
    _paste_centered(canvas, product_shadowed, int(w * 0.34), int(h * 0.48))

    # Tagline right side with glow effect
    font_tag = _load_font(max(36, w // 20))
    text_with_shadow(
        draw, (int(w * 0.76), int(h * 0.38)),
        _wrap(tagline, 12), font_tag,
        fill=(255, 255, 255, 255),
        shadow_color=(*palette["accent"], 40), shadow_offset=(0, 2),
    )

    # Glowing neon-style CTA
    font_cta = _load_font(max(28, w // 26))
    cta_y = int(h * 0.85)
    btn = _cta_bbox(draw, cta, font_cta, w // 2, cta_y)
    glow_rect(
        draw, canvas, btn,
        (*palette["accent"], 255),
        glow_color=(*palette["accent"], 120),
        radius=(btn[3] - btn[1]),
        glow_radius=20,
    )
    draw.text((w // 2, cta_y), cta, font=font_cta, fill=(255, 255, 255, 255), anchor="mm")

    return canvas


# Registry of all layouts
LAYOUTS = {
    "centered": layout_centered,
    "split": layout_split,
    "hero": layout_hero,
    "minimal": layout_minimal,
    "dark": layout_dark,
}
