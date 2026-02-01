"""
RAG (Retrieval Augmented Generation) Service for CASTOR ELECCIONES.
Main service combining retrieval and generation with SQLite storage.
"""
import logging
from typing import Any, Dict, List, Optional

import openai

from config import Config
from .rag_models import RetrievalResult
from .rag_vector_store import SQLiteVectorStore
from .rag_indexer import RAGIndexer
from .rag_sync import RAGDatabaseSync

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres CASTOR AI, un asistente experto en análisis electoral y campañas políticas en Colombia.

Tu rol es responder preguntas usando el CONTEXTO proporcionado de análisis históricos guardados.

Reglas:
1. Basa tus respuestas PRINCIPALMENTE en el contexto proporcionado (datos históricos reales)
2. Menciona fechas, ubicaciones y datos específicos cuando estén disponibles
3. Si el contexto no tiene información suficiente, indícalo y sugiere qué análisis realizar
4. Responde en español, de manera concisa y profesional
5. Da recomendaciones accionables basadas en los datos históricos
6. Compara tendencias entre diferentes análisis si es relevante
7. No inventes datos - solo usa lo que está en el contexto"""


class RAGService:
    """Main RAG service combining retrieval and generation."""

    def __init__(self, db_service=None):
        """Initialize RAG service."""
        self.openai_client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
        self.vector_store = SQLiteVectorStore(
            openai_client=self.openai_client,
            embedding_model=getattr(Config, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        )
        self.indexer = RAGIndexer(self.vector_store)
        self.model = Config.OPENAI_MODEL
        self.db_service = db_service
        self.system_prompt = SYSTEM_PROMPT
        self._sync = RAGDatabaseSync(db_service, self.indexer) if db_service else None

        logger.info(f"RAGService initialized with SQLite ({self.vector_store.count()} documents)")

    def set_db_service(self, db_service) -> None:
        """Set database service for historical data access."""
        self.db_service = db_service
        self._sync = RAGDatabaseSync(db_service, self.indexer)

    def sync_from_database(self, limit: int = 100) -> int:
        """Sync historical analyses from database to vector store."""
        if not self._sync:
            self._sync = RAGDatabaseSync(self.db_service, self.indexer)
        return self._sync.sync_all(limit)

    # Delegate indexing methods to indexer
    def index_analysis(self, analysis_id: str, analysis_data: Dict, metadata: Dict = None) -> List[str]:
        """Index an analysis into the vector store."""
        return self.indexer.index_analysis(analysis_id, analysis_data, metadata)

    def index_tweets(self, api_call_id: str, tweets: List[Dict], metadata: Dict = None) -> int:
        """Index tweets into the vector store."""
        return self.indexer.index_tweets(api_call_id, tweets, metadata)

    def index_pnd_metrics(self, api_call_id: str, pnd_metrics: List[Dict], metadata: Dict = None) -> int:
        """Index PND metrics into the vector store."""
        return self.indexer.index_pnd_metrics(api_call_id, pnd_metrics, metadata)

    def index_analysis_snapshot(self, api_call_id: str, snapshot: Dict, metadata: Dict = None) -> int:
        """Index analysis snapshot into the vector store."""
        return self.indexer.index_analysis_snapshot(api_call_id, snapshot, metadata)

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        location_filter: str = None,
        topic_filter: str = None
    ) -> List[RetrievalResult]:
        """Retrieve relevant documents for a query."""
        where = self._build_filter(location_filter, topic_filter)
        return self.vector_store.search(query_text=query, top_k=top_k, where=where)

    def _build_filter(self, location: str = None, topic: str = None) -> Optional[Dict]:
        """Build where filter for retrieval."""
        if not location and not topic:
            return None

        conditions = []
        if location:
            conditions.append({"location": location})
        if topic:
            conditions.append({"topic_name": topic})

        return conditions[0] if len(conditions) == 1 else {"$and": conditions}

    def generate_response(
        self,
        query: str,
        context_docs: List[RetrievalResult],
        conversation_history: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7
    ) -> str:
        """Generate response using retrieved context."""
        context = self._build_context(context_docs)
        messages = self._build_messages(query, context, conversation_history)

        try:
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=600
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generating RAG response: {e}")
            return "Lo siento, hubo un error generando la respuesta. Por favor intenta de nuevo."

    def _build_context(self, context_docs: List[RetrievalResult]) -> str:
        """Build context string from retrieved documents."""
        if not context_docs:
            return "No hay datos históricos disponibles. Sugiere al usuario realizar un análisis primero."

        parts = []
        for result in context_docs:
            relevance = f"[Relevancia: {result.score:.0%}]"
            parts.append(f"{relevance}\n{result.document.content}")

        return "\n\n---\n\n".join(parts)

    def _build_messages(
        self,
        query: str,
        context: str,
        history: Optional[List[Dict[str, str]]]
    ) -> List[Dict[str, str]]:
        """Build message list for OpenAI API."""
        messages = [{"role": "system", "content": self.system_prompt}]

        if history:
            messages.extend(history[-6:])

        user_message = f"""DATOS HISTÓRICOS DE ANÁLISIS:
{context}

---

PREGUNTA DEL USUARIO:
{query}

Responde basándote en los datos históricos proporcionados. Si no hay suficiente información, indícalo claramente:"""

        messages.append({"role": "user", "content": user_message})
        return messages

    def chat(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        top_k: int = 5,
        location_filter: str = None,
        topic_filter: str = None
    ) -> Dict[str, Any]:
        """Main RAG chat interface."""
        results = self.retrieve(query, top_k, location_filter, topic_filter)
        answer = self.generate_response(query, results, conversation_history)
        sources = self._format_sources(results)

        return {
            "answer": answer,
            "sources": sources,
            "documents_indexed": self.vector_store.count(),
            "documents_retrieved": len(results)
        }

    def _format_sources(self, results: List[RetrievalResult]) -> List[Dict]:
        """Format retrieval results as sources."""
        return [
            {
                "id": r.document.id,
                "score": round(r.score, 3),
                "type": r.document.metadata.get("chunk_type", "unknown"),
                "topic": r.document.metadata.get("topic_name"),
                "location": r.document.metadata.get("location"),
                "date": r.document.metadata.get("created_at"),
                "preview": r.document.content[:200] + "..." if len(r.document.content) > 200 else r.document.content
            }
            for r in results
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get RAG service statistics."""
        return {
            "documents_indexed": self.vector_store.count(),
            "embedding_model": getattr(Config, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            "generation_model": self.model,
            "sqlite_path": self.vector_store.db_path
        }

    def clear_index(self) -> None:
        """Clear all indexed documents."""
        self.vector_store.clear()
        logger.info("RAG index cleared")

    # =========================================================================
    # E-14 ELECTORAL FORMS INDEXING
    # =========================================================================

    def index_e14_form(
        self,
        extraction_id: str,
        extraction_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Indexar un formulario E-14 procesado en el RAG.
        Soporta formato Senado/Cámara 2022 con circunscripciones y voto preferente.

        Args:
            extraction_id: ID único de la extracción OCR
            extraction_data: Datos completos del E-14 (E14ExtractionResult o dict)
            metadata: Metadatos adicionales

        Returns:
            Número de documentos indexados
        """
        meta = metadata or {}
        documents = []

        # Extraer datos del header
        header = extraction_data.get('header', {})
        departamento = header.get('departamento_name', 'Desconocido')
        municipio = header.get('municipio_name', 'Desconocido')
        mesa_id = header.get('mesa_id') or f"{header.get('departamento_code', '00')}-{header.get('municipio_code', '000')}-{header.get('zona', '00')}-{header.get('puesto', '00')}-{header.get('mesa', '000')}"
        corporacion = header.get('corporacion', 'PRESIDENCIA')
        lugar = header.get('lugar', '')
        eleccion = header.get('eleccion', '')

        # Extraer datos de nivelación
        nivelacion = extraction_data.get('nivelacion', {})
        total_sufragantes = nivelacion.get('total_sufragantes_e11', 0)
        total_urna = nivelacion.get('total_votos_urna', 0)

        # Extraer votos especiales
        votos_esp = extraction_data.get('votos_especiales', {})
        votos_blanco = votos_esp.get('votos_blanco', 0)
        votos_nulos = votos_esp.get('votos_nulos', 0)
        votos_no_marcados = votos_esp.get('votos_no_marcados', 0)

        # Extraer partidos - soporta formato nuevo (circunscripciones) y antiguo (partidos)
        partidos = []

        # Formato nuevo: circunscripcion_nacional + circunscripcion_indigena
        circ_nacional = extraction_data.get('circunscripcion_nacional', {})
        circ_indigena = extraction_data.get('circunscripcion_indigena', {})

        if circ_nacional.get('partidos'):
            for p in circ_nacional['partidos']:
                p['circunscripcion'] = 'NACIONAL'
                partidos.append(p)

        if circ_indigena.get('partidos'):
            for p in circ_indigena['partidos']:
                p['circunscripcion'] = 'INDIGENA'
                partidos.append(p)

        # Formato antiguo: partidos directos
        if not partidos:
            partidos = extraction_data.get('partidos', [])

        # Calcular totales
        total_votos_partidos = sum(p.get('total_votos', 0) for p in partidos)
        total_computado = total_votos_partidos + votos_blanco + votos_nulos + votos_no_marcados

        # Confidence global
        overall_confidence = extraction_data.get('overall_confidence', 0.0)
        fields_needing_review = extraction_data.get('fields_needing_review', 0)

        # Contar partidos por circunscripción
        partidos_nacional = [p for p in partidos if p.get('circunscripcion') == 'NACIONAL']
        partidos_indigena = [p for p in partidos if p.get('circunscripcion') == 'INDIGENA']

        # Base metadata para todos los documentos
        base_meta = {
            "type": "e14_form",
            "extraction_id": extraction_id,
            "mesa_id": mesa_id,
            "departamento": departamento,
            "municipio": municipio,
            "corporacion": corporacion,
            "eleccion": eleccion,
            "lugar": lugar,
            "overall_confidence": overall_confidence,
            **meta
        }

        # 1. Documento resumen del E-14
        resumen_parts = [
            f"FORMULARIO E-14 - ACTA DE ESCRUTINIO",
            f"Elección: {eleccion}" if eleccion else "",
            f"Mesa: {mesa_id}",
            f"Corporación: {corporacion}",
            f"Ubicación: {lugar}, {municipio}, {departamento}",
            f"",
            f"NIVELACIÓN DE MESA:",
            f"- Total sufragantes (E-11): {total_sufragantes:,}",
            f"- Total votos en urna: {total_urna:,}",
            f"- Total computado: {total_computado:,}",
            f"- Diferencia: {total_urna - total_computado:+,}",
            f"",
            f"VOTOS ESPECIALES:",
            f"- Votos en blanco: {votos_blanco:,}",
            f"- Votos nulos: {votos_nulos:,}",
            f"- Tarjetas no marcadas: {votos_no_marcados:,}",
        ]

        # Agregar info de circunscripciones si aplica (Senado/Cámara)
        if partidos_nacional or partidos_indigena:
            resumen_parts.append("")
            resumen_parts.append("CIRCUNSCRIPCIONES:")
            if partidos_nacional:
                votos_nac = sum(p.get('total_votos', 0) for p in partidos_nacional)
                resumen_parts.append(f"- Nacional: {len(partidos_nacional)} partidos, {votos_nac:,} votos")
            if partidos_indigena:
                votos_ind = sum(p.get('total_votos', 0) for p in partidos_indigena)
                resumen_parts.append(f"- Indígena: {len(partidos_indigena)} partidos, {votos_ind:,} votos")

        resumen_parts.extend([
            f"",
            f"CONFIANZA OCR: {overall_confidence*100:.1f}%",
            f"Campos que requieren revisión: {fields_needing_review}"
        ])

        # Filtrar líneas vacías consecutivas
        resumen_parts = [p for p in resumen_parts if p or p == ""]

        documents.append(Document(
            id=f"e14_{extraction_id}_resumen",
            content="\n".join(resumen_parts),
            metadata={**base_meta, "chunk_type": "e14_summary"}
        ))

        # 2. Documento de resultados por partido/candidato
        if partidos:
            resultados_parts = [
                f"RESULTADOS ELECTORALES - {corporacion}",
                f"Elección: {eleccion}" if eleccion else "",
                f"Mesa: {mesa_id} | {municipio}, {departamento}",
                f""
            ]

            # Función para agregar resultados de una lista de partidos
            def agregar_resultados(lista_partidos, titulo=None):
                if not lista_partidos:
                    return
                if titulo:
                    resultados_parts.append(f"\n{titulo}:")

                partidos_ord = sorted(lista_partidos, key=lambda p: p.get('total_votos', 0), reverse=True)
                for i, partido in enumerate(partidos_ord, 1):
                    nombre = partido.get('party_name', 'Desconocido')
                    codigo = partido.get('party_code', '')
                    votos = partido.get('total_votos', 0)
                    votos_agrup = partido.get('votos_agrupacion', 0)
                    tipo = partido.get('tipo_lista', partido.get('list_type', ''))
                    porcentaje = (votos / total_computado * 100) if total_computado > 0 else 0

                    linea = f"#{i} {nombre} ({codigo}): {votos:,} votos ({porcentaje:.1f}%)"
                    if tipo == 'CON_VOTO_PREFERENTE' and votos_agrup > 0:
                        linea += f" [Lista: {votos_agrup:,}]"
                    resultados_parts.append(linea)

                    # Agregar candidatos individuales si hay voto preferente
                    candidatos = partido.get('votos_candidatos', [])
                    if candidatos:
                        for cand in sorted(candidatos, key=lambda c: c.get('votos', c.get('votes', 0)), reverse=True)[:5]:
                            cand_num = cand.get('numero', cand.get('candidate_number', '?'))
                            cand_votos = cand.get('votos', cand.get('votes', 0))
                            if cand_votos > 0:
                                resultados_parts.append(f"   - Candidato #{cand_num}: {cand_votos:,} votos")

            # Si hay circunscripciones separadas (Senado/Cámara)
            if partidos_nacional or partidos_indigena:
                agregar_resultados(partidos_nacional, "CIRCUNSCRIPCIÓN NACIONAL")
                agregar_resultados(partidos_indigena, "CIRCUNSCRIPCIÓN ESPECIAL INDÍGENA")
            else:
                resultados_parts.append("VOTOS POR PARTIDO/CANDIDATO:")
                agregar_resultados(partidos)

            resultados_parts.append(f"")
            resultados_parts.append(f"TOTAL VOTOS VÁLIDOS: {total_votos_partidos:,}")

            documents.append(Document(
                id=f"e14_{extraction_id}_resultados",
                content="\n".join(resultados_parts),
                metadata={
                    **base_meta,
                    "chunk_type": "e14_results",
                    "total_votos": total_votos_partidos,
                    "num_partidos": len(partidos)
                }
            ))

        # 3. Documento por cada partido (para búsquedas específicas)
        for partido in partidos:
            nombre = partido.get('party_name', 'Desconocido')
            codigo = partido.get('party_code', '')
            votos = partido.get('total_votos', 0)
            votos_agrupacion = partido.get('votos_agrupacion', 0)
            tipo_lista = partido.get('tipo_lista', partido.get('list_type', 'SIN_VOTO_PREFERENTE'))
            circunscripcion = partido.get('circunscripcion', 'NACIONAL')
            confidence = partido.get('confidence_total', overall_confidence)

            partido_content = f"""VOTOS DE {nombre.upper()} - E-14
Mesa: {mesa_id}
Ubicación: {municipio}, {departamento}
Corporación: {corporacion}
Elección: {eleccion}

Partido: {nombre}
Código: {codigo}
Circunscripción: {circunscripcion}
Tipo de lista: {tipo_lista}
Votos por lista/agrupación: {votos_agrupacion:,}
Total votos: {votos:,}
Porcentaje de mesa: {(votos/total_computado*100) if total_computado > 0 else 0:.2f}%
Confianza OCR: {confidence*100:.1f}%
"""

            # Agregar candidatos si hay voto preferente
            candidatos = partido.get('votos_candidatos', [])
            if candidatos:
                partido_content += "\nVotos por candidato (voto preferente):\n"
                for cand in sorted(candidatos, key=lambda c: c.get('votos', c.get('votes', 0)), reverse=True):
                    cand_num = cand.get('numero', cand.get('candidate_number', '?'))
                    cand_votos = cand.get('votos', cand.get('votes', 0))
                    if cand_votos > 0:
                        partido_content += f"- Candidato #{cand_num}: {cand_votos:,} votos\n"

            documents.append(Document(
                id=f"e14_{extraction_id}_partido_{codigo}",
                content=partido_content,
                metadata={
                    **base_meta,
                    "chunk_type": "e14_party",
                    "party_code": codigo,
                    "party_name": nombre,
                    "party_votes": votos,
                    "circunscripcion": circunscripcion,
                    "tipo_lista": tipo_lista,
                    "confidence": confidence
                }
            ))

        # 4. Documento de alertas/problemas (si hay campos con baja confianza)
        if fields_needing_review > 0 or overall_confidence < 0.8:
            alerta_content = f"""ALERTA OCR - E-14 CON POSIBLES PROBLEMAS
Mesa: {mesa_id}
Ubicación: {municipio}, {departamento}
Corporación: {corporacion}

INDICADORES DE RIESGO:
- Confianza general: {overall_confidence*100:.1f}% {'⚠️ BAJA' if overall_confidence < 0.7 else ''}
- Campos que requieren revisión: {fields_needing_review}
- Diferencia urna vs computado: {total_urna - total_computado:+,}

{'REQUIERE REVISIÓN MANUAL' if overall_confidence < 0.7 or fields_needing_review > 3 else 'REVISAR SI ES NECESARIO'}
"""

            documents.append(Document(
                id=f"e14_{extraction_id}_alerta",
                content=alerta_content,
                metadata={
                    **base_meta,
                    "chunk_type": "e14_alert",
                    "needs_review": True,
                    "risk_level": "HIGH" if overall_confidence < 0.7 else "MEDIUM"
                }
            ))

        # Indexar todos los documentos
        if documents:
            self.vector_store.add_documents(documents)
            logger.info(f"Indexed E-14 form {extraction_id}: {len(documents)} documents, mesa {mesa_id}")

        return len(documents)

    def index_e14_batch(
        self,
        extractions: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Indexar múltiples formularios E-14 en batch.

        Args:
            extractions: Lista de extracciones E-14
            metadata: Metadatos adicionales compartidos

        Returns:
            Resumen del indexado
        """
        total_indexed = 0
        successful = 0
        failed = 0
        errors = []

        for extraction in extractions:
            try:
                extraction_id = extraction.get('extraction_id', str(uuid.uuid4()))
                count = self.index_e14_form(extraction_id, extraction, metadata)
                total_indexed += count
                successful += 1
            except Exception as e:
                failed += 1
                errors.append({
                    "extraction_id": extraction.get('extraction_id', 'unknown'),
                    "error": str(e)
                })
                logger.warning(f"Error indexing E-14: {e}")

        logger.info(f"E-14 batch indexing complete: {successful} success, {failed} failed, {total_indexed} docs")

        return {
            "total_extractions": len(extractions),
            "successful": successful,
            "failed": failed,
            "documents_indexed": total_indexed,
            "errors": errors
        }

    def search_e14(
        self,
        query: str,
        top_k: int = 10,
        departamento: str = None,
        municipio: str = None,
        corporacion: str = None,
        party_name: str = None
    ) -> List[RetrievalResult]:
        """
        Búsqueda especializada en datos E-14.

        Args:
            query: Consulta de búsqueda
            top_k: Número de resultados
            departamento: Filtrar por departamento
            municipio: Filtrar por municipio
            corporacion: Filtrar por corporación
            party_name: Filtrar por nombre de partido

        Returns:
            Lista de resultados relevantes
        """
        # Construir filtros
        conditions = [{"type": "e14_form"}]

        if departamento:
            conditions.append({"departamento": departamento})
        if municipio:
            conditions.append({"municipio": municipio})
        if corporacion:
            conditions.append({"corporacion": corporacion})
        if party_name:
            conditions.append({"party_name": party_name})

        where = {"$and": conditions} if len(conditions) > 1 else conditions[0]

        return self.vector_store.search(
            query_text=query,
            top_k=top_k,
            where=where
        )

    def get_e14_stats(self) -> Dict[str, Any]:
        """
        Obtener estadísticas de E-14 indexados.

        Returns:
            Estadísticas de formularios indexados
        """
        stats = {
            "total_e14_documents": 0,
            "by_corporacion": {},
            "by_departamento": {},
            "alerts_count": 0
        }

        # Contar documentos E-14 en el store
        with sqlite3.connect(self.vector_store.db_path) as conn:
            cursor = conn.execute(
                "SELECT metadata FROM rag_documents WHERE metadata LIKE '%e14_form%'"
            )
            rows = cursor.fetchall()

            for row in rows:
                try:
                    metadata = json.loads(row[0])
                    if metadata.get('type') == 'e14_form':
                        stats["total_e14_documents"] += 1

                        # Por corporación
                        corp = metadata.get('corporacion', 'UNKNOWN')
                        stats["by_corporacion"][corp] = stats["by_corporacion"].get(corp, 0) + 1

                        # Por departamento
                        dept = metadata.get('departamento', 'UNKNOWN')
                        stats["by_departamento"][dept] = stats["by_departamento"].get(dept, 0) + 1

                        # Alertas
                        if metadata.get('chunk_type') == 'e14_alert':
                            stats["alerts_count"] += 1
                except:
                    pass

        return stats

    def chat_e14(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        top_k: int = 10,
        departamento: str = None,
        municipio: str = None,
        corporacion: str = None
    ) -> Dict[str, Any]:
        """
        Chat especializado para consultas sobre E-14 electorales.

        Args:
            query: Pregunta del usuario sobre datos electorales
            conversation_history: Historial de conversación
            top_k: Documentos a recuperar
            departamento: Filtrar por departamento
            municipio: Filtrar por municipio
            corporacion: Filtrar por corporación

        Returns:
            Respuesta con datos electorales
        """
        # Sistema prompt especializado para E-14
        e14_system_prompt = """Eres CASTOR Electoral, un asistente experto en análisis de resultados electorales de Colombia basado en formularios E-14.

Tu rol es responder preguntas sobre resultados electorales usando ÚNICAMENTE los datos de los formularios E-14 indexados.

DATOS DISPONIBLES EN E-14:
- Resultados por mesa de votación (votos por partido/candidato)
- Ubicación: departamento, municipio, zona, puesto, mesa
- Nivelación: sufragantes, votos en urna, votos computados
- Votos especiales: blancos, nulos, no marcados
- Confianza del OCR y campos que requieren revisión

REGLAS:
1. Responde SOLO con datos del contexto proporcionado
2. Menciona siempre la ubicación (departamento, municipio, mesa) de los datos
3. Si hay alertas de OCR baja confianza, menciónalas
4. Presenta números con formato de miles (ej: 1,234)
5. Si no hay datos suficientes, indica qué información falta
6. NO inventes datos - solo usa lo que está en el contexto

FORMATO DE RESPUESTA:
- Usa listas con viñetas para claridad
- Incluye porcentajes cuando sea relevante
- Agrupa por ubicación si hay múltiples mesas"""

        # Buscar documentos E-14 relevantes
        results = self.search_e14(
            query=query,
            top_k=top_k,
            departamento=departamento,
            municipio=municipio,
            corporacion=corporacion
        )

        # Construir contexto
        context_parts = []
        for result in results:
            doc = result.document
            relevance = f"[Relevancia: {result.score:.0%}]"
            context_parts.append(f"{relevance}\n{doc.content}")

        context = "\n\n---\n\n".join(context_parts) if context_parts else "No hay formularios E-14 indexados para esta consulta."

        # Construir mensajes
        messages = [{"role": "system", "content": e14_system_prompt}]

        if conversation_history:
            messages.extend(conversation_history[-6:])

        user_message = f"""DATOS DE FORMULARIOS E-14 INDEXADOS:
{context}

---

PREGUNTA SOBRE RESULTADOS ELECTORALES:
{query}

Responde basándote ÚNICAMENTE en los datos E-14 proporcionados:"""

        messages.append({"role": "user", "content": user_message})

        try:
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,  # Más bajo para respuestas más precisas
                max_tokens=800
            )
            answer = response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generating E-14 chat response: {e}")
            answer = "Error al procesar la consulta. Por favor intenta de nuevo."

        # Construir fuentes
        sources = [
            {
                "id": r.document.id,
                "score": round(r.score, 3),
                "type": r.document.metadata.get("chunk_type", "e14_form"),
                "mesa_id": r.document.metadata.get("mesa_id"),
                "departamento": r.document.metadata.get("departamento"),
                "municipio": r.document.metadata.get("municipio"),
                "corporacion": r.document.metadata.get("corporacion"),
                "preview": r.document.content[:150] + "..." if len(r.document.content) > 150 else r.document.content
            }
            for r in results
        ]

        return {
            "answer": answer,
            "sources": sources,
            "e14_documents_found": len(results),
            "filters_applied": {
                "departamento": departamento,
                "municipio": municipio,
                "corporacion": corporacion
            }
        }


# Singleton instance
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """Get or create RAG service singleton."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service


def init_rag_service(db_service=None) -> RAGService:
    """Initialize RAG service with database connection."""
    global _rag_service
    _rag_service = RAGService(db_service=db_service)
    return _rag_service
