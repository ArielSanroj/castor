"""
Repository Pattern implementation for CASTOR.

Provides database abstraction following Fowler's Repository Pattern,
allowing easy swapping of database implementations.

Usage:
    from repositories import unit_of_work

    # Using context manager (recommended)
    with unit_of_work() as uow:
        user = uow.users.create(email="test@example.com", password="secret")
        analysis = uow.analyses.create(
            user_id=str(user.id),
            location="Bogota",
            theme="Seguridad",
            candidate_name="Candidato",
            analysis_data={"key": "value"}
        )
        uow.commit()

    # Querying
    with unit_of_work() as uow:
        user = uow.users.get_by_email("test@example.com")
        analyses = uow.analyses.get_by_user(str(user.id))
"""

from .base import BaseRepository
from .user_repository import UserRepository
from .analysis_repository import AnalysisRepository
from .lead_repository import LeadRepository
from .unit_of_work import (
    UnitOfWork,
    unit_of_work,
    get_unit_of_work,
)

__all__ = [
    # Base
    "BaseRepository",
    # Repositories
    "UserRepository",
    "AnalysisRepository",
    "LeadRepository",
    # Unit of Work
    "UnitOfWork",
    "unit_of_work",
    "get_unit_of_work",
]
