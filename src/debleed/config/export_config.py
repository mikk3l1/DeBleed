"""Export configuration for PDF and text output generation."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ExportConfig:
    """Configuration for PDF/text export stage.
    
    Attributes:
        default_suffix: Filename suffix added to cleaned PDFs (e.g., "_cleaned")
        compression_quality: JPEG compression quality for PDF images (1-100, higher = better)
        deterministic_generation: Whether to disable timestamps for reproducible PDFs
        preserve_metadata: Whether to copy metadata from source PDF to cleaned PDF
        default_output_directory: Directory for exports (None = same as source file)
    """
    
    default_suffix: str = "_cleaned"
    compression_quality: int = 85
    deterministic_generation: bool = True
    preserve_metadata: bool = False
    default_output_directory: str = None
    
    def __post_init__(self) -> None:
        """Validate export configuration."""
        if not 1 <= self.compression_quality <= 100:
            raise ValueError(f"compression_quality must be in [1, 100], got {self.compression_quality}")
        if not self.default_suffix:
            raise ValueError("default_suffix cannot be empty")
        if self.default_suffix.startswith('.'):
            raise ValueError(f"default_suffix should not start with '.', got '{self.default_suffix}'")
