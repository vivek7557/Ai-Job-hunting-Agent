"""Mock Google Search Tool
In the demo this returns mock job postings. Replace the implementation for production.
"""
from typing import List, Dict
from agents.job_scraper_agent import fetch_fresh_jobs

def search_jobs(query: str, max_results: int = 20) -> List[Dict]:
    return fetch_fresh_jobs(query, max_results=max_results)
