"""Job Scraper Agent (mocked) with parallel fetching helpers.
"""
from typing import List, Dict
import datetime, logging, time
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

def _make_mock_job(query: str, i: int):
    now = datetime.datetime.utcnow()
    return {
        "id": f"job_{query}_{i}",
        "title": f"{query} Engineer {i}",
        "company": f"Company {i}",
        "posted_at": (now - datetime.timedelta(minutes=5*i)).isoformat() + "Z",
        "url": f"https://example.com/jobs/{query}/{i}",
        "description": f"We are looking for a {query} engineer. Skills: Python, SQL, Machine Learning."
    }

def fetch_fresh_jobs(query: str, max_results: int = 20) -> List[Dict]:
    """Return a list of job dicts (mock implementation)."""
    jobs = []
    for i in range(min(max_results, 10)):
        jobs.append(_make_mock_job(query, i))
    logger.info(f"Fetched {len(jobs)} mock jobs for query='{query}'")
    return jobs

def fetch_from_sources_parallel(query: str, sources: List[str], per_source: int = 5) -> List[Dict]:
    """Mock parallel fetch across multiple sources using ThreadPoolExecutor."""
    results = []
    def fetch_source(src):
        # simulate variable latency
        time.sleep(0.1)
        return [ _make_mock_job(f"{query}_{src}", i) for i in range(per_source) ]

    with ThreadPoolExecutor(max_workers=min(8, len(sources))) as ex:
        futures = [ex.submit(fetch_source, s) for s in sources]
        for f in futures:
            try:
                results.extend(f.result())
            except Exception:
                logger.exception('Error fetching from source')
    logger.info(f"Parallel fetched {len(results)} jobs from {len(sources)} sources") 
    return results
