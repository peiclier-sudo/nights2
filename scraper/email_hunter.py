"""
Advanced email hunter — deep-crawls company websites to find email addresses.
This is the priority module: the main goal is to find emails.
"""

import logging
import re
from urllib.parse import urlparse, urljoin
from collections import deque

from bs4 import BeautifulSoup
from .utils import (
    fetch_page, random_delay, extract_emails_from_html,
    extract_phone_from_text, get_domain
)

logger = logging.getLogger(__name__)

# Pages most likely to contain contact info
PRIORITY_PATHS = [
    "/contact", "/contactez-nous", "/nous-contacter",
    "/contact.html", "/contact.php", "/contact.htm",
    "/a-propos", "/about", "/about-us",
    "/mentions-legales", "/mentions_legales", "/legal",
    "/cgu", "/cgv", "/conditions-generales",
    "/qui-sommes-nous", "/equipe", "/team",
    "/devis", "/demande-de-devis",
    "/recrutement", "/emploi", "/careers",
    "/footer", "/plan-du-site", "/sitemap",
]


def hunt_emails_on_website(base_url, max_pages=15, crawl_depth=2):
    """
    Crawl a company website to find all email addresses.
    Prioritizes contact/about pages. Returns dict with emails and extra info.

    Args:
        base_url: The website URL to crawl
        max_pages: Maximum number of pages to visit
        crawl_depth: How deep to follow links

    Returns:
        dict with 'emails', 'phones', 'pages_crawled'
    """
    if not base_url:
        return {"emails": set(), "phones": set(), "pages_crawled": 0}

    # Normalize URL
    if not base_url.startswith("http"):
        base_url = "https://" + base_url
    base_url = base_url.rstrip("/")

    base_domain = get_domain(base_url)
    if not base_domain:
        return {"emails": set(), "phones": set(), "pages_crawled": 0}

    all_emails = set()
    all_phones = set()
    visited = set()
    pages_crawled = 0

    # Build priority URL queue
    queue = deque()

    # Add priority pages first (contact, about, etc.)
    for path in PRIORITY_PATHS:
        priority_url = base_url + path
        queue.append((priority_url, 0))

    # Add the homepage
    queue.append((base_url, 0))
    queue.append((base_url + "/", 0))

    while queue and pages_crawled < max_pages:
        url, depth = queue.popleft()

        # Normalize
        url = url.split("#")[0].rstrip("/")
        if url in visited:
            continue

        # Stay on same domain
        if get_domain(url) != base_domain:
            continue

        # Skip non-HTML resources
        if _is_non_html(url):
            continue

        visited.add(url)

        resp = fetch_page(url, timeout=10, retries=2)
        if not resp:
            continue

        content_type = resp.headers.get("content-type", "")
        if "html" not in content_type and "text" not in content_type:
            continue

        pages_crawled += 1
        html = resp.text

        # Extract emails
        page_emails = extract_emails_from_html(html)
        if page_emails:
            all_emails.update(page_emails)
            logger.info(f"  Found {len(page_emails)} email(s) on {url}")

        # Extract phones
        page_phones = extract_phone_from_text(html)
        all_phones.update(page_phones)

        # Follow links if within depth
        if depth < crawl_depth:
            new_urls = _extract_internal_links(html, base_url, base_domain)
            for new_url in new_urls:
                if new_url not in visited:
                    # Prioritize contact-like pages
                    if _is_contact_page(new_url):
                        queue.appendleft((new_url, depth + 1))
                    else:
                        queue.append((new_url, depth + 1))

        random_delay(0.5, 1.5)

    # Also try common email patterns if we found the domain but no email
    if not all_emails:
        guessed = _guess_common_emails(base_domain)
        all_emails.update(guessed)

    return {
        "emails": all_emails,
        "phones": all_phones,
        "pages_crawled": pages_crawled,
    }


def _extract_internal_links(html, base_url, base_domain):
    """Extract internal links from HTML."""
    urls = []
    try:
        soup = BeautifulSoup(html, "lxml")
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].strip()

            # Resolve relative URLs
            if href.startswith("/"):
                href = base_url + href
            elif not href.startswith("http"):
                href = urljoin(base_url, href)

            # Only keep same-domain links
            if get_domain(href) == base_domain:
                urls.append(href.split("#")[0])
    except Exception as e:
        logger.debug(f"Link extraction error: {e}")

    return urls


def _is_contact_page(url):
    """Check if URL looks like a contact/about page."""
    url_lower = url.lower()
    contact_indicators = [
        "contact", "contacter", "about", "propos", "equipe",
        "mention", "legal", "devis", "email", "mail",
        "recrutement", "emploi", "qui-sommes",
    ]
    return any(indicator in url_lower for indicator in contact_indicators)


def _is_non_html(url):
    """Check if URL points to a non-HTML resource."""
    non_html_ext = {
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".zip", ".rar", ".tar", ".gz", ".7z",
        ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".bmp", ".ico",
        ".mp3", ".mp4", ".avi", ".mov", ".wmv", ".flv",
        ".css", ".js", ".xml", ".json", ".woff", ".woff2", ".ttf", ".eot",
    }
    url_lower = url.lower().split("?")[0]
    return any(url_lower.endswith(ext) for ext in non_html_ext)


def _guess_common_emails(domain):
    """Try common email patterns — only returns them if DNS MX record exists."""
    common_prefixes = [
        "contact", "info", "commercial", "devis",
        "accueil", "direction", "admin",
    ]

    valid_emails = set()

    # Check if domain has MX records
    try:
        import dns.resolver
        try:
            dns.resolver.resolve(domain, "MX")
            has_mx = True
        except Exception:
            has_mx = False
    except ImportError:
        # dnspython not installed — skip guessing
        return valid_emails

    if has_mx:
        for prefix in common_prefixes:
            valid_emails.add(f"{prefix}@{domain}")
        logger.info(f"  Domain {domain} has MX records — added {len(valid_emails)} guessed emails")
    else:
        logger.debug(f"  Domain {domain} has no MX records — skipping email guesses")

    return valid_emails


def verify_email_domain(email):
    """Verify that the email domain has valid MX records."""
    try:
        import dns.resolver
        domain = email.split("@")[1]
        dns.resolver.resolve(domain, "MX")
        return True
    except Exception:
        return False
