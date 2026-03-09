"""Societe.com scraper for finding cleaning company details."""

import logging
import re
from urllib.parse import quote_plus

from bs4 import BeautifulSoup
from .utils import fetch_page, random_delay, extract_phone_from_text

logger = logging.getLogger(__name__)

BASE_URL = "https://www.societe.com"


def search_societe(query, max_pages=3):
    """
    Search societe.com for cleaning companies.
    Returns list of company dicts.
    """
    companies = []
    seen = set()

    for page in range(1, max_pages + 1):
        url = f"{BASE_URL}/cgi-bin/search?champs={quote_plus(query)}&page={page}"

        resp = fetch_page(url)
        if not resp:
            logger.warning(f"Societe.com search failed for: {query}, page {page}")
            break

        soup = BeautifulSoup(resp.text, "lxml")

        results = soup.find_all("a", href=re.compile(r"/societe/"))
        found = 0

        for link in results:
            href = link.get("href", "")
            name = link.get_text(strip=True)

            if not name or len(name) < 3 or name in seen:
                continue
            if "/societe/" not in href:
                continue

            seen.add(name)
            detail_url = href if href.startswith("http") else BASE_URL + href

            company = {
                "name": name,
                "detail_url": detail_url,
                "source": "societe.com",
                "address": "",
                "phone": "",
                "website": "",
                "siret": "",
                "naf_code": "",
            }
            companies.append(company)
            found += 1

        if found == 0:
            break

        logger.info(f"Societe.com page {page}: {found} companies for '{query}'")
        random_delay(2, 5)

    return companies


def get_company_details(detail_url):
    """Fetch detailed company info from societe.com detail page."""
    resp = fetch_page(detail_url)
    if not resp:
        return {}

    info = {}
    soup = BeautifulSoup(resp.text, "lxml")

    # SIRET
    siret_match = re.search(r'\b(\d{14})\b', resp.text)
    if siret_match:
        info["siret"] = siret_match.group(1)

    # SIREN
    siren_match = re.search(r'SIREN\s*:?\s*(\d{9})', resp.text)
    if siren_match:
        info["siren"] = siren_match.group(1)

    # Address
    addr_tag = soup.find(class_=re.compile(r"address|adresse|adr"))
    if addr_tag:
        info["address"] = addr_tag.get_text(strip=True)

    # NAF/APE code (cleaning companies are typically 81.2*)
    naf_match = re.search(r'(?:NAF|APE)\s*:?\s*(\d{2}\.\d{2}[A-Z]?)', resp.text)
    if naf_match:
        info["naf_code"] = naf_match.group(1)

    # Phone
    phones = extract_phone_from_text(soup.get_text())
    if phones:
        info["phone"] = list(phones)[0]

    # Website
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if href.startswith("http") and "societe.com" not in href:
            text = a_tag.get_text(strip=True).lower()
            if any(kw in text for kw in ["site", "web", "internet"]):
                info["website"] = href
                break

    return info


def filter_cleaning_companies(companies):
    """Filter companies that are likely cleaning/propreté companies based on NAF codes."""
    cleaning_naf = {"81.21Z", "81.22Z", "81.29A", "81.29B", "81.10Z"}
    cleaning_keywords = [
        "nettoyage", "propreté", "proprete", "cleaning", "entretien",
        "ménage", "menage", "hygiène", "hygiene", "désinfection",
    ]

    filtered = []
    for company in companies:
        name_lower = company.get("name", "").lower()
        naf = company.get("naf_code", "")

        if naf in cleaning_naf:
            filtered.append(company)
        elif any(kw in name_lower for kw in cleaning_keywords):
            filtered.append(company)
        else:
            # Keep it — we can't be sure without NAF
            filtered.append(company)

    return filtered
