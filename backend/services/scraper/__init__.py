"""
E-14 Scraper Module for Castor

Distributed scraper for Colombian electoral documents (E-14 forms).
Integrates with Castor's OCR pipeline and PostgreSQL backend.
"""

from .config import ScraperConfig, get_scraper_config
from .task_queue import TaskQueue, TaskStatus, TaskPriority
from .orchestrator import Orchestrator, run_orchestrator
from .e14_worker import E14Worker
from .captcha_solver import CaptchaSolver
from .proxy_manager import ProxyManager, get_proxy_manager

__all__ = [
    "ScraperConfig",
    "get_scraper_config",
    "TaskQueue",
    "TaskStatus",
    "TaskPriority",
    "Orchestrator",
    "run_orchestrator",
    "E14Worker",
    "CaptchaSolver",
    "ProxyManager",
    "get_proxy_manager",
]
