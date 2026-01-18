"""
Exception hierarchy for DeBleed application.

This module defines typed exceptions for each pipeline stage,
enabling precise error handling and user-facing error messages.
"""

from typing import Optional


class DeBleedError(Exception):
    """Base exception for all DeBleed errors."""
    
    def __init__(self, message: str, details: Optional[dict[str, str | int | float]] = None) -> None:
        """Initialize error with message and optional details.
        
        Args:
            message: User-friendly error description
            details: Additional context for debugging (not shown to end users)
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class PreprocessingError(DeBleedError):
    """Error during PDF preprocessing stage.
    
    Error codes:
        - PDF_UNREADABLE: File cannot be opened or read
        - PAGE_OUT_OF_RANGE: Requested page number exceeds document page count
        - RENDER_FAILED: PDF page rendering to image failed
        - MEMORY_EXCEEDED: Page size exceeds memory limits
    """
    
    def __init__(
        self,
        message: str,
        error_code: str,
        page_number: Optional[int] = None,
        details: Optional[dict[str, str | int | float]] = None,
    ) -> None:
        """Initialize preprocessing error.
        
        Args:
            message: User-friendly error description
            error_code: One of: PDF_UNREADABLE, PAGE_OUT_OF_RANGE, RENDER_FAILED, MEMORY_EXCEEDED
            page_number: Page number where error occurred (if applicable)
            details: Additional error context
        """
        super().__init__(message, details)
        self.error_code = error_code
        self.page_number = page_number


class LayoutDetectionError(DeBleedError):
    """Error during layout detection stage.
    
    Error codes:
        - INVALID_IMAGE: Input image is corrupted or invalid format
        - NO_REGIONS_FOUND: No page boundaries could be detected
        - TIMEOUT: Detection exceeded max_page_detection_time
        - MEMORY_EXCEEDED: Processing exceeds memory limits
    """
    
    def __init__(
        self,
        message: str,
        error_code: str,
        page_number: Optional[int] = None,
        details: Optional[dict[str, str | int | float]] = None,
    ) -> None:
        """Initialize layout detection error.
        
        Args:
            message: User-friendly error description
            error_code: One of: INVALID_IMAGE, NO_REGIONS_FOUND, TIMEOUT, MEMORY_EXCEEDED
            page_number: Page number where error occurred
            details: Additional error context
        """
        super().__init__(message, details)
        self.error_code = error_code
        self.page_number = page_number


class OCRError(DeBleedError):
    """Error during OCR extraction stage.
    
    Error codes:
        - TESSERACT_NOT_FOUND: OCR engine not available or not initialized
        - LANGUAGE_NOT_AVAILABLE: Requested language pack not installed
        - INVALID_IMAGE: Input image is corrupted or invalid format
        - TIMEOUT: OCR exceeded max_ocr_time_per_page
    """
    
    def __init__(
        self,
        message: str,
        error_code: str,
        page_number: Optional[int] = None,
        language: Optional[str] = None,
        details: Optional[dict[str, str | int | float]] = None,
    ) -> None:
        """Initialize OCR error.
        
        Args:
            message: User-friendly error description
            error_code: One of: TESSERACT_NOT_FOUND, LANGUAGE_NOT_AVAILABLE, INVALID_IMAGE, TIMEOUT
            page_number: Page number where error occurred (if applicable)
            language: Requested language code (if applicable)
            details: Additional error context
        """
        super().__init__(message, details)
        self.error_code = error_code
        self.page_number = page_number
        self.language = language


class ExportError(DeBleedError):
    """Error during PDF/text export stage.
    
    Error codes:
        - INVALID_OUTPUT_PATH: Output path is invalid or inaccessible
        - WRITE_FAILED: File write operation failed
        - DISK_FULL: Insufficient disk space for export
        - PERMISSION_DENIED: No write permission to output directory
    """
    
    def __init__(
        self,
        message: str,
        error_code: str,
        output_path: Optional[str] = None,
        details: Optional[dict[str, str | int | float]] = None,
    ) -> None:
        """Initialize export error.
        
        Args:
            message: User-friendly error description
            error_code: One of: INVALID_OUTPUT_PATH, WRITE_FAILED, DISK_FULL, PERMISSION_DENIED
            output_path: Destination path where error occurred
            details: Additional error context
        """
        super().__init__(message, details)
        self.error_code = error_code
        self.output_path = output_path
