"""Simple in-memory Long Term Memory (Memory Bank)
Production systems should use a DB or vector DB. This demo keeps memory in RAM.
"""
from typing import Dict, Any
import uuid, logging, time

logger = logging.getLogger(__name__)

class MemoryBank:
    def __init__(self):
        self._store = {}

    def save_profile(self, user_id: str, profile: Dict[str, Any]) -> str:
        key = user_id or str(uuid.uuid4())
        self._store[key] = {'profile': profile, 'ts': time.time()}
        logger.info(f"Saved profile for user_id={key}")
        return key

    def get_profile(self, user_id: str):
        return self._store.get(user_id)

    def list_profiles(self):
        return list(self._store.keys())
