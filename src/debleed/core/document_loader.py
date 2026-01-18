"""Document loading and initialization."""

from datetime import datetime
from pathlib import Path

import fitz  # PyMuPDF

from debleed.core.exceptions import PreprocessingError
from debleed.models.document import ScannedDocument
from debleed.models.enums import ProcessingStatus


def load_document(file_path: Path) -> ScannedDocument:
    """Load PDF document and create ScannedDocument instance.
    
    Document loading pipeline:
    1. Validate file exists and is a PDF
    2. Open PDF and extract page count
    3. Calculate file size for memory estimation
    4. Create ScannedDocument with LOADED status
    5. Validate PDF is not encrypted (FR-031)
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        ScannedDocument initialized with metadata, empty pages list
        
    Raises:
        PreprocessingError: If file doesn't exist, is not a PDF, or is encrypted
    """
    # Validate file exists
    if not file_path.exists():
        raise PreprocessingError(
            message=f"File not found: {file_path.name}",
            error_code="PDF_UNREADABLE",
            details={"path": str(file_path)},
        )
    
    if not file_path.is_file():
        raise PreprocessingError(
            message=f"Path is not a file: {file_path.name}",
            error_code="PDF_UNREADABLE",
            details={"path": str(file_path)},
        )
    
    # Validate PDF extension (FR-042: only PDF files supported)
    if file_path.suffix.lower() != ".pdf":
        raise PreprocessingError(
            message=f"Only PDF files are supported. Got: {file_path.suffix}",
            error_code="PDF_UNREADABLE",
            details={"path": str(file_path), "extension": file_path.suffix},
        )
    
    # Open PDF and extract metadata
    try:
        doc = fitz.open(file_path)
    except Exception as e:
        raise PreprocessingError(
            message=f"Cannot open PDF file: {file_path.name}",
            error_code="PDF_UNREADABLE",
            details={"path": str(file_path), "error": str(e)},
        )
    
    # Check if encrypted (FR-031: encrypted PDFs not supported)
    if doc.is_encrypted:
        doc.close()
        raise PreprocessingError(
            message="Encrypted PDFs are not supported",
            error_code="PDF_UNREADABLE",
            details={"path": str(file_path)},
        )
    
    # Extract page count
    page_count = doc.page_count
    if page_count == 0:
        doc.close()
        raise PreprocessingError(
            message="PDF has no pages",
            error_code="PDF_UNREADABLE",
            details={"path": str(file_path)},
        )
    
    doc.close()
    
    # Calculate file size
    file_size_bytes = file_path.stat().st_size
    
    # Create ScannedDocument
    document = ScannedDocument(
        file_path=file_path,
        page_count=page_count,
        processing_status=ProcessingStatus.LOADED,
        pages=[],  # Pages will be populated during processing
        created_at=datetime.now(),
        file_size_bytes=file_size_bytes,
    )
    
    return document
