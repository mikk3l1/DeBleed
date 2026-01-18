"""
Centralized configuration for DeBleed application.

This module contains all configuration dataclasses for the application,
including detection thresholds, OCR settings, export options, and performance limits.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DetectionConfig:
    """Configuration for page boundary detection.
    
    Attributes:
        page_confidence_threshold: Minimum confidence (0.0-1.0) for automatic page detection.
            Pages below this threshold are flagged for manual review. Default: 0.80
        borderline_confidence_threshold: Upper bound for borderline confidence range.
            Pages with confidence between page_confidence_threshold and this value
            are highlighted as "borderline" in UI. Default: 0.85
        canny_threshold_low: Lower threshold for Canny edge detection. Default: 50
        canny_threshold_high: Upper threshold for Canny edge detection. Default: 150
        min_region_area_ratio: Minimum area ratio (0.0-1.0) for valid page region. Default: 0.1
        max_region_area_ratio: Maximum area ratio (0.0-1.0) for valid page region. Default: 0.95
    """
    
    page_confidence_threshold: float = 0.80
    borderline_confidence_threshold: float = 0.85
    canny_threshold_low: int = 50
    canny_threshold_high: int = 150
    min_region_area_ratio: float = 0.1
    max_region_area_ratio: float = 0.95
    
    def __post_init__(self) -> None:
        """Validate configuration values."""
        if not 0.0 <= self.page_confidence_threshold <= 1.0:
            raise ValueError("page_confidence_threshold must be in [0.0, 1.0]")
        if not 0.0 <= self.borderline_confidence_threshold <= 1.0:
            raise ValueError("borderline_confidence_threshold must be in [0.0, 1.0]")
        if self.borderline_confidence_threshold < self.page_confidence_threshold:
            raise ValueError("borderline_confidence_threshold must be >= page_confidence_threshold")


@dataclass(frozen=True)
class OCRConfig:
    """Configuration for OCR text extraction.
    
    Attributes:
        confidence_threshold: Minimum confidence (0.0-1.0) for OCR word recognition.
            Words below this threshold are flagged with [?] markers. Default: 0.75
        tesseract_psm: Tesseract Page Segmentation Mode. Default: 3 (Fully automatic)
        tesseract_oem: Tesseract OCR Engine Mode. Default: 3 (Default, based on what is available)
        supported_languages: List of ISO 639-1 language codes to support. Default: ['eng', 'spa', 'fra', 'deu']
        default_language: Default language for OCR. Default: 'eng'
    """
    
    confidence_threshold: float = 0.75
    tesseract_psm: int = 3
    tesseract_oem: int = 3
    supported_languages: list[str] = field(default_factory=lambda: ['eng', 'spa', 'fra', 'deu'])
    default_language: str = 'eng'
    
    def __post_init__(self) -> None:
        """Validate configuration values."""
        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold must be in [0.0, 1.0]")
        if self.default_language not in self.supported_languages:
            raise ValueError(f"default_language '{self.default_language}' not in supported_languages")


@dataclass(frozen=True)
class ExportConfig:
    """Configuration for PDF and text export.
    
    Attributes:
        default_suffix: Suffix appended to source filename for cleaned exports. Default: '_cleaned'
        compression_quality: JPEG compression quality (1-100) for images in PDF. Default: 85
        preserve_metadata: Whether to include source PDF metadata in export. Default: False
        deterministic_generation: Disable timestamps for reproducible outputs. Default: True
    """
    
    default_suffix: str = '_cleaned'
    compression_quality: int = 85
    preserve_metadata: bool = False
    deterministic_generation: bool = True
    
    def __post_init__(self) -> None:
        """Validate configuration values."""
        if not 1 <= self.compression_quality <= 100:
            raise ValueError("compression_quality must be in [1, 100]")


@dataclass(frozen=True)
class PerformanceConfig:
    """Configuration for performance limits and timeouts.
    
    Attributes:
        max_memory_mb: Maximum total application memory usage in MB. Default: 500
        max_page_size_mb: Maximum individual page size in MB. Default: 100
        file_load_timeout_s: Timeout for loading PDF file in seconds. Default: 10
        layout_detection_timeout_s: Timeout for layout detection per page in seconds. Default: 5
        layout_detection_target_ms: Performance target for layout detection in ms. Default: 500
        ocr_timeout_s: Timeout for OCR per page in seconds. Default: 10
        ocr_target_s: Performance target for OCR per page in seconds. Default: 2
        thumbnail_size: Thumbnail dimensions (width, height) in pixels. Default: (200, 200)
        disk_space_safety_multiplier: Multiplier for estimated output size when checking disk space. Default: 2.0
    """
    
    max_memory_mb: int = 500
    max_page_size_mb: int = 100
    file_load_timeout_s: int = 10
    layout_detection_timeout_s: int = 5
    layout_detection_target_ms: int = 500
    ocr_timeout_s: int = 10
    ocr_target_s: int = 2
    thumbnail_size: tuple[int, int] = (200, 200)
    disk_space_safety_multiplier: float = 2.0
    
    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.max_memory_mb <= 0:
            raise ValueError("max_memory_mb must be > 0")
        if self.max_page_size_mb <= 0:
            raise ValueError("max_page_size_mb must be > 0")


# Global default configurations
DEFAULT_DETECTION_CONFIG = DetectionConfig()
DEFAULT_OCR_CONFIG = OCRConfig()
DEFAULT_EXPORT_CONFIG = ExportConfig()
DEFAULT_PERFORMANCE_CONFIG = PerformanceConfig()
