"""Google Search scraper for finding cleaning company websites."""

import logging
import re
from urllib.parse import quote_plus, urlparse, parse_qs

from bs4 import BeautifulSoup
from .utils import fetch_page, random_delay, get_headers, is_valid_company_url

logger = logging.getLogger(__name__)


def search_google(query, num_results=50):
    """
    Scrape Google search results for a query.
    Returns a list of URLs.
    """
    urls = []
    seen = set()
    start = 0

    while len(urls) < num_results:
        search_url = (
            f"https://www.google.fr/search?q={quote_plus(query)}"
            f"&hl=fr&gl=fr&num=10&start={start}"
        )

        resp = fetch_page(search_url)
        if not resp:
            logger.warning(f"Google search failed for: {query} (start={start})")
            break

        soup = BeautifulSoup(resp.text, "lxml")

        # Extract URLs from search results
        result_count_before = len(urls)

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]

            # Google wraps URLs in /url?q=...
            if href.startswith("/url?"):
                parsed = parse_qs(urlparse(href).query)
                actual_url = parsed.get("q", [None])[0]
                if actual_url and actual_url.startswith("http"):
                    if actual_url not in seen and is_valid_company_url(actual_url):
                        seen.add(actual_url)
                        urls.append(actual_url)

            elif href.startswith("http") and "google" not in href:
                if href not in seen and is_valid_company_url(href):
                    seen.add(href)
                    urls.append(href)

        # No new results found — stop
        if len(urls) == result_count_before:
            break

        start += 10
        random_delay(3, 7)  # Longer delay to avoid captcha

        if len(urls) >= num_results:
            break

    logger.info(f"Google: found {len(urls)} URLs for '{query}'")
    return urls[:num_results]


def build_search_queries(base_queries, regions):
    """Build search queries combining base queries with regions."""
    queries = []
    for q in base_queries:
        for region in regions:
            queries.append(f"{q} {region}")
            queries.append(f"{q} {region} contact email")
    return queries
