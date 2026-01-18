"""Data models for DeBleed application."""

from debleed.models.document import ScannedDocument
from debleed.models.enums import AdjustmentStatus, ExportFormat, JobStatus, ProcessingStatus
from debleed.models.export_job import BatchQueue, ExportJob
from debleed.models.ocr_result import OCRResult, TextBlock
from debleed.models.page import DetectedBoundary, Page, PrimaryPageRegion

__all__ = [
    # Enums
    "ProcessingStatus",
    "AdjustmentStatus",
    "ExportFormat",
    "JobStatus",
    # Page models
    "PrimaryPageRegion",
    "DetectedBoundary",
    "Page",
    # OCR models
    "TextBlock",
    "OCRResult",
    # Document models
    "ScannedDocument",
    # Export models
    "ExportJob",
    "BatchQueue",
]
