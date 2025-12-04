"""Recommendation Agent with start/stop (pause/resume) support using SchedulerController.
Also exposes a record() hook for observability/metrics.
"""
import logging
import sys
import os
from typing import List, Dict
from pathlib import Path

# Add the parent directory and current directory to Python path
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(parent_dir))

# Try multiple import strategies
try:
    # Strategy 1: Direct import from same directory
    from jd_matcher_agent import JDMatcher
    from job_scraper_agent import fetch_real_jobs
    from scheduler_controller import SchedulerController
except ImportError:
    try:
        # Strategy 2: Import from job_concierge_agent_fixed package
        from job_concierge_agent_fixed.jd_matcher_agent import JDMatcher
        from job_concierge_agent_fixed.job_scraper_agent import fetch_real_jobs
        from job_concierge_agent_fixed.scheduler_controller import SchedulerController
    except ImportError:
        # Strategy 3: Show error and available modules
        print("Import Error: Cannot find required modules")
        print(f"Current directory: {current_dir}")
        print(f"Files in current directory: {list(current_dir.glob('*.py'))}")
        print(f"Python path: {sys.path}")
        raise

try:
    import agents.skill_extractor as skill_extractor
    extract_skills = skill_extractor.extract_skills
except ImportError:
    print("Warning: Could not import skill_extractor, continuing without it")
    extract_skills = None

logger = logging.getLogger(__name__)

class RecommendationAgent:
    def __init__(self):
        self.matcher = JDMatcher()
        self.scheduler = SchedulerController()
        self._last_run = None
        self._listeners = []  # A2A listeners or UI callbacks

    def recommend_once(self, resume_text: str, query: str, threshold: float = 0.2) -> List[Dict]:
        # FIXED: using correct function name + correct argument
        jobs = fetch_real_jobs(query, top_k=50)

        scored = self.matcher.score(resume_text, jobs)
        recommended = [s for s in scored if s['score'] >= threshold]

        logger.info(
            f"RecommendationAgent found {len(recommended)} recommendations for threshold={threshold}"
        )

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


# Test if this is the main streamlit app being run
if __name__ == "__main__":
    print("RecommendationAgent module loaded successfully!")
    print(f"Current directory: {Path(__file__).parent}")
    print(f"Available in this module: {dir()}")
