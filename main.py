#!/usr/bin/env python3
"""
Scraper pour entreprises de nettoyage en France
Objectif principal: trouver des emails de contact

Sources:
  - Google Search
  - Pages Jaunes
  - Societe.com
  - 118712.fr
  - Crawl direct des sites web des entreprises

Usage:
  python main.py                    # Full scrape (all sources, all regions)
  python main.py --quick            # Quick mode (fewer regions, fewer results)
  python main.py --source google    # Only use Google
  python main.py --source pagesjaunes
  python main.py --regions Paris Lyon Marseille
  python main.py --emails-only      # Only output companies with emails
"""

import argparse
import json
import logging
import os
import sys
import csv
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

from scraper.google_scraper import search_google, build_search_queries
from scraper.pagesjaunes_scraper import search_pagesjaunes
from scraper.societe_scraper import search_societe, get_company_details, filter_cleaning_companies
from scraper.annuaire_scraper import search_118712, search_horaires_douverture
from scraper.email_hunter import hunt_emails_on_website, verify_email_domain
from scraper.utils import (
    extract_emails_from_html, fetch_page, random_delay,
    get_domain, is_valid_company_url, close_selenium_driver,
)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("scraper.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def load_config():
    """Load configuration from config.json."""
    config_path = Path(__file__).parent / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def merge_company(existing, new_data):
    """Merge new company data into existing record, keeping non-empty values."""
    for key, value in new_data.items():
        if value and (not existing.get(key) or key == "emails"):
            if key == "emails" and isinstance(value, set):
                existing.setdefault("emails", set()).update(value)
            else:
                existing[key] = value
    return existing


class NettoyageScraper:
    """Main scraper orchestrator for cleaning companies in France."""

    def __init__(self, config, args):
        self.config = config
        self.args = args
        self.companies = {}  # keyed by normalized name
        self.websites_crawled = set()

    def normalize_name(self, name):
        """Normalize company name for deduplication."""
        if not name:
            return ""
        import re
        name = name.lower().strip()
        name = re.sub(r'\b(sarl|sas|sa|eurl|sasu|sci|snc)\b', '', name)
        name = re.sub(r'[^a-z0-9\s]', '', name)
        name = re.sub(r'\s+', ' ', name).strip()
        return name

    def add_company(self, company_data):
        """Add or merge a company into our database."""
        name = company_data.get("name", "")
        if not name:
            return

        key = self.normalize_name(name)
        if not key:
            return

        if key in self.companies:
            self.companies[key] = merge_company(self.companies[key], company_data)
        else:
            company_data.setdefault("emails", set())
            self.companies[key] = company_data

    def run(self):
        """Run the full scraping pipeline."""
        logger.info("=" * 60)
        logger.info("SCRAPER ENTREPRISES DE NETTOYAGE - FRANCE")
        logger.info(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        logger.info("=" * 60)

        sources = self.args.source if self.args.source else ["all"]
        regions = self.args.regions if self.args.regions else self.config["regions"]

        if self.args.quick:
            regions = regions[:5]
            logger.info(f"Mode rapide: {len(regions)} régions")

        # Phase 1: Collect companies from directories
        logger.info("\n--- PHASE 1: Collecte depuis les annuaires ---")

        if "all" in sources or "pagesjaunes" in sources:
            self._scrape_pagesjaunes(regions)

        if "all" in sources or "societe" in sources:
            self._scrape_societe()

        if "all" in sources or "annuaires" in sources:
            self._scrape_annuaires(regions)

        logger.info(f"\nPhase 1 terminée: {len(self.companies)} entreprises collectées")

        # Phase 2: Google search for more companies + direct websites
        if "all" in sources or "google" in sources:
            logger.info("\n--- PHASE 2: Recherche Google ---")
            self._scrape_google(regions)
            logger.info(f"Après Google: {len(self.companies)} entreprises")

        # Phase 3: Deep email hunting — crawl company websites
        logger.info("\n--- PHASE 3: Recherche approfondie d'emails ---")
        self._hunt_emails()

        # Phase 4: Export
        logger.info("\n--- PHASE 4: Export ---")
        self._export_results()

        # Summary
        self._print_summary()

    def _scrape_pagesjaunes(self, regions):
        """Scrape Pages Jaunes for cleaning companies."""
        queries = ["nettoyage", "entreprise de nettoyage", "société de propreté"]
        total = len(queries) * len(regions)

        with tqdm(total=total, desc="Pages Jaunes") as pbar:
            for query in queries:
                for region in regions:
                    try:
                        companies = search_pagesjaunes(query, region, max_pages=3)
                        for c in companies:
                            self.add_company(c)
                    except Exception as e:
                        logger.error(f"PJ error: {query} in {region}: {e}")
                    pbar.update(1)
                    random_delay(1, 3)

    def _scrape_societe(self):
        """Scrape societe.com for cleaning companies."""
        queries = [
            "nettoyage", "propreté", "entreprise nettoyage",
            "nettoyage industriel", "nettoyage bureaux",
        ]

        with tqdm(total=len(queries), desc="Societe.com") as pbar:
            for query in queries:
                try:
                    companies = search_societe(query, max_pages=3)
                    companies = filter_cleaning_companies(companies)

                    for c in companies:
                        # Get details for extra info
                        if c.get("detail_url"):
                            details = get_company_details(c["detail_url"])
                            c.update(details)
                            random_delay(1, 2)

                        self.add_company(c)
                except Exception as e:
                    logger.error(f"Societe.com error for '{query}': {e}")
                pbar.update(1)

    def _scrape_annuaires(self, regions):
        """Scrape additional directories."""
        queries = ["nettoyage", "entreprise nettoyage"]

        with tqdm(total=len(queries) * len(regions), desc="Annuaires") as pbar:
            for query in queries:
                for region in regions:
                    try:
                        companies = search_118712(query, region)
                        for c in companies:
                            self.add_company(c)
                    except Exception as e:
                        logger.debug(f"118712 error: {e}")

                    try:
                        companies = search_horaires_douverture(query, region)
                        for c in companies:
                            self.add_company(c)
                    except Exception as e:
                        logger.debug(f"Horaires error: {e}")

                    pbar.update(1)
                    random_delay(1, 2)

    def _scrape_google(self, regions):
        """Use Google to find company websites directly."""
        base_queries = self.config["search_queries"][:5]  # Limit to avoid captcha

        if self.args.quick:
            base_queries = base_queries[:2]
            regions = regions[:3]

        queries = build_search_queries(base_queries, regions)
        max_per_query = self.config.get("max_results_per_query", 30)

        with tqdm(total=len(queries), desc="Google Search") as pbar:
            for query in queries:
                try:
                    urls = search_google(query, num_results=max_per_query)

                    for url in urls:
                        if is_valid_company_url(url):
                            domain = get_domain(url)
                            # Quick check: fetch the homepage for company name + emails
                            resp = fetch_page(url, timeout=10)
                            if resp:
                                emails = extract_emails_from_html(resp.text)
                                company = {
                                    "name": _extract_company_name(resp.text, domain),
                                    "website": url,
                                    "source": "google",
                                    "emails": emails,
                                }
                                if company["name"]:
                                    self.add_company(company)

                            random_delay(0.5, 1.5)
                except Exception as e:
                    logger.error(f"Google error for '{query}': {e}")
                pbar.update(1)
                random_delay(2, 5)

    def _hunt_emails(self):
        """Deep-crawl company websites to find emails."""
        companies_with_website = [
            (key, c) for key, c in self.companies.items()
            if c.get("website") and get_domain(c["website"]) not in self.websites_crawled
        ]

        logger.info(f"Sites web à crawler: {len(companies_with_website)}")

        crawl_depth = self.config.get("crawl_depth", 2)
        max_pages = 10 if self.args.quick else 15

        with tqdm(total=len(companies_with_website), desc="Email hunting") as pbar:
            for key, company in companies_with_website:
                website = company["website"]
                domain = get_domain(website)

                if domain in self.websites_crawled:
                    pbar.update(1)
                    continue

                self.websites_crawled.add(domain)

                try:
                    result = hunt_emails_on_website(
                        website, max_pages=max_pages, crawl_depth=crawl_depth
                    )
                    if result["emails"]:
                        company.setdefault("emails", set()).update(result["emails"])
                        logger.info(
                            f"  {company['name']}: {len(result['emails'])} email(s) trouvé(s)"
                        )
                    if result["phones"] and not company.get("phone"):
                        company["phone"] = list(result["phones"])[0]

                except Exception as e:
                    logger.error(f"Email hunt error for {website}: {e}")

                pbar.update(1)

    def _export_results(self):
        """Export results to CSV."""
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        output_file = self.config.get("output_file", "output/entreprises_nettoyage.csv")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(output_file)

        # Also create a timestamped version
        timestamped_path = output_dir / f"entreprises_nettoyage_{timestamp}.csv"

        companies_list = list(self.companies.values())

        # Sort: companies with emails first
        companies_list.sort(key=lambda c: (
            -len(c.get("emails", set())),
            c.get("name", ""),
        ))

        if self.args.emails_only:
            companies_list = [c for c in companies_list if c.get("emails")]

        fieldnames = [
            "name", "emails", "phone", "website", "address",
            "siret", "siren", "naf_code", "source",
        ]

        for path in [output_path, timestamped_path]:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";",
                                       extrasaction="ignore")
                writer.writeheader()

                for company in companies_list:
                    row = company.copy()
                    # Convert emails set to semicomma-separated string
                    emails = row.get("emails", set())
                    if isinstance(emails, set):
                        row["emails"] = " | ".join(sorted(emails))
                    writer.writerow(row)

        logger.info(f"Exporté {len(companies_list)} entreprises vers {output_path}")
        logger.info(f"Copie horodatée: {timestamped_path}")

        # Also export emails-only list
        emails_path = output_dir / f"emails_nettoyage_{timestamp}.csv"
        with open(emails_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["email", "company_name", "website", "phone"])
            for company in companies_list:
                emails = company.get("emails", set())
                for email in sorted(emails):
                    writer.writerow([
                        email,
                        company.get("name", ""),
                        company.get("website", ""),
                        company.get("phone", ""),
                    ])

        email_count = sum(len(c.get("emails", set())) for c in companies_list)
        logger.info(f"Liste emails: {emails_path} ({email_count} emails)")

    def _print_summary(self):
        """Print final summary."""
        total = len(self.companies)
        with_email = sum(1 for c in self.companies.values() if c.get("emails"))
        total_emails = sum(len(c.get("emails", set())) for c in self.companies.values())
        with_phone = sum(1 for c in self.companies.values() if c.get("phone"))
        with_website = sum(1 for c in self.companies.values() if c.get("website"))

        logger.info("\n" + "=" * 60)
        logger.info("RÉSUMÉ FINAL")
        logger.info("=" * 60)
        logger.info(f"  Entreprises trouvées:   {total}")
        logger.info(f"  Avec email:             {with_email} ({_pct(with_email, total)})")
        logger.info(f"  Total emails uniques:   {total_emails}")
        logger.info(f"  Avec téléphone:         {with_phone} ({_pct(with_phone, total)})")
        logger.info(f"  Avec site web:          {with_website} ({_pct(with_website, total)})")
        logger.info("=" * 60)

        # Show top companies with most emails
        if with_email > 0:
            logger.info("\nTop entreprises (par nombre d'emails):")
            sorted_companies = sorted(
                self.companies.values(),
                key=lambda c: len(c.get("emails", set())),
                reverse=True,
            )
            for c in sorted_companies[:10]:
                emails = c.get("emails", set())
                if emails:
                    logger.info(f"  {c['name']}: {', '.join(sorted(emails))}")


def _extract_company_name(html, domain):
    """Try to extract company name from HTML or fall back to domain."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")

        # Try <title>
        title = soup.find("title")
        if title:
            name = title.get_text(strip=True)
            # Clean up common suffixes
            for sep in [" - ", " | ", " – ", " — ", " :: "]:
                if sep in name:
                    name = name.split(sep)[0].strip()
            if name and len(name) > 2:
                return name

        # Try <h1>
        h1 = soup.find("h1")
        if h1:
            name = h1.get_text(strip=True)
            if name and len(name) > 2:
                return name

        # Try og:site_name
        og = soup.find("meta", property="og:site_name")
        if og and og.get("content"):
            return og["content"].strip()

    except Exception:
        pass

    # Fallback: domain name
    return domain.replace(".fr", "").replace(".com", "").replace("-", " ").title()


def _pct(part, total):
    """Format percentage."""
    if total == 0:
        return "0%"
    return f"{part / total * 100:.1f}%"


def main():
    parser = argparse.ArgumentParser(
        description="Scraper pour entreprises de nettoyage en France - Recherche d'emails"
    )
    parser.add_argument(
        "--quick", action="store_true",
        help="Mode rapide: moins de régions et de résultats"
    )
    parser.add_argument(
        "--source", nargs="+",
        choices=["google", "pagesjaunes", "societe", "annuaires", "all"],
        default=None,
        help="Sources à utiliser (défaut: toutes)"
    )
    parser.add_argument(
        "--regions", nargs="+", default=None,
        help="Régions/villes à cibler"
    )
    parser.add_argument(
        "--emails-only", action="store_true",
        help="N'exporter que les entreprises avec email"
    )

    args = parser.parse_args()
    config = load_config()

    scraper = NettoyageScraper(config, args)
    try:
        scraper.run()
    finally:
        close_selenium_driver()


if __name__ == "__main__":
    main()
