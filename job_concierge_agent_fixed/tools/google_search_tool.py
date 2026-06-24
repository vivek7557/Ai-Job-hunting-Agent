"""Mock Google Search Tool
In the demo this returns mock job postings. Replace the implementation for production.
"""
from typing import List, Dict
from agents.job_scraper_agent import fetch_real_jobs

def search_jobs(query: str, max_results: int = 20) -> List[Dict]:
    return fetch_real_jobs(query, top_k=max_results)
