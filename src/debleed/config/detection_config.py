"""Detection configuration for page boundary detection."""

from dataclasses import dataclass, field

from debleed.config.ocr_config import OCRConfig


@dataclass(frozen=True)
class DetectionConfig:
    """Configuration for layout detection stage.
    
    Attributes:
        page_confidence_threshold: Minimum confidence score (0.0-1.0) to consider detection valid
        borderline_confidence_threshold: Threshold above base where pages need visual flagging
        canny_threshold_low: Lower threshold for Canny edge detection
        canny_threshold_high: Upper threshold for Canny edge detection
        enable_rotation_detection: Whether to detect and auto-correct page rotation
        enable_debug_output: Whether to generate debug visualizations (edge maps, contours)
        ocr_config: Configuration for OCR text extraction (if enabled)
    """
    
    page_confidence_threshold: float = 0.80
    borderline_confidence_threshold: float = 0.85
    canny_threshold_low: int = 50
    canny_threshold_high: int = 150
    enable_rotation_detection: bool = True
    enable_debug_output: bool = False
    ocr_config: OCRConfig = field(default_factory=OCRConfig)
    
    def __post_init__(self) -> None:
        """Validate detection configuration."""
        if not 0.0 <= self.page_confidence_threshold <= 1.0:
            raise ValueError(f"page_confidence_threshold must be in [0.0, 1.0], got {self.page_confidence_threshold}")
        if not 0.0 <= self.borderline_confidence_threshold <= 1.0:
            raise ValueError(f"borderline_confidence_threshold must be in [0.0, 1.0], got {self.borderline_confidence_threshold}")
        if self.borderline_confidence_threshold < self.page_confidence_threshold:
            raise ValueError(
                f"borderline_confidence_threshold ({self.borderline_confidence_threshold}) "
                f"must be >= page_confidence_threshold ({self.page_confidence_threshold})"
            )
        if self.canny_threshold_low >= self.canny_threshold_high:
            raise ValueError(
                f"canny_threshold_low ({self.canny_threshold_low}) "
                f"must be < canny_threshold_high ({self.canny_threshold_high})"
            )
