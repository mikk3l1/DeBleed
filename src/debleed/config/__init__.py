"""Configuration module for DeBleed application."""

from debleed.config.detection_config import DetectionConfig
from debleed.config.export_config import ExportConfig
from debleed.config.ocr_config import OCRConfig
from debleed.config.performance_config import PerformanceConfig

# Default configuration instances for convenience
DEFAULT_DETECTION_CONFIG = DetectionConfig()
DEFAULT_OCR_CONFIG = OCRConfig()
DEFAULT_EXPORT_CONFIG = ExportConfig()
DEFAULT_PERFORMANCE_CONFIG = PerformanceConfig()

__all__ = [
    "DetectionConfig",
    "OCRConfig",
    "ExportConfig",
    "PerformanceConfig",
    "DEFAULT_DETECTION_CONFIG",
    "DEFAULT_OCR_CONFIG",
    "DEFAULT_EXPORT_CONFIG",
    "DEFAULT_PERFORMANCE_CONFIG",
]

