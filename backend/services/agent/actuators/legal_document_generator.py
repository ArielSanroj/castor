"""
Legal Document Generator for Electoral Intelligence Agent.
Generates formal legal documents for presentation to electoral judges.
"""
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum

from services.agent.config import AgentConfig, get_agent_config
from services.agent.analyzers.legal_classifier import (
    LegalClassifier,
    CPACAArticle,
    NullityCausal,
    LegalClassification,
)

logger = logging.getLogger(__name__)


class DocumentType(str, Enum):
    """Types of legal documents."""
    DEMANDA_NULIDAD = "DEMANDA_NULIDAD"  # Nullity lawsuit
    SOLICITUD_RECONTEO = "SOLICITUD_RECONTEO"  # Recount request
    RECURSO_APELACION = "RECURSO_APELACION"  # Appeal
    MEMORIAL_PRUEBAS = "MEMORIAL_PRUEBAS"  # Evidence memorial
    INFORME_ANOMALIAS = "INFORME_ANOMALIAS"  # Anomaly report


@dataclass
class LegalDocument:
    """Generated legal document."""
    document_id: str
    document_type: DocumentType
    title: str

    # Header info
    demandante: str  # Plaintiff
    demandado: str  # Defendant (usually electoral authority)
    corporacion: str
    circunscripcion: str
    fecha_eleccion: str

    # Legal basis
    cpaca_articles: List[CPACAArticle]
    causals: List[NullityCausal]

    # Content sections
    hechos: List[str]  # Facts
    pretensiones: List[str]  # Claims/requests
    fundamentos_derecho: List[str]  # Legal foundations
    pruebas: List[Dict[str, Any]]  # Evidence
    anexos: List[str]  # Attachments

    # Metadata
    generated_at: datetime = field(default_factory=datetime.utcnow)
    deadline: Optional[datetime] = None
    priority: str = "NORMAL"

    # Summary stats
    mesas_afectadas: int = 0
    votos_en_disputa: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'document_id': self.document_id,
            'document_type': self.document_type.value,
            'title': self.title,
            'demandante': self.demandante,
            'demandado': self.demandado,
            'corporacion': self.corporacion,
            'circunscripcion': self.circunscripcion,
            'fecha_eleccion': self.fecha_eleccion,
            'cpaca_articles': [a.value for a in self.cpaca_articles],
            'causals': [c.value for c in self.causals],
            'hechos': self.hechos,
            'pretensiones': self.pretensiones,
            'fundamentos_derecho': self.fundamentos_derecho,
            'pruebas': self.pruebas,
            'anexos': self.anexos,
            'generated_at': self.generated_at.isoformat(),
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'priority': self.priority,
            'mesas_afectadas': self.mesas_afectadas,
            'votos_en_disputa': self.votos_en_disputa,
        }


class LegalDocumentGenerator:
    """
    Generates formal legal documents for electoral disputes.
    Documents comply with Colombian CPACA requirements.
    """

    # Document templates
    DEMANDA_TEMPLATE = """
================================================================================
                    CONSEJO DE ESTADO
              SALA DE LO CONTENCIOSO ADMINISTRATIVO
                   SECCIÓN QUINTA
================================================================================

REFERENCIA: Demanda de Nulidad Electoral
DEMANDANTE: {demandante}
DEMANDADO: {demandado}
CORPORACIÓN: {corporacion}
CIRCUNSCRIPCIÓN: {circunscripcion}
FECHA ELECCIÓN: {fecha_eleccion}

================================================================================
                         DEMANDA DE NULIDAD ELECTORAL
                    (Artículos 139 y siguientes del CPACA)
================================================================================

{nombre_demandante}, identificado como aparece al pie de mi firma, actuando en
calidad de {calidad_demandante}, respetuosamente acudo ante esta Honorable
Corporación para interponer DEMANDA DE NULIDAD ELECTORAL contra el acto de
elección de {cargo_demandado}, con fundamento en los siguientes:

--------------------------------------------------------------------------------
                                  HECHOS
--------------------------------------------------------------------------------

{hechos}

--------------------------------------------------------------------------------
                              PRETENSIONES
--------------------------------------------------------------------------------

{pretensiones}

--------------------------------------------------------------------------------
                        FUNDAMENTOS DE DERECHO
--------------------------------------------------------------------------------

{fundamentos}

--------------------------------------------------------------------------------
                                PRUEBAS
--------------------------------------------------------------------------------

Solicito se decreten y practiquen las siguientes pruebas:

{pruebas}

--------------------------------------------------------------------------------
                                ANEXOS
--------------------------------------------------------------------------------

{anexos}

--------------------------------------------------------------------------------
                              NOTIFICACIONES
--------------------------------------------------------------------------------

Recibiré notificaciones en: {direccion_notificacion}
Correo electrónico: {email_notificacion}

Del Honorable Magistrado,

Atentamente,


_______________________________
{nombre_demandante}
C.C. {cedula_demandante}

Fecha de presentación: {fecha_presentacion}
Documento generado por: Sistema CASTOR - Inteligencia Electoral

================================================================================
                         TÉRMINO LEGAL DE PRESENTACIÓN
================================================================================
{info_termino}
================================================================================
"""

    INFORME_ANOMALIAS_TEMPLATE = """
================================================================================
           INFORME DE ANOMALÍAS ELECTORALES - SISTEMA CASTOR
================================================================================

Fecha de generación: {fecha_generacion}
Período analizado: {periodo}
Corporación: {corporacion}
Circunscripción: {circunscripcion}

================================================================================
                           RESUMEN EJECUTIVO
================================================================================

Total de mesas analizadas: {total_mesas}
Anomalías detectadas: {total_anomalias}
Mesas con irregularidades: {mesas_con_anomalias}
Votos potencialmente afectados: {votos_afectados}

Nivel de riesgo: {nivel_riesgo}

================================================================================
                        ANOMALÍAS POR TIPO
================================================================================

{anomalias_por_tipo}

================================================================================
                    ANOMALÍAS POR UBICACIÓN GEOGRÁFICA
================================================================================

{anomalias_por_ubicacion}

================================================================================
                      DETALLE DE ANOMALÍAS CRÍTICAS
================================================================================

{detalle_criticas}

================================================================================
                      CLASIFICACIÓN LEGAL (CPACA)
================================================================================

{clasificacion_legal}

================================================================================
                         RECOMENDACIONES
================================================================================

{recomendaciones}

================================================================================
                              ANEXOS
================================================================================

{anexos}

================================================================================
Documento generado automáticamente por el Sistema CASTOR
Agente de Inteligencia Electoral v1.0
================================================================================
"""

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or get_agent_config()
        self.classifier = LegalClassifier(config)
        logger.info("LegalDocumentGenerator initialized")

    def generate_nullity_demand(
        self,
        anomalies: List[Dict[str, Any]],
        demandante_info: Dict[str, str],
        corporacion: str,
        circunscripcion: str,
        fecha_eleccion: str,
        cargo_demandado: str = "miembros electos",
    ) -> LegalDocument:
        """
        Generate a nullity demand document (Demanda de Nulidad Electoral).

        Args:
            anomalies: List of detected anomalies
            demandante_info: Plaintiff information
            corporacion: Electoral body (SENADO, CAMARA, etc.)
            circunscripcion: Electoral district
            fecha_eleccion: Election date
            cargo_demandado: Position being contested

        Returns:
            LegalDocument ready for presentation
        """
        import uuid

        doc_id = f"DEM-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8]}"

        # Classify anomalies
        classifications = []
        for anomaly in anomalies:
            incident = {
                'id': anomaly.get('id', 0),
                'incident_type': anomaly.get('type', 'UNKNOWN'),
                'mesa_id': anomaly.get('mesa_id', ''),
                'delta_value': anomaly.get('details', {}).get('delta', 0),
                'created_at': datetime.utcnow().isoformat(),
            }
            classification = self.classifier.classify(incident)
            classifications.append(classification)

        # Determine primary articles and causals
        articles = set()
        causals = set()
        for c in classifications:
            articles.add(c.primary_article)
            causals.update(c.causals)

        # Calculate stats
        mesas_afectadas = len(set(a.get('mesa_id', '') for a in anomalies))
        votos_en_disputa = sum(
            a.get('details', {}).get('delta', 0)
            for a in anomalies
            if a.get('type') == 'ARITHMETIC_MISMATCH'
        )

        # Generate hechos (facts)
        hechos = self._generate_hechos(anomalies, corporacion, fecha_eleccion)

        # Generate pretensiones (claims)
        pretensiones = self._generate_pretensiones(articles, causals, cargo_demandado)

        # Generate fundamentos de derecho (legal foundations)
        fundamentos = self._generate_fundamentos(articles, causals)

        # Generate pruebas (evidence)
        pruebas = self._generate_pruebas(anomalies)

        # Generate anexos (attachments)
        anexos = self._generate_anexos(anomalies)

        # Calculate deadline (30 days for nullity per CPACA)
        deadline = datetime.utcnow() + timedelta(days=30)

        return LegalDocument(
            document_id=doc_id,
            document_type=DocumentType.DEMANDA_NULIDAD,
            title=f"Demanda de Nulidad Electoral - {corporacion} - {circunscripcion}",
            demandante=demandante_info.get('nombre', 'DEMANDANTE'),
            demandado="Registraduría Nacional del Estado Civil",
            corporacion=corporacion,
            circunscripcion=circunscripcion,
            fecha_eleccion=fecha_eleccion,
            cpaca_articles=list(articles),
            causals=list(causals),
            hechos=hechos,
            pretensiones=pretensiones,
            fundamentos_derecho=fundamentos,
            pruebas=pruebas,
            anexos=anexos,
            deadline=deadline,
            priority="HIGH" if CPACAArticle.ART_223 in articles else "NORMAL",
            mesas_afectadas=mesas_afectadas,
            votos_en_disputa=votos_en_disputa,
        )

    def generate_anomaly_report(
        self,
        anomalies: List[Dict[str, Any]],
        corporacion: str,
        circunscripcion: str,
        total_mesas: int,
    ) -> str:
        """
        Generate an anomaly report document.

        Args:
            anomalies: List of detected anomalies
            corporacion: Electoral body
            circunscripcion: Electoral district
            total_mesas: Total mesas analyzed

        Returns:
            Formatted report string
        """
        # Group anomalies by type
        by_type = {}
        for a in anomalies:
            atype = a.get('type', 'UNKNOWN')
            if atype not in by_type:
                by_type[atype] = []
            by_type[atype].append(a)

        # Group by location
        by_location = {}
        for a in anomalies:
            mesa_id = a.get('mesa_id', '')
            parts = mesa_id.split('-')
            location = parts[1] if len(parts) > 1 else 'DESCONOCIDO'
            if location not in by_location:
                by_location[location] = []
            by_location[location].append(a)

        # Format anomalies by type
        tipo_text = ""
        for atype, items in sorted(by_type.items(), key=lambda x: -len(x[1])):
            tipo_text += f"\n{atype}: {len(items)} casos\n"
            tipo_text += f"  Severidad promedio: {self._get_avg_severity(items)}\n"

        # Format by location
        location_text = ""
        for loc, items in sorted(by_location.items(), key=lambda x: -len(x[1]))[:10]:
            location_text += f"\n{loc}: {len(items)} anomalías\n"

        # Critical anomalies detail
        critical = [a for a in anomalies if a.get('severity') in ('CRITICAL', 'HIGH')]
        critical_text = ""
        for i, a in enumerate(critical[:20], 1):
            critical_text += f"\n{i}. [{a.get('severity')}] {a.get('type')}\n"
            critical_text += f"   Mesa: {a.get('mesa_id')}\n"
            details = a.get('details', {})
            if 'delta' in details:
                critical_text += f"   Discrepancia: {details['delta']} votos\n"
                critical_text += f"   (Esperado: {details.get('expected')}, Actual: {details.get('actual')})\n"

        # Legal classification
        legal_text = self._generate_legal_classification_summary(anomalies)

        # Recommendations
        recommendations = self._generate_recommendations(anomalies, by_type)

        # Calculate risk level
        critical_count = len([a for a in anomalies if a.get('severity') == 'CRITICAL'])
        if critical_count > 10:
            risk_level = "CRÍTICO"
        elif critical_count > 5:
            risk_level = "ALTO"
        elif len(anomalies) > 50:
            risk_level = "MEDIO"
        else:
            risk_level = "BAJO"

        # Calculate affected votes
        votos_afectados = sum(
            abs(a.get('details', {}).get('delta', 0))
            for a in anomalies
            if a.get('type') == 'ARITHMETIC_MISMATCH'
        )

        return self.INFORME_ANOMALIAS_TEMPLATE.format(
            fecha_generacion=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            periodo="Elecciones Congreso 2022",
            corporacion=corporacion,
            circunscripcion=circunscripcion,
            total_mesas=total_mesas,
            total_anomalias=len(anomalies),
            mesas_con_anomalias=len(set(a.get('mesa_id', '') for a in anomalies)),
            votos_afectados=votos_afectados,
            nivel_riesgo=risk_level,
            anomalias_por_tipo=tipo_text,
            anomalias_por_ubicacion=location_text,
            detalle_criticas=critical_text if critical_text else "No se detectaron anomalías críticas.",
            clasificacion_legal=legal_text,
            recomendaciones=recommendations,
            anexos="1. Listado completo de mesas analizadas\n2. Detalle de cada anomalía detectada\n3. Imágenes de formularios E-14 con irregularidades",
        )

    def generate_recount_request(
        self,
        anomalies: List[Dict[str, Any]],
        demandante_info: Dict[str, str],
        corporacion: str,
        mesas_solicitadas: List[str],
    ) -> LegalDocument:
        """
        Generate a recount request document.

        Args:
            anomalies: Related anomalies
            demandante_info: Requester information
            corporacion: Electoral body
            mesas_solicitadas: List of mesas to recount

        Returns:
            LegalDocument for recount request
        """
        import uuid

        doc_id = f"REC-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8]}"

        hechos = [
            f"En las elecciones para {corporacion} se presentaron irregularidades en el conteo de votos.",
            f"Se han identificado {len(anomalies)} anomalías en {len(mesas_solicitadas)} mesas de votación.",
            "Las anomalías incluyen discrepancias aritméticas entre los votos registrados y los totales.",
            "Existen indicios de errores en el proceso de escrutinio que afectan la veracidad del resultado.",
        ]

        pretensiones = [
            f"Se ordene el RECONTEO de los votos en las siguientes mesas: {', '.join(mesas_solicitadas[:10])}{'...' if len(mesas_solicitadas) > 10 else ''}",
            "Se verifique la correspondencia entre los formularios E-14 y los resultados publicados.",
            "Se corrijan las inconsistencias aritméticas detectadas.",
        ]

        # 5 days deadline for recount requests
        deadline = datetime.utcnow() + timedelta(days=5)

        return LegalDocument(
            document_id=doc_id,
            document_type=DocumentType.SOLICITUD_RECONTEO,
            title=f"Solicitud de Reconteo - {corporacion}",
            demandante=demandante_info.get('nombre', 'SOLICITANTE'),
            demandado="Comisión Escrutadora",
            corporacion=corporacion,
            circunscripcion="Nacional",
            fecha_eleccion=datetime.utcnow().strftime("%Y-%m-%d"),
            cpaca_articles=[CPACAArticle.ART_225],
            causals=[NullityCausal.ARITHMETIC_ERROR],
            hechos=hechos,
            pretensiones=pretensiones,
            fundamentos_derecho=[
                "Artículo 225 del CPACA - Nulidad por error aritmético",
                "Artículo 192 del Código Electoral - Reclamaciones en escrutinio",
            ],
            pruebas=self._generate_pruebas(anomalies),
            anexos=[f"Formulario E-14 de mesa {m}" for m in mesas_solicitadas[:20]],
            deadline=deadline,
            priority="URGENT",
            mesas_afectadas=len(mesas_solicitadas),
            votos_en_disputa=sum(a.get('details', {}).get('delta', 0) for a in anomalies),
        )

    def render_document(self, document: LegalDocument) -> str:
        """
        Render a LegalDocument to formatted text.

        Args:
            document: LegalDocument to render

        Returns:
            Formatted document string
        """
        if document.document_type == DocumentType.DEMANDA_NULIDAD:
            return self._render_demanda(document)
        elif document.document_type == DocumentType.SOLICITUD_RECONTEO:
            return self._render_reconteo(document)
        elif document.document_type == DocumentType.INFORME_ANOMALIAS:
            return self._render_informe(document)
        else:
            return self._render_generic(document)

    def _render_demanda(self, doc: LegalDocument) -> str:
        """Render nullity demand document."""
        hechos_text = "\n".join(f"HECHO {i}. {h}" for i, h in enumerate(doc.hechos, 1))
        pretensiones_text = "\n".join(f"PRETENSIÓN {i}. {p}" for i, p in enumerate(doc.pretensiones, 1))
        fundamentos_text = "\n".join(f"- {f}" for f in doc.fundamentos_derecho)
        pruebas_text = "\n".join(f"{i}. {p.get('descripcion', p)}" for i, p in enumerate(doc.pruebas, 1))
        anexos_text = "\n".join(f"Anexo {i}. {a}" for i, a in enumerate(doc.anexos, 1))

        # Calculate deadline info
        days_remaining = (doc.deadline - datetime.utcnow()).days if doc.deadline else 30
        info_termino = f"""
ARTÍCULO APLICABLE: {', '.join(str(a.value) if hasattr(a, 'value') else str(a) for a in doc.cpaca_articles)}
TÉRMINO: {days_remaining} días restantes para presentación
FECHA LÍMITE: {doc.deadline.strftime('%Y-%m-%d') if doc.deadline else 'N/A'}

ADVERTENCIA: La demanda de nulidad electoral debe presentarse dentro de los
treinta (30) días siguientes a la declaratoria de elección (Art. 139 CPACA).
"""

        return self.DEMANDA_TEMPLATE.format(
            demandante=doc.demandante,
            demandado=doc.demandado,
            corporacion=doc.corporacion,
            circunscripcion=doc.circunscripcion,
            fecha_eleccion=doc.fecha_eleccion,
            nombre_demandante=doc.demandante,
            calidad_demandante="ciudadano en ejercicio",
            cargo_demandado=f"la elección de {doc.corporacion}",
            hechos=hechos_text,
            pretensiones=pretensiones_text,
            fundamentos=fundamentos_text,
            pruebas=pruebas_text,
            anexos=anexos_text,
            direccion_notificacion="[DIRECCIÓN]",
            email_notificacion="[EMAIL]",
            cedula_demandante="[CÉDULA]",
            fecha_presentacion=datetime.utcnow().strftime("%Y-%m-%d"),
            info_termino=info_termino,
        )

    def _render_reconteo(self, doc: LegalDocument) -> str:
        """Render recount request document."""
        return f"""
================================================================================
                    SOLICITUD DE RECONTEO DE VOTOS
================================================================================

Documento No: {doc.document_id}
Fecha: {doc.generated_at.strftime('%Y-%m-%d')}
Corporación: {doc.corporacion}

SOLICITANTE: {doc.demandante}
DIRIGIDO A: {doc.demandado}

================================================================================
                                HECHOS
================================================================================

{chr(10).join(f'{i}. {h}' for i, h in enumerate(doc.hechos, 1))}

================================================================================
                             SOLICITUD
================================================================================

{chr(10).join(f'{i}. {p}' for i, p in enumerate(doc.pretensiones, 1))}

================================================================================
                          FUNDAMENTO LEGAL
================================================================================

{chr(10).join(f'- {f}' for f in doc.fundamentos_derecho)}

================================================================================
                              PRUEBAS
================================================================================

{chr(10).join(f'{i}. {p.get("descripcion", str(p))}' for i, p in enumerate(doc.pruebas, 1))}

================================================================================
                         MESAS SOLICITADAS
================================================================================

Total mesas: {doc.mesas_afectadas}
Votos en disputa: {doc.votos_en_disputa}

================================================================================
                         TÉRMINO DE RESPUESTA
================================================================================

Fecha límite: {doc.deadline.strftime('%Y-%m-%d') if doc.deadline else 'N/A'}
Días restantes: {(doc.deadline - datetime.utcnow()).days if doc.deadline else 'N/A'}

================================================================================
Documento generado por Sistema CASTOR - Inteligencia Electoral
================================================================================
"""

    def _render_generic(self, doc: LegalDocument) -> str:
        """Render generic legal document."""
        return f"""
================================================================================
                    {doc.title.upper()}
================================================================================

Documento No: {doc.document_id}
Tipo: {doc.document_type.value}
Fecha: {doc.generated_at.strftime('%Y-%m-%d %H:%M')}

Corporación: {doc.corporacion}
Circunscripción: {doc.circunscripcion}

================================================================================

HECHOS:
{chr(10).join(f'  {i}. {h}' for i, h in enumerate(doc.hechos, 1))}

PRETENSIONES:
{chr(10).join(f'  {i}. {p}' for i, p in enumerate(doc.pretensiones, 1))}

FUNDAMENTOS:
{chr(10).join(f'  - {f}' for f in doc.fundamentos_derecho)}

================================================================================
Mesas afectadas: {doc.mesas_afectadas}
Votos en disputa: {doc.votos_en_disputa}
================================================================================
"""

    def _generate_hechos(
        self,
        anomalies: List[Dict[str, Any]],
        corporacion: str,
        fecha_eleccion: str
    ) -> List[str]:
        """Generate facts section."""
        hechos = [
            f"El día {fecha_eleccion} se llevaron a cabo las elecciones para {corporacion} en todo el territorio nacional.",
            f"Durante el proceso de escrutinio se identificaron {len(anomalies)} irregularidades en los formularios E-14.",
        ]

        # Group by type
        by_type = {}
        for a in anomalies:
            atype = a.get('type', 'UNKNOWN')
            by_type[atype] = by_type.get(atype, 0) + 1

        if 'ARITHMETIC_MISMATCH' in by_type:
            hechos.append(
                f"Se detectaron {by_type['ARITHMETIC_MISMATCH']} casos de discrepancias aritméticas "
                "donde la suma de votos por candidatos no coincide con el total registrado."
            )

        if 'IMPOSSIBLE_VALUE' in by_type:
            hechos.append(
                f"Se encontraron {by_type['IMPOSSIBLE_VALUE']} valores imposibles o fuera de rango "
                "en los conteos de votos, lo que indica posibles errores de transcripción o manipulación."
            )

        if 'GEOGRAPHIC_CLUSTER' in by_type:
            hechos.append(
                f"Se identificaron {by_type['GEOGRAPHIC_CLUSTER']} clusters geográficos de anomalías, "
                "sugiriendo un patrón sistemático en determinadas zonas."
            )

        # Calculate total disputed votes
        total_delta = sum(
            abs(a.get('details', {}).get('delta', 0))
            for a in anomalies
            if a.get('type') == 'ARITHMETIC_MISMATCH'
        )
        if total_delta > 0:
            hechos.append(
                f"Las irregularidades afectan un total estimado de {total_delta:,} votos, "
                "cantidad que podría alterar el resultado de la elección."
            )

        return hechos

    def _generate_pretensiones(
        self,
        articles: set,
        causals: set,
        cargo: str
    ) -> List[str]:
        """Generate claims section."""
        pretensiones = [
            f"Se declare la NULIDAD de la elección de {cargo} en las mesas afectadas.",
        ]

        if NullityCausal.ARITHMETIC_ERROR in causals:
            pretensiones.append(
                "Se ordene la corrección de los errores aritméticos detectados en los formularios E-14."
            )

        if CPACAArticle.ART_225 in articles:
            pretensiones.append(
                "Se ordene el RECONTEO de votos en las mesas donde se detectaron discrepancias."
            )

        if NullityCausal.VIOLENCE_OR_FRAUD in causals:
            pretensiones.append(
                "Se investigue la posible comisión de fraude electoral y se remita a las autoridades competentes."
            )

        pretensiones.extend([
            "Se ordene a la Registraduría Nacional la entrega de los documentos electorales originales.",
            "Se condene en costas a la parte demandada.",
        ])

        return pretensiones

    def _generate_fundamentos(
        self,
        articles: set,
        causals: set
    ) -> List[str]:
        """Generate legal foundations section."""
        fundamentos = [
            "Constitución Política de Colombia, Artículo 258 - Derecho al voto",
            "Ley 1437 de 2011 (CPACA), Artículos 139 y siguientes - Nulidad Electoral",
        ]

        article_texts = {
            CPACAArticle.ART_223: "Artículo 223 CPACA - Causales de nulidad: violencia, fraude o cohecho",
            CPACAArticle.ART_224: "Artículo 224 CPACA - Nulidad por irregularidades en documentos electorales",
            CPACAArticle.ART_225: "Artículo 225 CPACA - Nulidad por error aritmético en escrutinio",
            CPACAArticle.ART_226: "Artículo 226 CPACA - Nulidad por falsedad en documentos electorales",
        }

        for article in articles:
            if article in article_texts:
                fundamentos.append(article_texts[article])

        fundamentos.extend([
            "Código Electoral (Decreto 2241 de 1986) - Procedimientos de escrutinio",
            "Jurisprudencia del Consejo de Estado sobre nulidad electoral",
        ])

        return fundamentos

    def _generate_pruebas(self, anomalies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate evidence section."""
        pruebas = [
            {
                'tipo': 'DOCUMENTAL',
                'descripcion': 'Copia de los formularios E-14 donde se detectaron irregularidades',
                'cantidad': len(set(a.get('mesa_id', '') for a in anomalies)),
            },
            {
                'tipo': 'PERICIAL',
                'descripcion': 'Análisis técnico automatizado del Sistema CASTOR de Inteligencia Electoral',
                'metodologia': 'Detección de anomalías mediante algoritmos de validación aritmética y patrones',
            },
            {
                'tipo': 'DOCUMENTAL',
                'descripcion': 'Informe detallado de anomalías detectadas con coordenadas de cada mesa',
                'anexo': 'Informe_Anomalias_CASTOR.pdf',
            },
        ]

        # Add specific evidence for critical anomalies
        critical = [a for a in anomalies if a.get('severity') == 'CRITICAL']
        if critical:
            pruebas.append({
                'tipo': 'DOCUMENTAL',
                'descripcion': f'Evidencia específica de {len(critical)} anomalías CRÍTICAS',
                'detalle': [
                    f"Mesa {a.get('mesa_id')}: discrepancia de {a.get('details', {}).get('delta', 0)} votos"
                    for a in critical[:10]
                ],
            })

        pruebas.extend([
            {
                'tipo': 'TESTIMONIAL',
                'descripcion': 'Declaración de testigos electorales presentes en las mesas afectadas',
            },
            {
                'tipo': 'INSPECCIÓN',
                'descripcion': 'Solicitud de inspección judicial de los documentos electorales originales',
            },
        ])

        return pruebas

    def _generate_anexos(self, anomalies: List[Dict[str, Any]]) -> List[str]:
        """Generate attachments list."""
        mesas = list(set(a.get('mesa_id', '') for a in anomalies))

        anexos = [
            "Poder debidamente otorgado (si aplica)",
            "Copia de la cédula de ciudadanía del demandante",
            f"Listado de {len(mesas)} mesas con irregularidades detectadas",
            "Informe técnico del Sistema CASTOR de Inteligencia Electoral",
            "Capturas de pantalla de los formularios E-14 digitalizados",
        ]

        # Add specific mesa E-14s (first 20)
        for mesa in mesas[:20]:
            anexos.append(f"Formulario E-14 de mesa {mesa}")

        if len(mesas) > 20:
            anexos.append(f"... y {len(mesas) - 20} formularios E-14 adicionales (ver CD anexo)")

        return anexos

    def _generate_legal_classification_summary(self, anomalies: List[Dict[str, Any]]) -> str:
        """Generate legal classification summary."""
        classifications = {}

        for a in anomalies:
            incident = {
                'id': 0,
                'incident_type': a.get('type', 'UNKNOWN'),
                'mesa_id': a.get('mesa_id', ''),
                'delta_value': a.get('details', {}).get('delta', 0),
                'created_at': datetime.utcnow().isoformat(),
            }
            classification = self.classifier.classify(incident)

            article = classification.primary_article.value
            if article not in classifications:
                classifications[article] = {
                    'count': 0,
                    'causals': set(),
                    'deadline': classification.deadline_hours,
                }
            classifications[article]['count'] += 1
            classifications[article]['causals'].update(c.value for c in classification.causals)

        text = ""
        for article, data in sorted(classifications.items()):
            text += f"\n{article}: {data['count']} casos\n"
            text += f"  Causales: {', '.join(data['causals'])}\n"
            text += f"  Término: {data['deadline']} horas\n"

        return text

    def _generate_recommendations(
        self,
        anomalies: List[Dict[str, Any]],
        by_type: Dict[str, List]
    ) -> str:
        """Generate recommendations section."""
        recommendations = []

        if 'ARITHMETIC_MISMATCH' in by_type and len(by_type['ARITHMETIC_MISMATCH']) > 5:
            recommendations.append(
                "URGENTE: Presentar solicitud de reconteo dentro de los 5 días siguientes "
                "a la declaratoria de elección (Art. 225 CPACA)."
            )

        if 'GEOGRAPHIC_CLUSTER' in by_type:
            recommendations.append(
                "Investigar patrones geográficos de anomalías que podrían indicar "
                "coordinación o fraude sistemático."
            )

        critical_count = len([a for a in anomalies if a.get('severity') == 'CRITICAL'])
        if critical_count > 10:
            recommendations.append(
                "Considerar demanda de nulidad electoral ante el Consejo de Estado "
                "dado el alto número de anomalías críticas."
            )

        recommendations.extend([
            "Preservar toda la evidencia digital y documental.",
            "Notificar a los testigos electorales para obtener declaraciones.",
            "Solicitar copias autenticadas de los formularios E-14 originales.",
        ])

        return "\n".join(f"{i}. {r}" for i, r in enumerate(recommendations, 1))

    def _get_avg_severity(self, anomalies: List[Dict[str, Any]]) -> str:
        """Calculate average severity of anomalies."""
        severity_values = {'CRITICAL': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
        total = sum(severity_values.get(a.get('severity', 'LOW'), 1) for a in anomalies)
        avg = total / len(anomalies) if anomalies else 0

        if avg >= 3.5:
            return "CRÍTICA"
        elif avg >= 2.5:
            return "ALTA"
        elif avg >= 1.5:
            return "MEDIA"
        return "BAJA"
