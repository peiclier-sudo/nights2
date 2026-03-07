"""Download images from free stock photo APIs (Pexels, Pixabay)."""

import logging
from pathlib import Path
import requests
from src.utils.config import (
    PEXELS_API_KEY,
    PIXABAY_API_KEY,
    IMAGE_SOURCES,
    TEMP_DIR,
)

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15


def _download_file(url: str, dest: Path) -> Path:
    """Download a file from a URL to a local path."""
    resp = requests.get(url, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(resp.content)
    return dest


def _search_pexels(keyword: str) -> str | None:
    """Search Pexels for an image matching the keyword. Returns image URL."""
    if not PEXELS_API_KEY:
        return None
    headers = {"Authorization": PEXELS_API_KEY}
    url = "https://api.pexels.com/v1/search"
    params = {"query": keyword, "per_page": 5, "orientation": "portrait"}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if data.get("photos"):
            return data["photos"][0]["src"]["large2x"]
    except requests.RequestException as e:
        logger.warning("Pexels search failed for '%s': %s", keyword, e)
    return None


def _search_pixabay(keyword: str) -> str | None:
    """Search Pixabay for an image matching the keyword. Returns image URL."""
    if not PIXABAY_API_KEY:
        return None
    url = "https://pixabay.com/api/"
    params = {
        "key": PIXABAY_API_KEY,
        "q": keyword,
        "per_page": 5,
        "image_type": "photo",
        "orientation": "vertical",
    }
    try:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if data.get("hits"):
            return data["hits"][0]["largeImageURL"]
    except requests.RequestException as e:
        logger.warning("Pixabay search failed for '%s': %s", keyword, e)
    return None


SEARCH_FUNCTIONS = {
    "pexels": _search_pexels,
    "pixabay": _search_pixabay,
}


def download_images(keywords: list[str], output_dir: Path | None = None) -> list[Path]:
    """
    Download one image per keyword using configured image sources.

    Falls back through sources in priority order. If no image is found,
    returns None for that slot so the caller can generate a solid-color fallback.

    Args:
        keywords: List of English search terms.
        output_dir: Where to save images. Defaults to TEMP_DIR.

    Returns:
        List of Path objects (or None for missing images).
    """
    output_dir = output_dir or TEMP_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    image_paths: list[Path | None] = []

    for i, keyword in enumerate(keywords):
        img_url = None
        for source in IMAGE_SOURCES:
            search_fn = SEARCH_FUNCTIONS.get(source)
            if search_fn:
                img_url = search_fn(keyword)
                if img_url:
                    logger.info("Found image for '%s' on %s", keyword, source)
                    break

        if img_url:
            dest = output_dir / f"slide_{i + 1}.jpg"
            try:
                _download_file(img_url, dest)
                image_paths.append(dest)
                continue
            except requests.RequestException as e:
                logger.warning("Failed to download image: %s", e)

        logger.warning("No image found for keyword '%s'", keyword)
        image_paths.append(None)

    return image_paths
