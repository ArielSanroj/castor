"""
E-14 OCR Service using Tesseract.

Fallback/free OCR for E-14 forms when Vision API is not available.
Uses Tesseract for text extraction + structured parsing.

Note: Lower accuracy than Vision AI for handwritten numbers,
but useful for initial data population.
"""
import io
import json
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytesseract
from pdf2image import convert_from_bytes, convert_from_path
from PIL import Image, ImageEnhance, ImageFilter

logger = logging.getLogger(__name__)


@dataclass
class TesseractOCRResult:
    """Result from Tesseract E14 OCR processing."""
    extraction_id: str
    filename: str
    success: bool
    processing_time_ms: int

    # Header info
    corporacion: str = ""
    departamento: str = ""
    municipio: str = ""
    zona: str = ""
    puesto: str = ""
    mesa: str = ""

    # Vote data
    partidos: List[Dict[str, Any]] = field(default_factory=list)
    total_votos: int = 0
    votos_blancos: int = 0
    votos_nulos: int = 0

    # Quality metrics
    confidence: float = 0.0
    raw_text: str = ""
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None


class E14TesseractOCR:
    """
    Tesseract-based OCR for E-14 electoral forms.

    This is a fallback when Vision API is not available.
    Accuracy is lower but it's free and fast.
    """

    # Known Colombian political parties (2022 Congress elections)
    KNOWN_PARTIES = [
        "PARTIDO LIBERAL",
        "PARTIDO CONSERVADOR",
        "CAMBIO RADICAL",
        "CENTRO DEMOCR[AÁ]TICO",
        "PARTIDO DE LA U",
        "ALIANZA VERDE",
        "POLO DEMOCR[AÁ]TICO",
        "PACTO HIST[OÓ]RICO",
        "MIRA",
        "COLOMBIA JUSTA LIBRES",
        "PARTIDO COMUNES",
        "COALICI[OÓ]N ESPERANZA",
        "NUEVO LIBERALISMO",
        "FUERZA CIUDADANA",
        "MOVIMIENTO AUTORIDADES IND[IÍ]GENAS",
        "LIGA GOBERNANTES",
        "PARTIDO VERDE OXIGENO",
        "MOVIMIENTO UNITARIO",
        "SALVACI[OÓ]N NACIONAL",
        "SOMOS REGI[OÓ]N",
        "EN MARCHA",
        "GENTE EN MOVIMIENTO",
        "FUERZA DE LA PAZ",
        "UNI[OÓ]N PATRI[OÓ]TICA",
        "MAIS",
    ]

    # Noise patterns to filter out
    NOISE_PATTERNS = [
        r'^ACTA DE ESCRUTINIO',
        r'^JURADOS DE VOTACI[OÓ]N',
        r'^DELEGADOS$',
        r'^ELECCIONES\s*CONGRESO',
        r'^\d+ DE MARZO',
        r'^REGISTRADUR[IÍ]A',
        r'^DEPARTAMENTO',
        r'^MUNICIPIO',
        r'^LUGAR:',
        r'^ZONA:',
        r'^PUESTO:',
        r'^MESA:',
        r'^TOTAL\s*(=|VOTOS)',
        r'^SUFRAGANTES',
        r'^FORMATO\s*E-',
        r'^EN LA URNA',
        r'^INCINERADOS',
        r'^CIRCUNSCRIPCI[OÓ]N',
        r'^NACIONAL$',
        r'^\d{12,}',  # Long numbers (barcodes)
        r'^Ver:\s*\d+',
        r'^Pag:\s*\d+',
        r'^No\.\s*Form',
        r'^KIT\s*\d+',
        r'^Civ\d+',
        r'^X\s*[\d-]+\s*X',  # Code patterns
        r'VOTOS\s*(AGRUPACI|CANDIDATOS|SOLO)',
        r'LISTA\s*SIN\s*VOTO',
        r'^[|\-\[\]]+$',  # Lines with only symbols
        r'^\s*[0-9]{1,2}\s*$',  # Single numbers
        r'^[A-Z]{1,3}$',  # Very short text
        r'^SEC\.\s*ESC',  # School names
        r'^\(\s*$',  # Just parenthesis
        r'^ANTIOQUIA$',
        r'^MEDELLIN$',
        r'^BOGOT[AÁ]$',
    ]

    # Words that indicate it's NOT a party (false positives)
    NOT_PARTY_WORDS = [
        'DELEGADOS',
        'REGISTRADURIA',
        'ELECCIONES',
        'CONGRESO',
        'NACIONAL',
        'ANTIOQUIA',
        'MEDELLIN',
        'BOGOTA',
        'CUNDINAMARCA',
        'ATLANTICO',
        'VALLE',
        'SANTANDER',
        'DEPARTAMENTO',
        'MUNICIPIO',
        'CIRCUNSCRIPCION',
        'SUFRAGANTES',
        'URNA',
        'MESA',
        'ZONA',
        'PUESTO',
        'LUGAR',
        'FORMATO',
        'ACTA',
        'ESCRUTINIO',
        'JURADOS',
        'JURADO',
        'VOTACION',
        'MARZO',
        'FEBRERO',
        'ENERO',
        'VOTOS POR LA AGRUPACION',
        'VOTOS POR LA AGRUPACIÓN',
        'ORGANIZACIÓN SOCIO',
        'RGANIZACIÓN',
        'MNESYJES',
    ]

    def __init__(self, lang: str = "spa", dpi: int = 300):
        """
        Initialize Tesseract OCR.

        Args:
            lang: Tesseract language (spa for Spanish)
            dpi: DPI for PDF to image conversion
        """
        self.lang = lang
        self.dpi = dpi
        self.tesseract_config = '--oem 3 --psm 6'  # LSTM + uniform block

        # Verify tesseract is available
        try:
            pytesseract.get_tesseract_version()
            logger.info("Tesseract OCR initialized")
        except Exception as e:
            logger.error(f"Tesseract not available: {e}")
            raise

    def process_pdf(self, pdf_path: str) -> TesseractOCRResult:
        """
        Process a PDF file with Tesseract OCR.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            TesseractOCRResult with extracted data
        """
        start_time = time.time()
        extraction_id = str(uuid.uuid4())[:8]
        filename = os.path.basename(pdf_path)

        try:
            # Convert PDF to images
            images = convert_from_path(
                pdf_path,
                dpi=self.dpi,
                fmt='png'
            )

            if not images:
                return TesseractOCRResult(
                    extraction_id=extraction_id,
                    filename=filename,
                    success=False,
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    error="No images extracted from PDF"
                )

            # Process each page and combine results
            all_text = []
            for i, img in enumerate(images):
                # Preprocess image
                processed_img = self._preprocess_image(img)

                # Extract text
                text = pytesseract.image_to_string(
                    processed_img,
                    lang=self.lang,
                    config=self.tesseract_config
                )
                all_text.append(text)

            raw_text = "\n--- PAGE BREAK ---\n".join(all_text)

            # Parse extracted text
            result = self._parse_e14_text(raw_text, extraction_id, filename)
            result.processing_time_ms = int((time.time() - start_time) * 1000)
            result.raw_text = raw_text[:5000]  # Truncate for storage

            return result

        except Exception as e:
            logger.error(f"Error processing {filename}: {e}")
            return TesseractOCRResult(
                extraction_id=extraction_id,
                filename=filename,
                success=False,
                processing_time_ms=int((time.time() - start_time) * 1000),
                error=str(e)
            )

    def process_pdf_bytes(self, pdf_bytes: bytes, filename: str = "unknown.pdf") -> TesseractOCRResult:
        """
        Process PDF from bytes.

        Args:
            pdf_bytes: PDF file content as bytes
            filename: Original filename for reference

        Returns:
            TesseractOCRResult with extracted data
        """
        start_time = time.time()
        extraction_id = str(uuid.uuid4())[:8]

        try:
            images = convert_from_bytes(
                pdf_bytes,
                dpi=self.dpi,
                fmt='png'
            )

            if not images:
                return TesseractOCRResult(
                    extraction_id=extraction_id,
                    filename=filename,
                    success=False,
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    error="No images extracted from PDF"
                )

            all_text = []
            for img in images:
                processed_img = self._preprocess_image(img)
                text = pytesseract.image_to_string(
                    processed_img,
                    lang=self.lang,
                    config=self.tesseract_config
                )
                all_text.append(text)

            raw_text = "\n--- PAGE BREAK ---\n".join(all_text)

            result = self._parse_e14_text(raw_text, extraction_id, filename)
            result.processing_time_ms = int((time.time() - start_time) * 1000)
            result.raw_text = raw_text[:5000]

            return result

        except Exception as e:
            logger.error(f"Error processing {filename}: {e}")
            return TesseractOCRResult(
                extraction_id=extraction_id,
                filename=filename,
                success=False,
                processing_time_ms=int((time.time() - start_time) * 1000),
                error=str(e)
            )

    def _preprocess_image(self, img: Image.Image) -> Image.Image:
        """
        Preprocess image for better OCR results.

        Args:
            img: PIL Image

        Returns:
            Preprocessed PIL Image
        """
        # Convert to grayscale
        if img.mode != 'L':
            img = img.convert('L')

        # Enhance contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)

        # Sharpen
        img = img.filter(ImageFilter.SHARPEN)

        # Binarize (threshold)
        threshold = 150
        img = img.point(lambda x: 255 if x > threshold else 0, '1')

        return img

    def _parse_e14_text(self, text: str, extraction_id: str, filename: str) -> TesseractOCRResult:
        """
        Parse extracted text to E14 structure.

        Args:
            text: Raw OCR text
            extraction_id: Unique ID for this extraction
            filename: Source filename

        Returns:
            TesseractOCRResult with parsed data
        """
        result = TesseractOCRResult(
            extraction_id=extraction_id,
            filename=filename,
            success=True,
            processing_time_ms=0
        )

        warnings = []

        # Extract header info (improved patterns)
        result.corporacion = self._extract_corporacion(text, filename)
        result.departamento = self._extract_departamento(text)
        result.municipio = self._extract_municipio(text)
        result.zona = self._extract_field(text, r'ZONA[:\s]*(\d{1,3})', "")
        result.puesto = self._extract_puesto(text)
        result.mesa = self._extract_mesa(text, filename)

        # Extract votes with improved parser
        partidos = []
        vote_patterns = self._find_vote_patterns(text)

        for party_name, votes in vote_patterns:
            # Final validation
            if not self._is_valid_party_entry(party_name, votes):
                continue

            # Clean the name one more time
            clean_name = self._clean_party_name(party_name)
            if not clean_name or len(clean_name) < 5:
                continue

            # Determine confidence based on whether it's a known party
            is_known = self._is_known_party(clean_name) is not None
            confidence = 0.75 if is_known else 0.5

            partidos.append({
                "party_name": clean_name,
                "party_code": "",
                "votes": votes,
                "confidence": confidence,
                "needs_review": not is_known or votes == 0
            })

        # Remove duplicates (keep first occurrence)
        seen = set()
        unique_partidos = []
        for p in partidos:
            key = p["party_name"].upper()
            if key not in seen:
                seen.add(key)
                unique_partidos.append(p)

        result.partidos = unique_partidos

        # Calculate total from partidos if not found directly
        calculated_total = sum(p["votes"] for p in partidos)

        # Extract totals from text
        result.total_votos = self._extract_number(text, r'TOTAL\s*(?:VOTOS|SUFRAGANTES)?\s*[:\s=]+(\d+)', 0)
        result.votos_blancos = self._extract_number(text, r'(?:VOTOS\s*)?BLANCOS?\s*[:\s=]+(\d+)', 0)
        result.votos_nulos = self._extract_number(text, r'(?:VOTOS\s*)?NULOS?\s*[:\s=]+(\d+)', 0)

        # Use calculated total if extracted total is 0
        if result.total_votos == 0 and calculated_total > 0:
            result.total_votos = calculated_total
            warnings.append("Total calculated from party votes")

        # Calculate confidence based on what we found
        confidence_score = 0.0
        if result.corporacion:
            confidence_score += 0.15
        if result.departamento:
            confidence_score += 0.10
        if result.municipio:
            confidence_score += 0.10
        if result.mesa:
            confidence_score += 0.15
        if result.partidos:
            # More parties found = higher confidence
            party_confidence = min(len(result.partidos) / 20.0, 0.3)
            confidence_score += party_confidence
        if result.total_votos > 0:
            confidence_score += 0.20

        result.confidence = min(confidence_score, 1.0)

        # Warnings
        if result.confidence < 0.5:
            warnings.append("Low extraction confidence - manual review recommended")

        if not result.partidos:
            warnings.append("No party votes detected")
        elif len(result.partidos) < 5:
            warnings.append(f"Only {len(result.partidos)} parties detected (expected more)")

        result.warnings = warnings
        result.success = result.confidence > 0.2

        return result

    def _extract_departamento(self, text: str) -> str:
        """Extract departamento from text."""
        # Pattern: DEPARTAMENTO: 01 - ANTIOQUIA
        match = re.search(r'DEPARTAMENTO[:\s]*\d*\s*[-–]\s*([A-ZÁÉÍÓÚÑ\s]+?)(?:\n|\d|$)', text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # Fallback: just the name
        match = re.search(r'DEPARTAMENTO[:\s]+([A-ZÁÉÍÓÚÑ\s]+)', text, re.IGNORECASE)
        if match:
            return match.group(1).strip()[:30]

        return ""

    def _extract_municipio(self, text: str) -> str:
        """Extract municipio from text."""
        # Pattern: MUNICIPIO: 001 - MEDELLIN
        match = re.search(r'MUNICIPIO[:\s]*\d*\s*[-–]\s*([A-ZÁÉÍÓÚÑ\s]+?)(?:\n|\d|$)', text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # Fallback
        match = re.search(r'MUNICIPIO[:\s]+([A-ZÁÉÍÓÚÑ\s]+)', text, re.IGNORECASE)
        if match:
            return match.group(1).strip()[:30]

        return ""

    def _extract_puesto(self, text: str) -> str:
        """Extract puesto/lugar from text."""
        # Pattern: LUGAR: SEC.ESC. MANUEL URIBE ANGEL
        match = re.search(r'LUGAR[:\s]+(.+?)(?:\n|ZONA|$)', text, re.IGNORECASE)
        if match:
            return match.group(1).strip()[:50]

        # Pattern: PUESTO: 02
        match = re.search(r'PUESTO[:\s]+(\d+)', text, re.IGNORECASE)
        if match:
            return f"Puesto {match.group(1)}"

        return ""

    def _extract_corporacion(self, text: str, filename: str) -> str:
        """Extract corporacion from text or filename."""
        text_upper = text.upper()

        if 'SENADO' in text_upper or '_SEN_' in filename.upper():
            return "SENADO"
        elif 'CAMARA' in text_upper or 'CÁMARA' in text_upper or '_CAM_' in filename.upper():
            return "CAMARA"

        return ""

    def _extract_mesa(self, text: str, filename: str) -> str:
        """Extract mesa number from text or filename."""
        # Try from text
        match = re.search(r'MESA\s*(?:N[°oO]?)?\s*[:\s]+(\d+)', text, re.IGNORECASE)
        if match:
            return match.group(1)

        # Try from filename (first part is usually mesa ID)
        parts = filename.split('_')
        if parts and parts[0].isdigit():
            return parts[0]

        return ""

    def _extract_field(self, text: str, pattern: str, default: str) -> str:
        """Extract field using regex pattern."""
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match else default

    def _extract_number(self, text: str, pattern: str, default: int) -> int:
        """Extract number using regex pattern."""
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1).replace('.', '').replace(',', ''))
            except ValueError:
                pass
        return default

    def _is_noise_line(self, line: str) -> bool:
        """Check if line matches noise patterns."""
        line_upper = line.upper().strip()
        for pattern in self.NOISE_PATTERNS:
            if re.search(pattern, line_upper):
                return True
        return False

    def _is_known_party(self, text: str) -> Optional[str]:
        """Check if text matches a known party name."""
        text_upper = text.upper().strip()
        for party_pattern in self.KNOWN_PARTIES:
            if re.search(party_pattern, text_upper):
                return text_upper
        return None

    def _find_vote_patterns(self, text: str) -> List[Tuple[str, int]]:
        """
        Find party names and vote counts in text.

        Returns list of (party_name, votes) tuples.
        """
        results = []
        found_parties = set()

        lines = text.split('\n')

        for i, line in enumerate(lines):
            line = line.strip()
            if not line or len(line) < 8:
                continue

            # Skip obvious noise lines
            if self._is_noise_line(line):
                continue

            # Method 1: Try structured extraction (CODE VOTES - PARTY NAME)
            extracted = self._extract_party_and_votes_from_line(line)
            if extracted:
                party_name, votes = extracted
                normalized = party_name.upper()
                if normalized not in found_parties:
                    results.append((party_name, votes))
                    found_parties.add(normalized)
                continue

            # Method 2: Check for known party names with votes nearby
            known = self._is_known_party(line)
            if known:
                clean_known = self._clean_party_name(known)
                if clean_known and clean_known.upper() not in found_parties:
                    votes = self._extract_votes_near_line(lines, i)
                    if votes is not None and votes < 5000:
                        results.append((clean_known, votes))
                        found_parties.add(clean_known.upper())
                continue

            # Method 3: Look for PARTIDO/MOVIMIENTO/COALICIÓN keywords
            if re.search(r'(PARTIDO|MOVIMIENTO|COALICI|ALIANZA)', line.upper()):
                # Try to extract votes from this line
                numbers = re.findall(r'\b(\d{1,4})\b', line)
                if numbers:
                    votes = int(numbers[0])
                    party_name = self._clean_party_name(line)
                    if party_name and len(party_name) > 5 and votes < 5000:
                        normalized = party_name.upper()
                        if normalized not in found_parties:
                            results.append((party_name, votes))
                            found_parties.add(normalized)

        return results

    def _extract_votes_near_line(self, lines: List[str], index: int) -> Optional[int]:
        """Extract vote count from current line or nearby lines."""
        # Check current line
        current = lines[index] if index < len(lines) else ""
        numbers = re.findall(r'\b(\d{1,4})\b', current)
        if numbers:
            # Take last number (usually the vote count)
            return int(numbers[-1])

        # Check next 2 lines
        for offset in [1, 2]:
            if index + offset < len(lines):
                next_line = lines[index + offset].strip()
                if next_line and not self._is_noise_line(next_line):
                    numbers = re.findall(r'\b(\d{1,4})\b', next_line)
                    if numbers:
                        return int(numbers[0])

        return None

    def _is_valid_party_entry(self, name: str, votes: int) -> bool:
        """Validate if entry looks like a real party entry."""
        # Must have reasonable vote count
        if votes > 5000 or votes < 0:
            return False

        # Must have reasonable name length
        if len(name) < 5 or len(name) > 50:
            return False

        # Must start with letter
        if not name[0].isalpha():
            return False

        # Check for noise patterns
        if self._is_noise_line(name):
            return False

        # Check against known false positives
        name_upper = name.upper()
        for word in self.NOT_PARTY_WORDS:
            if name_upper == word or name_upper.startswith(word + ' ') or name_upper.endswith(' ' + word):
                return False
            # Also check if it's just the word
            if len(name_upper) < len(word) + 5 and word in name_upper:
                return False

        # Must have mostly letters
        letter_count = sum(1 for c in name if c.isalpha())
        if letter_count < len(name) * 0.6:
            return False

        return True

    def _clean_party_name(self, text: str) -> str:
        """Clean and normalize party name."""
        # Remove leading noise: codes, pipes, numbers, special chars
        name = re.sub(r'^[\d\s\|\-\[\]¿¡=:;,\.O0\(\)en]+', '', text)
        name = re.sub(r'^\d{1,4}\s*[;:\-\.iI]\s*', '', name)  # "0003 ; " or "0292 " patterns
        name = re.sub(r'^[A-Z]{1,4}\s+', '', name)  # Remove short codes like "PA", "ZN"

        # Remove trailing noise
        name = re.sub(r'[\d\s\|\-\[\]L\(\)E]+$', '', name)
        name = re.sub(r'\s+PO$', '', name)  # Trailing "PO" from "PACTO HISTÓRICO PO"

        # Remove vote count patterns embedded in name
        name = re.sub(r'\s*\d{4}\s*[:\.\-;]\s*', ' ', name)  # "0013 :" patterns
        name = re.sub(r'\s*\d{1,4}\s*$', '', name)  # Trailing numbers

        # Remove common OCR artifacts
        name = re.sub(r'[|¡\[\]_=\(\)]', '', name)

        # Remove page/form indicators
        name = re.sub(r'\s*(Ver|Pag|Form|KIT|Civ|EST|ARA|MA|NACIONA|PO|RADICA)$', '', name, flags=re.IGNORECASE)

        # Fix truncated party names
        name = re.sub(r'RADICA$', 'RADICAL', name)

        # Normalize whitespace
        name = re.sub(r'\s+', ' ', name)

        # Final cleanup
        name = name.strip(' -:;,.')

        # If name is too short after cleaning, return empty
        if len(name) < 5:
            return ""

        return name

    def _extract_party_and_votes_from_line(self, line: str) -> Optional[Tuple[str, int]]:
        """
        Extract party name and votes from a line with format:
        "CODE 0255 - PARTIDO NAME | |" or similar
        """
        # Pattern: optional code, number (votes), separator, party name
        match = re.search(r'(\d{1,4})\s*[-:\.]\s*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]+)', line)
        if match:
            votes = int(match.group(1))
            party_name = self._clean_party_name(match.group(2))
            if party_name and len(party_name) > 4 and votes < 5000:
                return (party_name, votes)

        # Alternative pattern: party name followed by votes
        match = re.search(r'([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{5,40}?)\s+(\d{1,4})\s*$', line)
        if match:
            party_name = self._clean_party_name(match.group(1))
            votes = int(match.group(2))
            if party_name and len(party_name) > 4 and votes < 5000:
                return (party_name, votes)

        return None


def get_tesseract_ocr() -> E14TesseractOCR:
    """Get Tesseract OCR instance."""
    return E14TesseractOCR()


# Test function
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python e14_tesseract_ocr.py <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    ocr = get_tesseract_ocr()
    result = ocr.process_pdf(pdf_path)

    print(f"\n=== Results for {result.filename} ===")
    print(f"Success: {result.success}")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Time: {result.processing_time_ms}ms")
    print(f"Corporacion: {result.corporacion}")
    print(f"Mesa: {result.mesa}")
    print(f"Partidos found: {len(result.partidos)}")
    print(f"Total votos: {result.total_votos}")

    if result.warnings:
        print(f"Warnings: {result.warnings}")
    if result.error:
        print(f"Error: {result.error}")
