"""
DeBleed - Desktop Scan Cleaner Application with OCR

A desktop application that helps educators and students convert imperfect scanned
book pages into clean, readable, single-page PDFs with OCR text extraction for accessibility.
"""

__version__ = "0.1.0"
__author__ = "DeBleed Team"

from debleed.config.settings import (
    DetectionConfig,
    ExportConfig,
    OCRConfig,
    PerformanceConfig,
)

__all__ = [
    "__version__",
    "__author__",
    "DetectionConfig",
    "ExportConfig",
    "OCRConfig",
    "PerformanceConfig",
]
