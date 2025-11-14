from apscheduler.schedulers.background import BackgroundScheduler
from .scraper import fetch_recent_jobs
from .db import save_jobs


sched = None


def refresh_jobs_job():
jobs = fetch_recent_jobs(hours=1)
save_jobs(jobs)
print('Refreshed jobs:', len(jobs))




def start_scheduler():
global sched
if sched: return
sched = BackgroundScheduler()
# run every 60 minutes
sched.add_job(refresh_jobs_job, 'interval', minutes=60, next_run_time=None)
sched.start()
