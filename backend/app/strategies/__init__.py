"""
Topic Strategies for PND analysis.
Concrete implementations of ITopicStrategy.
"""
from .base_strategy import BaseTopicStrategy
from .seguridad import SeguridadStrategy
from .educacion import EducacionStrategy
from .salud import SaludStrategy
from .economia import EconomiaStrategy
from .infraestructura import InfraestructuraStrategy

__all__ = [
    'BaseTopicStrategy',
    'SeguridadStrategy',
    'EducacionStrategy',
    'SaludStrategy',
    'EconomiaStrategy',
    'InfraestructuraStrategy',
]
