"""Job Scraper Agent (enhanced mock version with long realistic JDs)."""

from typing import List, Dict
import datetime, logging, time
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

LONG_DESCRIPTION_TEMPLATE = """
We are hiring a {query} Engineer to design, develop, and deploy production-grade machine learning 
systems. Responsibilities include data preprocessing, feature engineering, building ML pipelines, 
training and evaluating models, A/B testing, and deploying models into production.

You will work with Python, SQL, TensorFlow/PyTorch, Scikit-learn, data pipelines, cloud platforms 
(AWS, GCP, Azure), CI/CD, Docker, Kubernetes, experiment tracking, and MLOps workflows.

Strong experience with machine learning algorithms, NLP, deep learning, and large datasets is expected.
Experience with model optimization, monitoring, vector databases, and LLMs is a plus.
"""

def _make_mock_job(query: str, i: int) -> Dict:
    now = datetime.datetime.utcnow()
    return {
        "id": f"job_{query}_{i}",
        "title": f"{query} Engineer {i}",
        "company": f"Company {i}",
        "posted_at": (now - datetime.timedelta(minutes=5*i)).isoformat() + "Z",
        "url": f"https://example.com/jobs/{query}/{i}",
        "description": LONG_DESCRIPTION_TEMPLATE.format(query=query)
    }

def fetch_fresh_jobs(query: str, max_results: int = 20) -> List[Dict]:
    """Return a list of job dicts (mock implementation)."""
    jobs = []
    for i in range(min(max_results, 10)):
        jobs.append(_make_mock_job(query, i))
    logger.info(f"Fetched {len(jobs)} enhanced mock jobs for query='{query}'")
    return jobs

def fetch_from_sources_parallel(query: str, sources: List[str], per_source: int = 5) -> List[Dict]:
    """Mock parallel fetch across multiple sources using ThreadPoolExecutor."""
    results = []

    def fetch_source(src):
        time.sleep(0.1)
        return [_make_mock_job(f"{query}_{src}", i) for i in range(per_source)]

    with ThreadPoolExecutor(max_workers=min(8, len(sources))) as ex:
        futures = [ex.submit(fetch_source, s) for s in sources]
        for f in futures:
            try:
                results.extend(f.result())
            except Exception:
                logger.exception('Error fetching from source')

    logger.info(f"Parallel fetched {len(results)} enhanced jobs from {len(sources)} sources")
    return results
