"""Recommendation Agent with start/stop (pause/resume) support using SchedulerController.
Also exposes a record() hook for observability/metrics.
"""
import logging
from typing import List, Dict
from agents.jd_matcher_agent import JDMatcher
from agents.job_scraper_agent import fetch_real_jobs
from agents.scheduler_controller import SchedulerController


logger = logging.getLogger(__name__)

class RecommendationAgent:
    def __init__(self):
        self.matcher = JDMatcher()
        self.scheduler = SchedulerController()
        self._last_run = None
        self._listeners = []  # A2A listeners or UI callbacks

    def recommend_once(self, resume_text: str, query: str, threshold: float = 0.2) -> List[Dict]:
        jobs = fetch_real_jobs(query, top_k=50)
        scored = self.matcher.score(resume_text, jobs)
        recommended = [s for s in scored if s['score'] >= threshold]
        logger.info(f"RecommendationAgent found {len(recommended)} recommendations for threshold={threshold}")
        self._last_run = {'query': query, 'count': len(recommended)}
        # notify listeners (A2A)
        for l in self._listeners:
            try:
                l.handle_recommendations(recommended)
            except Exception:
                logger.exception('A2A listener error')
        return recommended

    def start_periodic(self, func, seconds=3600):
        return self.scheduler.start_periodic(func, seconds=seconds)

    def stop_periodic(self):
        self.scheduler.stop()

    def is_running(self):
        return self.scheduler.is_running()

    def add_listener(self, listener):
        """Add an A2A listener (object with handle_recommendations method)."""
        self._listeners.append(listener)
