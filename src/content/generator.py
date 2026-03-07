"""Content generation using DeepSeek API."""

import json
import logging
from openai import OpenAI
from src.utils.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Tu es un expert en création de contenu pour TikTok.
Tu génères du contenu pour des carrousels vidéo engageants.

Réponds UNIQUEMENT en JSON valide avec cette structure exacte :
{
    "slides": ["texte slide 1", "texte slide 2", ...],
    "keywords": ["mot-clé image 1", "mot-clé image 2", ...]
}

Règles :
- Chaque texte de slide doit être court (max 15 mots) et percutant
- Les mots-clés doivent être en anglais pour les banques d'images
- Le nombre de keywords doit correspondre au nombre de slides
- La première slide est un titre accrocheur
- La dernière slide est un appel à l'action"""


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
                "content": f"Sujet : {topic}. Crée {num_slides} slides.",
            },
        ],
    )

    raw = response.choices[0].message.content
    content = json.loads(raw)

    if "slides" not in content or "keywords" not in content:
        raise ValueError(f"Unexpected API response structure: {raw}")

    if len(content["keywords"]) != len(content["slides"]):
        logger.warning(
            "Mismatch: %d slides vs %d keywords. Adjusting.",
            len(content["slides"]),
            len(content["keywords"]),
        )
        min_len = min(len(content["slides"]), len(content["keywords"]))
        content["slides"] = content["slides"][:min_len]
        content["keywords"] = content["keywords"][:min_len]

    logger.info("Generated %d slides successfully", len(content["slides"]))
    return content
