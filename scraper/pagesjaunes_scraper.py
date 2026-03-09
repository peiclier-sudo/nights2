"""Pages Jaunes scraper for finding cleaning companies in France."""

import logging
import re
from urllib.parse import quote_plus

from bs4 import BeautifulSoup
from .utils import fetch_page_selenium, fetch_page, random_delay, extract_emails_from_html, extract_phone_from_text

logger = logging.getLogger(__name__)

BASE_URL = "https://www.pagesjaunes.fr"


def search_pagesjaunes(query, location, max_pages=5):
    """
    Search Pages Jaunes for cleaning companies.
    Uses Selenium to bypass anti-bot protection, falls back to requests.
    Returns list of company dicts with name, address, phone, website, etc.
    """
    companies = []
    seen_names = set()

    for page in range(1, max_pages + 1):
        url = (
            f"{BASE_URL}/annuaire/chercherlespros"
            f"?quoiqui={quote_plus(query)}"
            f"&ou={quote_plus(location)}"
            f"&page={page}"
        )

        # Try Selenium first (PagesJaunes uses Datadome anti-bot)
        html = fetch_page_selenium(url, wait_seconds=4)

        if not html:
            # Fallback to requests
            resp = fetch_page(url)
            if not resp:
                logger.warning(f"PagesJaunes failed: {query} in {location}, page {page}")
                break
            html = resp.text

        soup = BeautifulSoup(html, "lxml")

        # PagesJaunes listing selectors (multiple fallbacks)
        listings = soup.select("li.bi-generic")
        if not listings:
            listings = soup.find_all("div", class_=re.compile(r"bi-bloc|bi-content|pj-bloc"))
        if not listings:
            listings = soup.find_all("li", class_=re.compile(r"bi-"))
        if not listings:
            listings = soup.select("[data-pjax], .bi-header-title, .bi")
        if not listings:
            # Try even broader: any block with a company-like structure
            listings = soup.select(".bi-clic, .bi-bloc-content, .single-bloc")

        found_on_page = 0

        for listing in listings:
            company = _parse_listing(listing)
            if company and company["name"] not in seen_names:
                seen_names.add(company["name"])
                companies.append(company)
                found_on_page += 1

        if found_on_page == 0:
            # Check if we got a captcha/block page
            page_text = soup.get_text(strip=True).lower()
            if any(kw in page_text for kw in ["captcha", "robot", "vérification", "datadome"]):
                logger.warning(f"PagesJaunes anti-bot detected for {location}, stopping")
                break
            logger.debug(f"PagesJaunes: no results on page {page} for '{query}' in {location}")
            break

        logger.info(f"PagesJaunes page {page}: {found_on_page} companies for '{query}' in {location}")
        random_delay(3, 6)

    return companies


def _parse_listing(listing):
    """Parse a single listing block from Pages Jaunes."""
    try:
        company = {
            "name": "",
            "address": "",
            "phone": "",
            "website": "",
            "source": "pagesjaunes.fr",
        }

        # Company name - try multiple selectors
        name_tag = listing.select_one(".bi-denomination, .denomination, .bi-header-title")
        if not name_tag:
            name_tag = listing.find(class_=re.compile(r"bi-denomination|denomination|bi-header-title"))
        if not name_tag:
            name_tag = listing.find("h2") or listing.find("h3") or listing.find("a", class_=re.compile(r"bi-"))
        if name_tag:
            company["name"] = name_tag.get_text(strip=True)
        else:
            return None

        if not company["name"] or len(company["name"]) < 2:
            return None

        # Address
        addr_tag = listing.select_one(".bi-address, .address, .bi-adresse, .bi-address-street")
        if not addr_tag:
            addr_tag = listing.find(class_=re.compile(r"bi-address|address|bi-adresse"))
        if addr_tag:
            company["address"] = addr_tag.get_text(strip=True)

        # Phone
        phone_tag = listing.select_one(".bi-phone, .phone, .numero, .click-pj-tel")
        if not phone_tag:
            phone_tag = listing.find(class_=re.compile(r"bi-phone|phone|numero"))
        if phone_tag:
            phones = extract_phone_from_text(phone_tag.get_text())
            if phones:
                company["phone"] = list(phones)[0]

        # Website link
        for a_tag in listing.find_all("a", href=True):
            href = a_tag["href"]
            text = a_tag.get_text(strip=True).lower()
            if "site" in text or "web" in text or "visiter" in text:
                if href.startswith("http") and "pagesjaunes" not in href:
                    company["website"] = href
                    break

        return company

    except Exception as e:
        logger.debug(f"Error parsing PJ listing: {e}")
        return None


def get_company_detail_page(detail_url):
    """Fetch additional info from a company's detail page on Pages Jaunes."""
    html = fetch_page_selenium(detail_url, wait_seconds=3)
    if not html:
        resp = fetch_page(detail_url)
        if not resp:
            return {}
        html = resp.text

    info = {}
    soup = BeautifulSoup(html, "lxml")

    # Try to find email on detail page
    emails = extract_emails_from_html(html)
    if emails:
        info["email"] = list(emails)[0]

    # Try to find website
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if "http" in href and "pagesjaunes" not in href:
            text = a_tag.get_text(strip=True).lower()
            if any(kw in text for kw in ["site", "web", "visiter"]):
                info["website"] = href
                break

    return info
