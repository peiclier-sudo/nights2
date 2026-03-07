#!/usr/bin/env python3
"""
Nights2 - Marketing Design Generator

Drop your logo + product image → get multiple ad design variations
powered by AI-generated copy and automated layouts.

Usage:
    python main.py --logo logo.png --product product.jpg --name "SuperWidget"
    python main.py --logo logo.png --product product.jpg --name "Coffee" --description "Premium organic blend"
    python main.py --logo logo.png --product product.jpg --name "Shoes" --formats square,story
    python main.py --logo logo.png --product product.jpg --name "Watch" --layouts hero,minimal,dark
"""

import argparse
import logging
import sys

from src.marketing.generator import generate_designs
from src.marketing.layouts import FORMATS, LAYOUTS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Generate marketing design variations from a logo + product image",
    )
    parser.add_argument(
        "--logo", type=str, required=True,
        help="Path to the brand logo image (PNG with transparency recommended)",
    )
    parser.add_argument(
        "--product", type=str, required=True,
        help="Path to the product image",
    )
    parser.add_argument(
        "--name", type=str, required=True,
        help="Product name",
    )
    parser.add_argument(
        "--description", type=str, default="",
        help="Brief product description for AI copy generation",
    )
    parser.add_argument(
        "--formats", type=str, default=None,
        help=f"Comma-separated output formats (options: {', '.join(FORMATS.keys())}). Default: all",
    )
    parser.add_argument(
        "--layouts", type=str, default=None,
        help=f"Comma-separated layout styles (options: {', '.join(LAYOUTS.keys())}). Default: all",
    )

    args = parser.parse_args()

    formats = args.formats.split(",") if args.formats else None
    layouts = args.layouts.split(",") if args.layouts else None

    try:
        results = generate_designs(
            logo_path=args.logo,
            product_path=args.product,
            product_name=args.name,
            product_description=args.description or args.name,
            formats=formats,
            layouts=layouts,
        )
        print(f"\nGenerated {len(results)} designs:")
        for path in results:
            print(f"  {path}")
    except FileNotFoundError as e:
        logger.error("%s", e)
        sys.exit(1)
    except ValueError as e:
        logger.error("Configuration error: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("Failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
