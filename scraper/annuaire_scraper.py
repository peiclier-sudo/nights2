"""Scraper for additional French business directories."""

import logging
import re
from urllib.parse import quote_plus

from bs4 import BeautifulSoup
from .utils import fetch_page, random_delay, extract_emails_from_html, extract_phone_from_text

logger = logging.getLogger(__name__)


def search_118712(query, location, max_pages=3):
    """Search 118712.fr directory."""
    companies = []
    seen = set()

    for page in range(1, max_pages + 1):
        url = (
            f"https://www.118712.fr/annuaire/"
            f"recherche?what={quote_plus(query)}"
            f"&where={quote_plus(location)}&page={page}"
        )

        resp = fetch_page(url)
        if not resp:
            break

        soup = BeautifulSoup(resp.text, "lxml")
        listings = soup.find_all("div", class_=re.compile(r"result|listing|card"))

        found = 0
        for listing in listings:
            name_tag = listing.find(["h2", "h3", "h4"])
            if not name_tag:
                continue
            name = name_tag.get_text(strip=True)
            if not name or name in seen:
                continue

            seen.add(name)
            company = {
                "name": name,
                "source": "118712.fr",
                "address": "",
                "phone": "",
                "website": "",
            }

            addr = listing.find(class_=re.compile(r"address|adresse|location"))
            if addr:
                company["address"] = addr.get_text(strip=True)

            phones = extract_phone_from_text(listing.get_text())
            if phones:
                company["phone"] = list(phones)[0]

            for a in listing.find_all("a", href=True):
                href = a["href"]
                if href.startswith("http") and "118712" not in href:
                    company["website"] = href
                    break

            companies.append(company)
            found += 1

        if found == 0:
            break

        random_delay(2, 4)

    logger.info(f"118712: found {len(companies)} companies for '{query}' in {location}")
    return companies


def search_horaires_douverture(query, location, max_pages=3):
    """Search horaires-douverture.fr directory."""
    companies = []
    seen = set()

    for page in range(1, max_pages + 1):
        url = (
            f"https://www.horaires-douverture.fr/recherche/"
            f"?q={quote_plus(query + ' ' + location)}&page={page}"
        )

        resp = fetch_page(url)
        if not resp:
            break

        soup = BeautifulSoup(resp.text, "lxml")
        listings = soup.find_all(["article", "div"], class_=re.compile(r"result|item|card|listing"))

        found = 0
        for listing in listings:
            name_tag = listing.find(["h2", "h3", "h4", "a"])
            if not name_tag:
                continue
            name = name_tag.get_text(strip=True)
            if not name or name in seen or len(name) < 3:
                continue

            seen.add(name)
            company = {
                "name": name,
                "source": "horaires-douverture.fr",
                "address": "",
                "phone": "",
                "website": "",
            }

            addr = listing.find(class_=re.compile(r"addr|location|ville"))
            if addr:
                company["address"] = addr.get_text(strip=True)

            phones = extract_phone_from_text(listing.get_text())
            if phones:
                company["phone"] = list(phones)[0]

            companies.append(company)
            found += 1

        if found == 0:
            break

        random_delay(2, 4)

    logger.info(f"Horaires: found {len(companies)} companies for '{query}' in {location}")
    return companies
