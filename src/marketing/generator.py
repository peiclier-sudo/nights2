"""Main orchestrator — generates all marketing design variations."""

import logging
from pathlib import Path
from PIL import Image

from src.utils.config import OUTPUT_DIR
from src.marketing.color_extractor import extract_palette
from src.marketing.copy_generator import generate_marketing_copy
from src.marketing.layouts import LAYOUTS, FORMATS

logger = logging.getLogger(__name__)


def generate_designs(
    logo_path: str,
    product_path: str,
    product_name: str,
    product_description: str,
    formats: list[str] | None = None,
    layouts: list[str] | None = None,
) -> list[Path]:
    """
    Generate multiple marketing design variations.

    Args:
        logo_path: Path to the brand logo image.
        product_path: Path to the product image.
        product_name: Name of the product.
        product_description: Brief description for AI copy generation.
        formats: List of format keys (square, story, banner). Defaults to all.
        layouts: List of layout keys. Defaults to all.

    Returns:
        List of paths to generated design images.
    """
    if formats is None:
        formats = list(FORMATS.keys())
    if layouts is None:
        layouts = list(LAYOUTS.keys())

    # Validate inputs
    logo_file = Path(logo_path)
    product_file = Path(product_path)
    if not logo_file.exists():
        raise FileNotFoundError(f"Logo not found: {logo_path}")
    if not product_file.exists():
        raise FileNotFoundError(f"Product image not found: {product_path}")

    output_dir = OUTPUT_DIR / "marketing"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Extract brand colors from logo
    logger.info("Step 1/3: Extracting brand colors from logo")
    palette = extract_palette(str(logo_file))

    # Step 2: Generate marketing copy
    logger.info("Step 2/3: Generating marketing copy with AI")
    copy = generate_marketing_copy(product_name, product_description)
    taglines = copy["taglines"]
    ctas = copy["ctas"]

    logger.info("  Taglines: %s", taglines)
    logger.info("  CTAs: %s", ctas)

    # Step 3: Generate all combinations
    logger.info("Step 3/3: Generating designs")
    logo_img = Image.open(str(logo_file)).convert("RGBA")
    product_img = Image.open(str(product_file)).convert("RGBA")

    generated = []
    variant = 0

    for fmt_name in formats:
        if fmt_name not in FORMATS:
            logger.warning("Unknown format '%s', skipping", fmt_name)
            continue
        canvas_size = FORMATS[fmt_name]

        for layout_name in layouts:
            if layout_name not in LAYOUTS:
                logger.warning("Unknown layout '%s', skipping", layout_name)
                continue
            layout_fn = LAYOUTS[layout_name]

            for i, (tagline, cta) in enumerate(zip(taglines, ctas)):
                variant += 1
                filename = f"{layout_name}_{fmt_name}_v{i + 1}.png"
                out_path = output_dir / filename

                logger.info("  [%d] %s", variant, filename)

                design = layout_fn(
                    canvas_size=canvas_size,
                    product=product_img.copy(),
                    logo=logo_img.copy(),
                    palette=palette,
                    tagline=tagline,
                    cta=cta,
                )

                design.save(str(out_path), "PNG")
                generated.append(out_path)

    logger.info("Generated %d designs in %s", len(generated), output_dir)
    return generated
