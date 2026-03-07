"""Visual effects — drop shadows, gradients, glow, reflections, text shadows."""

from PIL import Image, ImageDraw, ImageFilter


def drop_shadow(
    img: Image.Image,
    offset: tuple = (8, 8),
    blur_radius: int = 15,
    shadow_color: tuple = (0, 0, 0, 100),
) -> Image.Image:
    """
    Add a drop shadow behind an image.

    Returns a new RGBA image with the shadow composited behind.
    The canvas is expanded to fit the shadow.
    """
    expand = blur_radius * 2 + max(abs(offset[0]), abs(offset[1]))
    canvas_w = img.width + expand * 2
    canvas_h = img.height + expand * 2

    # Shadow layer
    shadow = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    # Create shadow shape from image alpha
    if img.mode == "RGBA":
        # Use image alpha as shadow mask
        _, _, _, alpha = img.split()
        shadow_shape = Image.new("RGBA", img.size, shadow_color)
        shadow_shape.putalpha(alpha)
    else:
        shadow_shape = Image.new("RGBA", img.size, shadow_color)

    sx = expand + offset[0]
    sy = expand + offset[1]
    shadow.paste(shadow_shape, (sx, sy), shadow_shape)
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur_radius))

    # Paste original on top
    shadow.paste(img, (expand, expand), img if img.mode == "RGBA" else None)

    return shadow


def gradient_background(
    size: tuple,
    color_top: tuple,
    color_bottom: tuple,
    direction: str = "vertical",
) -> Image.Image:
    """
    Create a smooth gradient background.

    Args:
        size: (width, height)
        color_top: RGB tuple for start color
        color_bottom: RGB tuple for end color
        direction: 'vertical', 'horizontal', or 'diagonal'
    """
    w, h = size
    canvas = Image.new("RGBA", size)
    draw = ImageDraw.Draw(canvas)

    if direction == "horizontal":
        for x in range(w):
            t = x / max(w - 1, 1)
            r = int(color_top[0] + (color_bottom[0] - color_top[0]) * t)
            g = int(color_top[1] + (color_bottom[1] - color_top[1]) * t)
            b = int(color_top[2] + (color_bottom[2] - color_top[2]) * t)
            draw.line([(x, 0), (x, h)], fill=(r, g, b, 255))
    elif direction == "diagonal":
        for y in range(h):
            for x in range(w):
                t = (x / max(w - 1, 1) + y / max(h - 1, 1)) / 2
                r = int(color_top[0] + (color_bottom[0] - color_top[0]) * t)
                g = int(color_top[1] + (color_bottom[1] - color_top[1]) * t)
                b = int(color_top[2] + (color_bottom[2] - color_top[2]) * t)
                draw.point((x, y), fill=(r, g, b, 255))
    else:  # vertical
        for y in range(h):
            t = y / max(h - 1, 1)
            r = int(color_top[0] + (color_bottom[0] - color_top[0]) * t)
            g = int(color_top[1] + (color_bottom[1] - color_top[1]) * t)
            b = int(color_top[2] + (color_bottom[2] - color_top[2]) * t)
            draw.line([(0, y), (w, y)], fill=(r, g, b, 255))

    return canvas


def glow_rect(
    draw: ImageDraw.Draw,
    canvas: Image.Image,
    bbox: tuple,
    fill_color: tuple,
    glow_color: tuple | None = None,
    radius: int = 20,
    glow_radius: int = 12,
) -> None:
    """
    Draw a rounded rectangle with a soft glow behind it.

    Args:
        draw: ImageDraw instance
        canvas: The canvas image (for compositing the glow)
        bbox: (x0, y0, x1, y1) rectangle bounds
        fill_color: RGBA fill for the button
        glow_color: RGBA color for glow (defaults to fill with lower alpha)
        radius: Corner radius
        glow_radius: Blur radius for glow
    """
    x0, y0, x1, y1 = bbox
    if glow_color is None:
        glow_color = (*fill_color[:3], 80)

    # Create glow layer
    glow_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    # Expand glow rect slightly
    expand = glow_radius
    glow_draw.rounded_rectangle(
        [x0 - expand, y0 - expand, x1 + expand, y1 + expand],
        radius=radius + expand // 2,
        fill=glow_color,
    )
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(glow_radius))

    # Composite glow onto canvas
    temp = Image.alpha_composite(canvas, glow_layer)
    canvas.paste(temp, (0, 0))

    # Draw the actual button on top
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill_color)


def text_with_shadow(
    draw: ImageDraw.Draw,
    position: tuple,
    text: str,
    font,
    fill: tuple = (255, 255, 255, 255),
    shadow_color: tuple = (0, 0, 0, 120),
    shadow_offset: tuple = (2, 2),
    anchor: str = "mm",
    align: str = "center",
) -> None:
    """Draw text with a subtle shadow for readability."""
    sx = position[0] + shadow_offset[0]
    sy = position[1] + shadow_offset[1]
    # Shadow pass
    draw.multiline_text((sx, sy), text, font=font, fill=shadow_color, anchor=anchor, align=align)
    # Main text
    draw.multiline_text(position, text, font=font, fill=fill, anchor=anchor, align=align)


def reflection(
    img: Image.Image,
    height_ratio: float = 0.3,
    start_opacity: int = 80,
) -> Image.Image:
    """
    Create a fading reflection below an image.

    Returns a new image containing the original + its reflection below.
    """
    reflect_h = int(img.height * height_ratio)

    # Flip and crop
    flipped = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    flipped = flipped.crop((0, 0, flipped.width, reflect_h))

    # Create gradient alpha mask (fade from semi-opaque to transparent)
    mask = Image.new("L", (flipped.width, reflect_h))
    mask_draw = ImageDraw.Draw(mask)
    for y in range(reflect_h):
        alpha = int(start_opacity * (1 - y / reflect_h))
        mask_draw.line([(0, y), (flipped.width, y)], fill=alpha)

    flipped.putalpha(mask)

    # Combine original + reflection
    gap = 4
    total_h = img.height + gap + reflect_h
    canvas = Image.new("RGBA", (img.width, total_h), (0, 0, 0, 0))
    canvas.paste(img, (0, 0), img if img.mode == "RGBA" else None)
    canvas.paste(flipped, (0, img.height + gap), flipped)

    return canvas


def lighten(color: tuple, amount: float = 0.3) -> tuple:
    """Lighten an RGB color by mixing with white."""
    return tuple(min(255, int(c + (255 - c) * amount)) for c in color[:3])


def darken(color: tuple, amount: float = 0.3) -> tuple:
    """Darken an RGB color by mixing with black."""
    return tuple(max(0, int(c * (1 - amount))) for c in color[:3])
