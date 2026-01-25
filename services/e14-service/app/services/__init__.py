"""
Services package for E-14 Service.

Core OCR and processing services for E-14 electoral forms.
"""
from .e14_ocr_service import E14OCRService
from .qr_parser import (
    parse_qr_barcode,
    validate_qr_against_ocr,
    QRData,
    QRParseStatus,
)
from .electoral_alphabet import (
    parse_cell_value,
    normalize_cell_value,
    ParsedCell,
    MarkType,
)
from .cell_extractor import (
    ExtractedCell,
    CellType,
    CellBoundingBox,
)
from .hitl_review import (
    ReviewItem,
    ReviewQueue,
    ReviewPriority,
)

__all__ = [
    # OCR Service
    'E14OCRService',

    # QR Parser
    'parse_qr_barcode',
    'validate_qr_against_ocr',
    'QRData',
    'QRParseStatus',

    # Electoral Alphabet
    'parse_cell_value',
    'normalize_cell_value',
    'ParsedCell',
    'MarkType',

    # Cell Extractor
    'ExtractedCell',
    'CellType',
    'CellBoundingBox',

    # HITL Review
    'ReviewItem',
    'ReviewQueue',
    'ReviewPriority',
]
