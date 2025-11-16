"""Simple A2A (agent-to-agent) router.
Agents can register and send messages to other agents via the router.
Messages are simple dicts with 'from', 'to', 'type', 'payload'.
"""
import logging
from typing import Dict, Callable

logger = logging.getLogger(__name__)

class A2ARouter:
    def __init__(self):
        self._agents = {}

    def register(self, agent_name: str, handler: Callable[[Dict], None]):
        self._agents[agent_name] = handler
        logger.info(f"Registered agent {agent_name} in A2A router")

    def send(self, to: str, msg: Dict):
        handler = self._agents.get(to)
        if not handler:
            logger.warning(f"No agent registered under name {to}")
            return False
        try:
            handler(msg)
            return True
        except Exception as e:
            logger.exception('Error delivering A2A message: %s', e)
            return False
