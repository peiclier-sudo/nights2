"""Scraper for additional French business directories."""

import logging
import re
from urllib.parse import quote_plus

from bs4 import BeautifulSoup
from .utils import fetch_page, fetch_page_selenium, random_delay, extract_emails_from_html, extract_phone_from_text

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

        # Try Selenium first for JS-rendered content
        html = fetch_page_selenium(url, wait_seconds=3)
        if not html:
            resp = fetch_page(url)
            if not resp:
                break
            html = resp.text

        soup = BeautifulSoup(html, "lxml")

        # Try multiple selector strategies
        listings = soup.select(".result-item, .search-result, .company-card, .bloc-result")
        if not listings:
            listings = soup.find_all("div", class_=re.compile(r"result|listing|card|bloc-pro"))
        if not listings:
            # Broader: any element with a heading inside a list/container
            listings = soup.select("li[class*='result'], article, .item")
        if not listings:
            # Last resort: look for structured blocks with headings
            for container in soup.find_all(["div", "li", "article"]):
                if container.find(["h2", "h3", "h4"]) and container.find(class_=re.compile(r"addr|phone|tel")):
                    listings.append(container)

        found = 0
        for listing in listings:
            name_tag = listing.find(["h2", "h3", "h4"])
            if not name_tag:
                # Try first <a> with meaningful text
                name_tag = listing.find("a")
            if not name_tag:
                continue
            name = name_tag.get_text(strip=True)
            if not name or name in seen or len(name) < 3:
                continue

            seen.add(name)
            company = {
                "name": name,
                "source": "118712.fr",
                "address": "",
                "phone": "",
                "website": "",
            }

            addr = listing.find(class_=re.compile(r"addr|adresse|location|ville|city"))
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

        # Try Selenium first for JS-rendered content
        html = fetch_page_selenium(url, wait_seconds=3)
        if not html:
            resp = fetch_page(url)
            if not resp:
                break
            html = resp.text

        soup = BeautifulSoup(html, "lxml")

        # Try multiple selector strategies
        listings = soup.select(".search-result, .result-item, .business-card, .poi-item")
        if not listings:
            listings = soup.find_all(["article", "div"], class_=re.compile(r"result|item|card|listing|poi"))
        if not listings:
            listings = soup.select("li[class*='result'], li[class*='item']")

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

            addr = listing.find(class_=re.compile(r"addr|location|ville|city|address"))
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
