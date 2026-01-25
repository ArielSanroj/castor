"""
E-14 Training Data Service.
Genera datos de entrenamiento para fine-tuning de modelos locales.
Usa Claude para generar ground truth de E-14s reales.
"""
import base64
import hashlib
import json
import logging
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import shutil

from services.e14_ocr_service import E14OCRService, get_e14_ocr_service

logger = logging.getLogger(__name__)


class E14TrainingService:
    """
    Servicio para generar datos de entrenamiento de E-14.

    Flujo:
    1. Procesa E-14 con Claude (genera ground truth)
    2. Guarda par (imagen, JSON) para entrenamiento
    3. Permite corrección manual del JSON
    4. Exporta en formato compatible con fine-tuning
    """

    def __init__(self, data_dir: str = "training_data/e14"):
        """
        Inicializa el servicio de entrenamiento.

        Args:
            data_dir: Directorio donde guardar los datos de entrenamiento
        """
        self.data_dir = Path(data_dir)
        self.images_dir = self.data_dir / "images"
        self.labels_dir = self.data_dir / "labels"
        self.exports_dir = self.data_dir / "exports"

        # Crear directorios
        for d in [self.images_dir, self.labels_dir, self.exports_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self.ocr_service = get_e14_ocr_service()
        self.manifest_path = self.data_dir / "manifest.json"
        self.manifest = self._load_manifest()

        logger.info(f"E14TrainingService inicializado en {self.data_dir}")
        logger.info(f"Ejemplos existentes: {len(self.manifest.get('samples', []))}")

    def _load_manifest(self) -> Dict:
        """Carga el manifest de datos de entrenamiento."""
        if self.manifest_path.exists():
            with open(self.manifest_path, 'r') as f:
                return json.load(f)
        return {
            "version": "1.0",
            "created_at": datetime.utcnow().isoformat(),
            "samples": [],
            "stats": {
                "total": 0,
                "validated": 0,
                "corrected": 0
            }
        }

    def _save_manifest(self):
        """Guarda el manifest."""
        self.manifest["updated_at"] = datetime.utcnow().isoformat()
        with open(self.manifest_path, 'w') as f:
            json.dump(self.manifest, f, indent=2, ensure_ascii=False)

    def process_and_save(
        self,
        pdf_path: Optional[str] = None,
        pdf_url: Optional[str] = None,
        pdf_bytes: Optional[bytes] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Procesa un E-14 con Claude y guarda para entrenamiento.

        Args:
            pdf_path: Ruta al PDF
            pdf_url: URL del PDF
            pdf_bytes: Bytes del PDF
            metadata: Metadata adicional (elección, fecha, etc.)

        Returns:
            Dict con info del sample creado
        """
        sample_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        # 1. Obtener PDF bytes
        if pdf_path:
            pdf_data = Path(pdf_path).read_bytes()
            source = pdf_path
        elif pdf_url:
            import httpx
            with httpx.Client(timeout=60) as client:
                pdf_data = client.get(pdf_url).content
            source = pdf_url
        elif pdf_bytes:
            pdf_data = pdf_bytes
            source = "bytes"
        else:
            raise ValueError("Debe proporcionar pdf_path, pdf_url o pdf_bytes")

        # 2. Calcular hash
        sha256 = hashlib.sha256(pdf_data).hexdigest()

        # Verificar si ya existe
        existing = [s for s in self.manifest.get("samples", []) if s.get("sha256") == sha256]
        if existing:
            logger.warning(f"E-14 ya procesado: {sha256[:16]}")
            return {"status": "duplicate", "sample_id": existing[0]["sample_id"]}

        # 3. Convertir a imágenes
        from pdf2image import convert_from_bytes
        import io

        pil_images = convert_from_bytes(pdf_data, dpi=150, fmt='PNG')

        # 4. Guardar imágenes individuales
        image_paths = []
        for i, img in enumerate(pil_images):
            img_filename = f"{sample_id}_page_{i+1:02d}.png"
            img_path = self.images_dir / img_filename
            img.save(img_path, "PNG")
            image_paths.append(str(img_path))

        # 5. Procesar con Claude OCR
        try:
            extraction = self.ocr_service.process_pdf(pdf_bytes=pdf_data)
            validation = self.ocr_service.validate_extraction(extraction)

            # Convertir a dict serializable
            extraction_dict = json.loads(
                json.dumps(extraction.dict(), default=str, ensure_ascii=False)
            )
            validation_dict = json.loads(
                json.dumps(validation.dict(), default=str, ensure_ascii=False)
            )

            ocr_success = True
            ocr_error = None

        except Exception as e:
            logger.error(f"Error OCR: {e}")
            extraction_dict = None
            validation_dict = None
            ocr_success = False
            ocr_error = str(e)

        # 6. Guardar label (ground truth)
        label_data = {
            "sample_id": sample_id,
            "sha256": sha256,
            "source": source,
            "pages": len(pil_images),
            "extraction": extraction_dict,
            "validation": validation_dict,
            "metadata": metadata or {},
            "ocr_success": ocr_success,
            "ocr_error": ocr_error,
            "processing_time_ms": int((time.time() - start_time) * 1000),
            "created_at": datetime.utcnow().isoformat(),
            "is_validated": False,
            "is_corrected": False,
            "corrections": []
        }

        label_path = self.labels_dir / f"{sample_id}.json"
        with open(label_path, 'w', encoding='utf-8') as f:
            json.dump(label_data, f, indent=2, ensure_ascii=False)

        # 7. Actualizar manifest
        sample_entry = {
            "sample_id": sample_id,
            "sha256": sha256,
            "source": source,
            "pages": len(pil_images),
            "images": image_paths,
            "label": str(label_path),
            "ocr_success": ocr_success,
            "is_validated": False,
            "created_at": datetime.utcnow().isoformat()
        }

        self.manifest["samples"].append(sample_entry)
        self.manifest["stats"]["total"] += 1
        self._save_manifest()

        logger.info(f"Sample {sample_id} guardado: {len(pil_images)} páginas, OCR={'OK' if ocr_success else 'FAIL'}")

        return {
            "status": "created",
            "sample_id": sample_id,
            "pages": len(pil_images),
            "ocr_success": ocr_success,
            "validation_passed": validation_dict.get("all_passed") if validation_dict else None,
            "label_path": str(label_path)
        }

    def correct_sample(self, sample_id: str, corrections: Dict[str, Any]) -> bool:
        """
        Aplica correcciones manuales a un sample.

        Args:
            sample_id: ID del sample
            corrections: Dict con correcciones {field_path: new_value}

        Returns:
            True si se aplicó correctamente
        """
        label_path = self.labels_dir / f"{sample_id}.json"
        if not label_path.exists():
            logger.error(f"Sample {sample_id} no encontrado")
            return False

        with open(label_path, 'r') as f:
            label_data = json.load(f)

        # Guardar correcciones
        label_data["corrections"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "corrections": corrections
        })
        label_data["is_corrected"] = True

        # Aplicar correcciones al extraction
        if label_data.get("extraction"):
            for path, value in corrections.items():
                self._apply_correction(label_data["extraction"], path, value)

        with open(label_path, 'w', encoding='utf-8') as f:
            json.dump(label_data, f, indent=2, ensure_ascii=False)

        # Actualizar manifest
        for sample in self.manifest["samples"]:
            if sample["sample_id"] == sample_id:
                sample["is_corrected"] = True
                break

        self.manifest["stats"]["corrected"] += 1
        self._save_manifest()

        logger.info(f"Sample {sample_id} corregido")
        return True

    def _apply_correction(self, data: Dict, path: str, value: Any):
        """Aplica una corrección a un path tipo 'partidos.0.total_votos'."""
        keys = path.split('.')
        obj = data
        for key in keys[:-1]:
            if key.isdigit():
                obj = obj[int(key)]
            else:
                obj = obj[key]
        final_key = keys[-1]
        if final_key.isdigit():
            obj[int(final_key)] = value
        else:
            obj[final_key] = value

    def validate_sample(self, sample_id: str) -> bool:
        """Marca un sample como validado (listo para entrenamiento)."""
        label_path = self.labels_dir / f"{sample_id}.json"
        if not label_path.exists():
            return False

        with open(label_path, 'r') as f:
            label_data = json.load(f)

        label_data["is_validated"] = True
        label_data["validated_at"] = datetime.utcnow().isoformat()

        with open(label_path, 'w', encoding='utf-8') as f:
            json.dump(label_data, f, indent=2, ensure_ascii=False)

        for sample in self.manifest["samples"]:
            if sample["sample_id"] == sample_id:
                sample["is_validated"] = True
                break

        self.manifest["stats"]["validated"] += 1
        self._save_manifest()

        return True

    def export_for_finetuning(
        self,
        output_format: str = "llava",
        only_validated: bool = True
    ) -> str:
        """
        Exporta datos para fine-tuning en formato específico.

        Args:
            output_format: 'llava', 'qwen', 'florence', 'jsonl'
            only_validated: Solo exportar samples validados

        Returns:
            Path al archivo exportado
        """
        samples = self.manifest["samples"]
        if only_validated:
            samples = [s for s in samples if s.get("is_validated")]

        if not samples:
            raise ValueError("No hay samples para exportar")

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        export_data = []

        for sample in samples:
            label_path = Path(sample["label"])
            if not label_path.exists():
                continue

            with open(label_path, 'r') as f:
                label_data = json.load(f)

            if not label_data.get("extraction"):
                continue

            # Preparar datos según formato
            if output_format == "llava":
                export_data.extend(self._format_llava(sample, label_data))
            elif output_format == "qwen":
                export_data.extend(self._format_qwen(sample, label_data))
            elif output_format == "jsonl":
                export_data.append(self._format_jsonl(sample, label_data))

        # Guardar export
        export_filename = f"e14_training_{output_format}_{timestamp}.json"
        export_path = self.exports_dir / export_filename

        with open(export_path, 'w', encoding='utf-8') as f:
            if output_format == "jsonl":
                for item in export_data:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
            else:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Exportado {len(export_data)} ejemplos a {export_path}")
        return str(export_path)

    def _format_llava(self, sample: Dict, label_data: Dict) -> List[Dict]:
        """Formato LLaVA/LLaVA-NeXT para fine-tuning."""
        extraction = label_data["extraction"]
        items = []

        # Un ejemplo por cada página (o uno combinado)
        for i, img_path in enumerate(sample["images"]):
            # Crear conversación
            conversation = [
                {
                    "from": "human",
                    "value": f"<image>\nExtrae todos los datos de esta página {i+1} del formulario E-14 electoral colombiano. Devuelve JSON estructurado."
                },
                {
                    "from": "gpt",
                    "value": json.dumps(extraction, ensure_ascii=False, indent=2)
                }
            ]

            items.append({
                "id": f"{sample['sample_id']}_p{i+1}",
                "image": img_path,
                "conversations": conversation
            })

        return items

    def _format_qwen(self, sample: Dict, label_data: Dict) -> List[Dict]:
        """Formato Qwen-VL para fine-tuning."""
        extraction = label_data["extraction"]
        items = []

        for i, img_path in enumerate(sample["images"]):
            items.append({
                "id": f"{sample['sample_id']}_p{i+1}",
                "conversations": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image", "image": img_path},
                            {"type": "text", "text": "Extrae todos los datos de este formulario E-14 electoral colombiano en formato JSON."}
                        ]
                    },
                    {
                        "role": "assistant",
                        "content": json.dumps(extraction, ensure_ascii=False)
                    }
                ]
            })

        return items

    def _format_jsonl(self, sample: Dict, label_data: Dict) -> Dict:
        """Formato JSONL genérico."""
        return {
            "sample_id": sample["sample_id"],
            "images": sample["images"],
            "extraction": label_data["extraction"],
            "validation": label_data.get("validation"),
            "is_corrected": label_data.get("is_corrected", False)
        }

    def get_stats(self) -> Dict:
        """Retorna estadísticas del dataset."""
        return {
            "total_samples": len(self.manifest["samples"]),
            "validated": self.manifest["stats"]["validated"],
            "corrected": self.manifest["stats"]["corrected"],
            "pending_validation": len([
                s for s in self.manifest["samples"]
                if not s.get("is_validated") and s.get("ocr_success")
            ]),
            "failed_ocr": len([
                s for s in self.manifest["samples"]
                if not s.get("ocr_success")
            ]),
            "total_pages": sum(s.get("pages", 0) for s in self.manifest["samples"]),
            "data_dir": str(self.data_dir)
        }

    def list_samples(self, only_pending: bool = False) -> List[Dict]:
        """Lista los samples disponibles."""
        samples = self.manifest["samples"]
        if only_pending:
            samples = [s for s in samples if not s.get("is_validated")]
        return samples


# ============================================================
# Singleton
# ============================================================

_training_service: Optional[E14TrainingService] = None


def get_e14_training_service(data_dir: str = "training_data/e14") -> E14TrainingService:
    """Obtiene instancia del servicio de entrenamiento."""
    global _training_service
    if _training_service is None:
        _training_service = E14TrainingService(data_dir)
    return _training_service
