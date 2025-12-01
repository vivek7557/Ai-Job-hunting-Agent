"""
Real Job Scraper — Indeed, Naukri, LinkedIn (Safe HTML Scraping)
"""

import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


# -------------------------
# 1. INDEED SCRAPER
# -------------------------
def scrape_indeed(query: str, location: str = "India", limit=5) -> List[Dict]:
    jobs = []
    q = query.replace(" ", "+")
    loc = location.replace(" ", "+")

    url = f"https://in.indeed.com/jobs?q={q}&l={loc}"

    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        cards = soup.select("div.job_seen_beacon")[:limit]

        for i, card in enumerate(cards):
            title = card.select_one("h2.jobTitle").text.strip() if card.select_one("h2.jobTitle") else "No Title"
            company = card.select_one("span.companyName").text.strip() if card.select_one("span.companyName") else "Unknown"
            desc = card.select_one("div.job-snippet").text.strip() if card.select_one("div.job-snippet") else ""
            jobs.append({
                "id": f"indeed_{i}",
                "title": title,
                "company": company,
                "url": f"https://in.indeed.com{card.a['href']}" if card.a else url,
                "description": desc
            })

        logger.info(f"Indeed scraped {len(jobs)} jobs")

    except Exception as e:
        logger.error("Indeed scraping error: %s", e)

    return jobs


# -------------------------
# 2. NAUKRI SCRAPER
# -------------------------
def scrape_naukri(query: str, limit=5) -> List[Dict]:
    jobs = []
    q = query.replace(" ", "-")
    url = f"https://www.naukri.com/{q}-jobs"

    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        cards = soup.select("article.jobTuple.bgWhite")[:limit]

        for i, card in enumerate(cards):
            title = card.select_one("a.title").text.strip() if card.select_one("a.title") else "No Title"
            company = card.select_one("a.subTitle").text.strip() if card.select_one("a.subTitle") else "Unknown"
            desc = card.select_one("div.job-description").text.strip() if card.select_one("div.job-description") else ""

            jobs.append({
                "id": f"naukri_{i}",
                "title": title,
                "company": company,
                "url": card.select_one("a.title")["href"] if card.select_one("a.title") else url,
                "description": desc
            })

        logger.info(f"Naukri scraped {len(jobs)} jobs")

    except Exception as e:
        logger.error("Naukri scraping error: %s", e)

    return jobs


# -------------------------
# 3. LINKEDIN (SAFE PUBLIC SEARCH)
# -------------------------
def scrape_linkedin(query: str, limit=5) -> List[Dict]:
    jobs = []
    q = query.replace(" ", "%20")

    url = f"https://www.linkedin.com/jobs/search/?keywords={q}&location=India"

    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        cards = soup.select("div.base-card")[:limit]

        for i, card in enumerate(cards):
            title = card.select_one("h3.base-search-card__title").text.strip() if card.select_one("h3.base-search-card__title") else "No Title"
            company = card.select_one("h4.base-search-card__subtitle").text.strip() if card.select_one("h4.base-search-card__subtitle") else "Unknown"
            desc = "LinkedIn does not expose full job description in HTML search results."

            url_el = card.select_one("a.base-card__full-link")
            link = url_el["href"] if url_el else url

            jobs.append({
                "id": f"linkedin_{i}",
                "title": title,
                "company": company,
                "url": link,
                "description": desc,
            })

        logger.info(f"LinkedIn scraped {len(jobs)} jobs")

    except Exception as e:
        logger.error("LinkedIn scraping error: %s", e)

    return jobs


# -------------------------
# MERGE ALL SOURCES
# -------------------------
def fetch_real_jobs(query: str, top_k: int = 10) -> List[Dict]:
    indeed = scrape_indeed(query, limit=5)
    naukri = scrape_naukri(query, limit=5)
    linkedin = scrape_linkedin(query, limit=5)

    jobs = indeed + naukri + linkedin
    jobs = jobs[:top_k]

    logger.info(f"Total scraped jobs: {len(jobs)}")

    return jobs
