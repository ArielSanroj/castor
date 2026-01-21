"""
Leads Module.

Handles lead management and CRM operations.
This module can be extracted as a microservice in the future.

Public Interface:
    - LeadsModule: Main facade for lead operations
"""

from .facade import LeadsModule

__all__ = [
    "LeadsModule",
]
