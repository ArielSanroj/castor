"""
Auth Module.

Handles authentication and user management.
This module can be extracted as a microservice in the future.

Public Interface:
    - AuthModule: Main facade for auth operations
"""

from .facade import AuthModule

__all__ = [
    "AuthModule",
]
