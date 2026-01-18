"""OCR configuration for text extraction."""

from dataclasses import dataclass


@dataclass(frozen=True)
class OCRConfig:
    """Configuration for OCR text extraction stage.
    
    Attributes:
        confidence_threshold: Minimum confidence score (0.0-1.0) to consider word reliable
        tesseract_psm: Tesseract Page Segmentation Mode (3 = fully automatic)
        timeout_seconds: Maximum time allowed for OCR per page (hard limit)
        supported_languages: ISO 639-2 language codes supported for OCR (e.g., 'eng', 'spa', 'fra', 'deu')
        enable_layout_analysis: Whether to preserve text block positioning
    """
    
    confidence_threshold: float = 0.75
    tesseract_psm: int = 3
    timeout_seconds: int = 10
    supported_languages: list[str] = None
    enable_layout_analysis: bool = True
    
    def __post_init__(self) -> None:
        """Validate OCR configuration."""
        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError(f"confidence_threshold must be in [0.0, 1.0], got {self.confidence_threshold}")
        if self.tesseract_psm < 0 or self.tesseract_psm > 13:
            raise ValueError(f"tesseract_psm must be in [0, 13], got {self.tesseract_psm}")
        if self.timeout_seconds <= 0:
            raise ValueError(f"timeout_seconds must be > 0, got {self.timeout_seconds}")
        
        # Handle default mutable argument
        if self.supported_languages is None:
            object.__setattr__(self, 'supported_languages', ['eng', 'spa', 'fra', 'deu'])
        
        # Validate language codes
        for lang in self.supported_languages:
            if not isinstance(lang, str) or len(lang) != 3:
                raise ValueError(f"Language codes must be 3-character ISO 639-2 codes, got '{lang}'")
