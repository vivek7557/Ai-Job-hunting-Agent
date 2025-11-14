# Simple scraper that demonstrates fetching jobs. Replace with real scrapers/ APIs.
from datetime import datetime, timedelta


# Example job structure
# {
# 'id': '...', 'title': 'ML Engineer', 'company': 'X', 'location': 'India',
# 'posted_at': datetime, 'description': '... text ...', 'url': 'https://...'
# }


def fetch_recent_jobs(hours: int = 1):
"""Return a list of job dicts posted within the last `hours` hours.
Replace this function with real scrapers for Indeed/LinkedIn/Naukri or use job APIs.
For a production app, add rate-limiting, retries, and parsers for each source.
"""
now = datetime.utcnow()
# demo/static jobs
demo = [
{
'id': 'demo-1',
'title': 'Machine Learning Engineer',
'company': 'Acme AI',
'location': 'India',
'posted_at': now.isoformat(),
'description': 'We need ML engineer with Python, PyTorch, ML pipelines.',
'url': 'https://example.com/job/demo-1'
},
{
'id': 'demo-2',
'title': 'Data Scientist',
'company': 'DataCo',
'location': 'Remote',
'posted_at': (now - timedelta(minutes=30)).isoformat(),
'description': 'Data Scientist with SQL, Python, feature engineering experience.',
'url': 'https://example.com/job/demo-2'
}
]
# filter by last `hours` (demo already matches)
return demo
