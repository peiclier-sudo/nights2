"""Content generation using DeepSeek API."""

import json
import logging
from openai import OpenAI
from src.utils.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert TikTok content creator.
You generate engaging carousel video content with voice narration.

Respond ONLY with valid JSON using this exact structure:
{
    "slides": ["slide 1 text", "slide 2 text", ...],
    "keywords": ["image keyword 1", "image keyword 2", ...],
    "voiceover": ["narration for slide 1", "narration for slide 2", ...]
}

Rules:
- Each slide text must be short (max 15 words) and punchy
- Keywords must be in English for stock image searches
- The number of keywords and voiceover entries must match the number of slides
- The first slide is a catchy hook title
- The last slide is a call to action

Voiceover rules:
- Each narration must be a natural, flowing sentence (20-40 words)
- The tone should be engaging, like a TikTok narrator
- The narration expands on what is shown on the slide
- Use simple, direct language — no jargon
- The first narration must grab attention immediately
- The last narration should encourage action (follow, like, share)"""


def generate_carousel_content(topic: str, num_slides: int = 6) -> dict:
    """
    Generate carousel text and image keywords using DeepSeek API.

    Args:
        topic: The subject for the carousel.
        num_slides: Number of slides to generate.

    Returns:
        Dict with 'slides' (list of texts) and 'keywords' (list of search terms).
    """
    if not DEEPSEEK_API_KEY:
        raise ValueError(
            "DEEPSEEK_API_KEY is not set. Add it to your .env file."
        )

    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

    logger.info("Generating content for topic: %s (%d slides)", topic, num_slides)

    response = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Topic: {topic}. Create {num_slides} slides.",
            },
        ],
    )

    raw = response.choices[0].message.content
    content = json.loads(raw)

    if "slides" not in content or "keywords" not in content:
        raise ValueError(f"Unexpected API response structure: {raw}")

    # Ensure voiceover exists (fallback to slide text if missing)
    if "voiceover" not in content:
        logger.warning("No voiceover in response, using slide texts as fallback")
        content["voiceover"] = content["slides"][:]

    # Align all arrays to same length
    min_len = min(len(content["slides"]), len(content["keywords"]), len(content["voiceover"]))
    if min_len != len(content["slides"]):
        logger.warning(
            "Mismatch: %d slides vs %d keywords vs %d voiceover. Adjusting.",
            len(content["slides"]),
            len(content["keywords"]),
            len(content["voiceover"]),
        )
        content["slides"] = content["slides"][:min_len]
        content["keywords"] = content["keywords"][:min_len]
        content["voiceover"] = content["voiceover"][:min_len]

    logger.info("Generated %d slides successfully", len(content["slides"]))
    return content
