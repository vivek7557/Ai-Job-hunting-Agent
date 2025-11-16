"""Scheduler controller using APScheduler for pause/resume loop operations.
Falls back to a simple thread-based loop if APScheduler is not installed.
"""
import logging
import threading, time
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    APSCHEDULER_AVAILABLE = True
except Exception:
    APSCHEDULER_AVAILABLE = False

logger = logging.getLogger(__name__)

class SchedulerController:
    def __init__(self):
        self._job = None
        self._running = False
        if APSCHEDULER_AVAILABLE:
            self._scheduler = BackgroundScheduler()
            self._scheduler.start()
        else:
            self._thread = None

    def start_periodic(self, func, seconds=3600):
        """Start calling func() every `seconds`. Returns True if scheduled."""
        if APSCHEDULER_AVAILABLE:
            if self._job is None:
                self._job = self._scheduler.add_job(func, 'interval', seconds=seconds)
                self._running = True
                logger.info('Started APScheduler periodic job.')
                return True
            return False
        else:
            if self._thread is None or not self._thread.is_alive():
                self._running = True
                def loop():
                    while self._running:
                        try:
                            func()
                        except Exception as e:
                            logger.exception('Error in periodic function: %s', e)
                        time.sleep(seconds)
                self._thread = threading.Thread(target=loop, daemon=True)
                self._thread.start()
                logger.info('Started fallback thread-based periodic job.')
                return True
            return False

    def stop(self):
        if APSCHEDULER_AVAILABLE:
            if self._job:
                self._job.remove()
                self._job = None
            self._running = False
            logger.info('Stopped APScheduler job.')
        else:
            self._running = False
            logger.info('Stopped fallback thread loop.')

    def is_running(self):
        return self._running
