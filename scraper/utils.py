"""Utility functions for the scraper."""

import random
import time
import re
import logging
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)

# Persistent session for connection reuse
_session = requests.Session()

try:
    _ua = UserAgent(fallback="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
except Exception:
    _ua = None

HEADERS_BASE = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.5,en;q=0.3",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "DNT": "1",
}

# Selenium driver singleton
_driver = None
_selenium_failed = False  # Cache failure to avoid retrying every request


def _make_browser_options(browser_type="chrome"):
    """Create browser options for anti-detection."""
    if browser_type == "edge":
        from selenium.webdriver.edge.options import Options
    else:
        from selenium.webdriver.chrome.options import Options

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=fr-FR")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
    if browser_type == "chrome":
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
    return options


def get_selenium_driver():
    """Get or create a Selenium driver (tries Edge first on Windows, then Chrome)."""
    global _driver, _selenium_failed

    # Don't retry if we already failed
    if _selenium_failed:
        return None

    if _driver is not None:
        try:
            _driver.current_url  # check if still alive
            return _driver
        except Exception:
            _driver = None

    # Try Edge first (pre-installed on Windows)
    try:
        from selenium import webdriver
        from selenium.webdriver.edge.service import Service as EdgeService
        from webdriver_manager.microsoft import EdgeChromiumDriverManager

        options = _make_browser_options("edge")
        service = EdgeService(EdgeChromiumDriverManager().install())
        _driver = webdriver.Edge(service=service, options=options)
        _driver.set_page_load_timeout(20)
        logger.info("Selenium Edge driver initialized")
        return _driver
    except Exception as e:
        logger.debug(f"Edge driver failed: {e}")

    # Try Chrome
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service as ChromeService
        from webdriver_manager.chrome import ChromeDriverManager

        options = _make_browser_options("chrome")
        service = ChromeService(ChromeDriverManager().install())
        _driver = webdriver.Chrome(service=service, options=options)

        _driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
        )
        _driver.set_page_load_timeout(20)
        logger.info("Selenium Chrome driver initialized")
        return _driver
    except Exception as e:
        logger.warning(f"No browser found for Selenium (Chrome/Edge). Falling back to requests only. Error: {e}")
        _selenium_failed = True
        return None


def fetch_page_selenium(url, wait_seconds=3):
    """Fetch a page using Selenium (for anti-bot protected sites)."""
    driver = get_selenium_driver()
    if not driver:
        return None

    try:
        driver.get(url)
        time.sleep(wait_seconds)  # wait for JS rendering + anti-bot checks
        html = driver.page_source
        if html and len(html) > 500:
            return html
        return None
    except Exception as e:
        logger.debug(f"Selenium fetch failed for {url}: {e}")
        return None


def close_selenium_driver():
    """Close the Selenium driver."""
    global _driver
    if _driver:
        try:
            _driver.quit()
        except Exception:
            pass
        _driver = None


def get_headers():
    """Return headers with a random user agent."""
    headers = HEADERS_BASE.copy()
    if _ua:
        try:
            headers["User-Agent"] = _ua.random
        except Exception:
            headers["User-Agent"] = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
    else:
        headers["User-Agent"] = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    return headers


def random_delay(min_sec=2, max_sec=5):
    """Sleep for a random duration to avoid rate limiting."""
    time.sleep(random.uniform(min_sec, max_sec))


def fetch_page(url, timeout=15, retries=3):
    """Fetch a page with retries and random headers."""
    for attempt in range(retries):
        try:
            resp = _session.get(url, headers=get_headers(), timeout=timeout, allow_redirects=True)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            logger.debug(f"Attempt {attempt + 1} failed for {url}: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    return None


def extract_emails_from_text(text):
    """Extract email addresses from text using regex."""
    if not text:
        return set()

    # Comprehensive email regex
    pattern = r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'
    emails = set(re.findall(pattern, text.lower()))

    # Filter out common false positives
    excluded_domains = {
        "example.com", "sentry.io", "wixpress.com", "w3.org",
        "schema.org", "googleapis.com", "google.com", "facebook.com",
        "twitter.com", "instagram.com", "jquery.com", "wordpress.org",
        "wordpress.com", "gravatar.com", "wp.com", "cloudflare.com",
    }
    excluded_extensions = {".png", ".jpg", ".gif", ".svg", ".css", ".js", ".webp"}

    filtered = set()
    for email in emails:
        domain = email.split("@")[1]
        if domain in excluded_domains:
            continue
        if any(email.endswith(ext) for ext in excluded_extensions):
            continue
        if len(email) > 80:
            continue
        filtered.add(email)

    return filtered


def extract_emails_from_html(html_content):
    """Extract emails from HTML content including mailto: links and obfuscated patterns."""
    if not html_content:
        return set()

    emails = set()

    # Extract from raw text
    emails.update(extract_emails_from_text(html_content))

    # Parse HTML for mailto: links
    try:
        soup = BeautifulSoup(html_content, "lxml")

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if "mailto:" in href:
                email = href.replace("mailto:", "").split("?")[0].strip().lower()
                if re.match(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', email):
                    emails.add(email)

        # Handle common obfuscation: [at] [dot] (at) (dot)
        body_text = soup.get_text(separator=" ")
        deobfuscated = body_text
        for at_pattern in [" [at] ", " (at) ", " [AT] ", " (AT) ", "[at]", "(at)", " @ "]:
            deobfuscated = deobfuscated.replace(at_pattern, "@")
        for dot_pattern in [" [dot] ", " (dot) ", " [DOT] ", " (DOT) ", "[dot]", "(dot)"]:
            deobfuscated = deobfuscated.replace(dot_pattern, ".")
        emails.update(extract_emails_from_text(deobfuscated))

    except Exception as e:
        logger.debug(f"HTML parsing error: {e}")

    return emails


def extract_phone_from_text(text):
    """Extract French phone numbers from text."""
    if not text:
        return set()
    patterns = [
        r'(?:(?:\+33|0033)\s*[1-9](?:[\s.\-]?\d{2}){4})',
        r'(?:0[1-9](?:[\s.\-]?\d{2}){4})',
    ]
    phones = set()
    for pattern in patterns:
        for match in re.findall(pattern, text):
            cleaned = re.sub(r'[\s.\-]', '', match)
            if len(cleaned) >= 10:
                phones.add(cleaned)
    return phones


def get_domain(url):
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower().replace("www.", "")
    except Exception:
        return ""


def is_valid_company_url(url):
    """Check if a URL is likely a company website (not a directory/social media)."""
    if not url:
        return False
    skip_domains = {
        "facebook.com", "twitter.com", "instagram.com", "linkedin.com",
        "youtube.com", "google.com", "bing.com", "yahoo.com",
        "wikipedia.org", "pagesjaunes.fr", "societe.com",
        "verif.com", "infogreffe.fr", "sirene.fr",
        "kompass.com", "europages.fr", "yelp.com", "tripadvisor.com",
    }
    domain = get_domain(url)
    return not any(skip in domain for skip in skip_domains)
