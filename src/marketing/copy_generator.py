"""Generate marketing copy variations using DeepSeek API."""

import json
import logging
from openai import OpenAI
from src.utils.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert marketing copywriter.
You generate short, punchy ad copy for product marketing visuals.

Respond ONLY with valid JSON using this exact structure:
{
    "taglines": ["tagline 1", "tagline 2", "tagline 3"],
    "descriptions": ["short description 1", "short description 2", "short description 3"],
    "ctas": ["call to action 1", "call to action 2", "call to action 3"]
}

Rules:
- Generate exactly 3 variations of each
- Taglines: max 6 words, bold and memorable
- Descriptions: max 15 words, highlight the key benefit
- CTAs: max 4 words, action-oriented (e.g., "Shop Now", "Get Yours Today")
- Use simple, direct language
- Make each variation feel different in tone (professional, casual, urgent)"""


def generate_marketing_copy(product_name: str, description: str) -> dict:
    """
    Generate marketing copy variations for a product.

    Args:
        product_name: Name of the product.
        description: Brief product description.

    Returns:
        Dict with 'taglines', 'descriptions', 'ctas' — each a list of 3 strings.
    """
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY is not set. Add it to your .env file.")

    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

    logger.info("Generating marketing copy for: %s", product_name)

    response = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Product: {product_name}\nDescription: {description}\n\nGenerate 3 variations of marketing copy.",
            },
        ],
    )

    raw = response.choices[0].message.content
    content = json.loads(raw)

    for key in ("taglines", "descriptions", "ctas"):
        if key not in content:
            raise ValueError(f"Missing '{key}' in API response: {raw}")

    logger.info("Generated %d copy variations", len(content["taglines"]))
    return content
