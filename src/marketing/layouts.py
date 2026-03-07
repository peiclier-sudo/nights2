"""Layout engine — compose logo, product image, and text into marketing designs."""

import logging
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from src.utils.config import FONTS_DIR, DEFAULT_FONT_FILE

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
    new_size = (int(img.width * ratio), int(img.height * ratio))
    return img.resize(new_size, Image.Resampling.LANCZOS)


def _paste_centered(canvas: Image.Image, img: Image.Image, x: int, y: int):
    """Paste image centered at (x, y), handling transparency."""
    px = x - img.width // 2
    py = y - img.height // 2
    if img.mode == "RGBA":
        canvas.paste(img, (px, py), img)
    else:
        canvas.paste(img, (px, py))


def _draw_text_block(
    draw: ImageDraw.Draw,
    text: str,
    position: tuple,
    font: ImageFont.FreeTypeFont,
    color: tuple,
    max_width: int = 20,
    anchor: str = "mm",
    align: str = "center",
):
    """Draw wrapped text at position."""
    wrapped = textwrap.fill(text, width=max_width)
    draw.multiline_text(position, wrapped, font=font, fill=color, anchor=anchor, align=align)


# ---------------------------------------------------------------------------
# Layout templates
# ---------------------------------------------------------------------------

def layout_centered(
    canvas_size: tuple,
    product: Image.Image,
    logo: Image.Image,
    palette: dict,
    tagline: str,
    cta: str,
) -> Image.Image:
    """Product centered, logo top-left, tagline above product, CTA below."""
    w, h = canvas_size
    canvas = Image.new("RGBA", canvas_size, (*palette["bg_light"], 255))
    draw = ImageDraw.Draw(canvas)

    # Accent bar at top
    draw.rectangle([0, 0, w, 8], fill=(*palette["primary"], 255))

    # Logo top-left
    logo_fit = _fit_image(logo, w // 5, h // 8)
    _paste_centered(canvas, logo_fit, 30 + logo_fit.width // 2, 50 + logo_fit.height // 2)

    # Product centered
    product_fit = _fit_image(product, int(w * 0.6), int(h * 0.45))
    _paste_centered(canvas, product_fit, w // 2, h // 2)

    # Tagline above product
    font_tag = _load_font(max(36, w // 20))
    _draw_text_block(draw, tagline, (w // 2, int(h * 0.15)), font_tag, (*palette["text_dark"], 255))

    # CTA button below product
    font_cta = _load_font(max(28, w // 28))
    cta_y = int(h * 0.82)
    bbox = draw.textbbox((0, 0), cta, font=font_cta)
    cta_w = bbox[2] - bbox[0] + 60
    cta_h = bbox[3] - bbox[1] + 30
    draw.rounded_rectangle(
        [w // 2 - cta_w // 2, cta_y - cta_h // 2, w // 2 + cta_w // 2, cta_y + cta_h // 2],
        radius=cta_h // 2,
        fill=(*palette["primary"], 255),
    )
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
    """Product on left half, text on right half with brand color background."""
    w, h = canvas_size
    canvas = Image.new("RGBA", canvas_size, (*palette["bg_light"], 255))
    draw = ImageDraw.Draw(canvas)

    # Right half colored background
    draw.rectangle([w // 2, 0, w, h], fill=(*palette["primary"], 255))

    # Product on left
    product_fit = _fit_image(product, int(w * 0.42), int(h * 0.7))
    _paste_centered(canvas, product_fit, w // 4, h // 2)

    # Logo top-right
    logo_fit = _fit_image(logo, w // 6, h // 8)
    _paste_centered(canvas, logo_fit, int(w * 0.75), 50 + logo_fit.height // 2)

    # Tagline on right
    font_tag = _load_font(max(32, w // 22))
    _draw_text_block(
        draw, tagline, (int(w * 0.75), int(h * 0.45)),
        font_tag, (*palette["text_on_primary"], 255), max_width=14,
    )

    # CTA on right
    font_cta = _load_font(max(26, w // 30))
    cta_y = int(h * 0.72)
    bbox = draw.textbbox((0, 0), cta, font=font_cta)
    cta_w = bbox[2] - bbox[0] + 50
    cta_h = bbox[3] - bbox[1] + 24
    draw.rounded_rectangle(
        [int(w * 0.75) - cta_w // 2, cta_y - cta_h // 2,
         int(w * 0.75) + cta_w // 2, cta_y + cta_h // 2],
        radius=cta_h // 2,
        fill=(*palette["bg_light"], 255),
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
    """Full-bleed product background with dark overlay, logo + text on top."""
    w, h = canvas_size
    # Product as full background
    bg = product.convert("RGBA").resize(canvas_size, Image.Resampling.LANCZOS)

    # Dark overlay
    overlay = Image.new("RGBA", canvas_size, (0, 0, 0, 140))
    canvas = Image.alpha_composite(bg, overlay)
    draw = ImageDraw.Draw(canvas)

    # Color accent line at bottom
    draw.rectangle([0, h - 6, w, h], fill=(*palette["accent"], 255))

    # Logo top-center
    logo_fit = _fit_image(logo, w // 4, h // 7)
    _paste_centered(canvas, logo_fit, w // 2, int(h * 0.12))

    # Big tagline center
    font_tag = _load_font(max(42, w // 16))
    _draw_text_block(draw, tagline, (w // 2, int(h * 0.48)), font_tag, (255, 255, 255, 255))

    # CTA
    font_cta = _load_font(max(30, w // 26))
    cta_y = int(h * 0.78)
    bbox = draw.textbbox((0, 0), cta, font=font_cta)
    cta_w = bbox[2] - bbox[0] + 60
    cta_h = bbox[3] - bbox[1] + 30
    draw.rounded_rectangle(
        [w // 2 - cta_w // 2, cta_y - cta_h // 2, w // 2 + cta_w // 2, cta_y + cta_h // 2],
        radius=cta_h // 2,
        fill=(*palette["accent"], 255),
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
    """Clean minimal — white background, small product, big bold tagline."""
    w, h = canvas_size
    canvas = Image.new("RGBA", canvas_size, (255, 255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    # Product small, upper area
    product_fit = _fit_image(product, int(w * 0.35), int(h * 0.35))
    _paste_centered(canvas, product_fit, w // 2, int(h * 0.3))

    # Bold tagline below product
    font_tag = _load_font(max(40, w // 18))
    _draw_text_block(draw, tagline, (w // 2, int(h * 0.6)), font_tag, (*palette["text_dark"], 255))

    # CTA as underlined text
    font_cta = _load_font(max(24, w // 32))
    draw.text(
        (w // 2, int(h * 0.78)), cta, font=font_cta,
        fill=(*palette["primary"], 255), anchor="mm",
    )

    # Logo bottom-center
    logo_fit = _fit_image(logo, w // 6, h // 10)
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
    """Dark premium feel — dark background, glowing accent highlights."""
    w, h = canvas_size
    canvas = Image.new("RGBA", canvas_size, (*palette["bg_dark"], 255))
    draw = ImageDraw.Draw(canvas)

    # Accent stripe
    draw.rectangle([0, int(h * 0.02), w, int(h * 0.025)], fill=(*palette["accent"], 255))

    # Logo top-right
    logo_fit = _fit_image(logo, w // 5, h // 8)
    _paste_centered(canvas, logo_fit, w - 30 - logo_fit.width // 2, 50 + logo_fit.height // 2)

    # Product center-left
    product_fit = _fit_image(product, int(w * 0.45), int(h * 0.5))
    _paste_centered(canvas, product_fit, int(w * 0.35), int(h * 0.48))

    # Tagline right side
    font_tag = _load_font(max(34, w // 22))
    _draw_text_block(
        draw, tagline, (int(w * 0.78), int(h * 0.4)),
        font_tag, (*palette["text_light"], 255), max_width=12,
    )

    # CTA bottom center
    font_cta = _load_font(max(28, w // 28))
    cta_y = int(h * 0.85)
    bbox = draw.textbbox((0, 0), cta, font=font_cta)
    cta_w = bbox[2] - bbox[0] + 60
    cta_h = bbox[3] - bbox[1] + 28
    draw.rounded_rectangle(
        [w // 2 - cta_w // 2, cta_y - cta_h // 2, w // 2 + cta_w // 2, cta_y + cta_h // 2],
        radius=cta_h // 2,
        fill=(*palette["accent"], 255),
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
