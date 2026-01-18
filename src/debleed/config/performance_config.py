"""Performance configuration for resource limits and timeouts."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PerformanceConfig:
    """Configuration for performance constraints and resource limits.
    
    Attributes:
        max_memory_mb: Maximum memory usage in megabytes for a single page
        max_file_load_time: Maximum time allowed for PDF loading (seconds)
        max_page_detection_time: Maximum time allowed for layout detection per page (seconds)
        max_ocr_time_per_page: Maximum time allowed for OCR per page (seconds)
        thumbnail_size: Target dimensions (width, height) for preview thumbnails
        enable_incremental_memory_release: Whether to release page N-1 after processing N
    """
    
    max_memory_mb: int = 500
    max_file_load_time: int = 10
    max_page_detection_time: int = 5
    max_ocr_time_per_page: int = 10
    thumbnail_size: tuple[int, int] = (200, 200)
    enable_incremental_memory_release: bool = True
    
    def __post_init__(self) -> None:
        """Validate performance configuration."""
        if self.max_memory_mb <= 0:
            raise ValueError(f"max_memory_mb must be > 0, got {self.max_memory_mb}")
        if self.max_file_load_time <= 0:
            raise ValueError(f"max_file_load_time must be > 0, got {self.max_file_load_time}")
        if self.max_page_detection_time <= 0:
            raise ValueError(f"max_page_detection_time must be > 0, got {self.max_page_detection_time}")
        if self.max_ocr_time_per_page <= 0:
            raise ValueError(f"max_ocr_time_per_page must be > 0, got {self.max_ocr_time_per_page}")
        if len(self.thumbnail_size) != 2:
            raise ValueError(f"thumbnail_size must be (width, height) tuple, got {self.thumbnail_size}")
        if self.thumbnail_size[0] <= 0 or self.thumbnail_size[1] <= 0:
            raise ValueError(f"thumbnail_size dimensions must be > 0, got {self.thumbnail_size}")
