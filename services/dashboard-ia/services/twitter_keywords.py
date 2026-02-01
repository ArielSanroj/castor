"""
Twitter PND Topic Keywords for CASTOR ELECCIONES.
Maps PND topics to Twitter search keywords.
"""
from typing import Dict

# PND Topic to Twitter search keywords mapping
PND_TOPIC_KEYWORDS: Dict[str, str] = {
    'Seguridad': 'seguridad OR delincuencia OR crimen OR policía OR robo',
    'Infraestructura': 'infraestructura OR vías OR carreteras OR transporte OR obras',
    'Gobernanza y Transparencia': 'transparencia OR corrupción OR gobernanza OR gobierno',
    'Educación': 'educación OR colegios OR universidad OR estudiantes OR maestros',
    'Salud': 'salud OR hospitales OR médicos OR EPS OR medicamentos',
    'Igualdad y Equidad': 'igualdad OR equidad OR género OR mujeres OR inclusión',
    'Paz y Reinserción': 'paz OR reinserción OR conflicto OR víctimas',
    'Economía y Empleo': 'economía OR empleo OR trabajo OR desempleo OR empresas',
    'Medio Ambiente y Cambio Climático': 'medio ambiente OR cambio climático OR contaminación',
    'Alimentación': 'alimentación OR comida OR hambre OR seguridad alimentaria'
}


def get_topic_keywords(topic: str) -> str:
    """
    Get search keywords for a PND topic.

    Args:
        topic: PND topic name

    Returns:
        Twitter search keywords string
    """
    return PND_TOPIC_KEYWORDS.get(topic, topic)
