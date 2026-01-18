"""
Page and region data models for DeBleed application.

This module contains dataclasses representing pages, detected boundaries,
and primary page regions within scanned documents.
"""

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from numpy.typing import NDArray

from debleed.models.enums import AdjustmentStatus


@dataclass
class PrimaryPageRegion:
    """Geometric region representing intended page content.
    
    Attributes:
        coordinates: (x, y, width, height) in pixels, relative to parent Page image
        confidence_level: Confidence in this region being correct (0.0-1.0)
        area_percentage: Percentage of total page area occupied by this region
        detection_method: Method used ('contour_analysis', 'connected_components', 'manual')
    """
    
    coordinates: tuple[int, int, int, int]
    confidence_level: float
    area_percentage: float
    detection_method: str
    
    def __post_init__(self) -> None:
        """Validate region properties."""
        if not 0.0 <= self.confidence_level <= 1.0:
            raise ValueError("confidence_level must be in [0.0, 1.0]")
        if not 0.0 < self.area_percentage <= 100.0:
            raise ValueError("area_percentage must be in (0.0, 100.0]")
        if self.detection_method == "manual" and self.confidence_level != 1.0:
            raise ValueError("Manual adjustments must have confidence_level = 1.0")
    
    @property
    def bounding_box(self) -> tuple[tuple[int, int], ...]:
        """Four corner points for visualization."""
        x, y, w, h = self.coordinates
        return (
            (x, y),           # Top-left
            (x + w, y),       # Top-right
            (x + w, y + h),   # Bottom-right
            (x, y + h),       # Bottom-left
        )


@dataclass
class DetectedBoundary:
    """Calculated coordinates defining the primary page region with metadata.
    
    Attributes:
        primary_region: The main content region
        secondary_regions: Other detected regions (gutters, bleed, adjacent pages) for debugging
        detection_timestamp: When detection was performed
        detection_config: Configuration used (thresholds, parameters) for reproducibility
    """
    
    primary_region: PrimaryPageRegion
    secondary_regions: list[PrimaryPageRegion] = field(default_factory=list)
    detection_timestamp: Optional[str] = None
    detection_config: dict[str, float | int] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Validate boundary properties."""
        # Primary region must have highest confidence among all regions
        if self.secondary_regions:
            max_secondary_conf = max(r.confidence_level for r in self.secondary_regions)
            if max_secondary_conf > self.primary_region.confidence_level:
                raise ValueError("primary_region must have highest confidence")
    
    @property
    def is_confident(self) -> bool:
        """True if primary region confidence >= 0.80."""
        return self.primary_region.confidence_level >= 0.80
    
    @property
    def flagged_for_review(self) -> bool:
        """True if confidence is below threshold."""
        return not self.is_confident


@dataclass
class Page:
    """Individual page within a scanned document.
    
    Attributes:
        page_number: 1-based page index in document
        image_data: NumPy array containing rendered page image
        dimensions: (width, height) in pixels
        detected_boundary: Identified primary page region (None if not yet detected)
        confidence_score: Overall confidence in boundary detection (0.0-1.0)
        adjustment_status: AUTO, MANUAL, or FLAGGED
        is_borderline_confidence: True if confidence is 0.80-0.85 (per FR-041)
        preview_thumbnail: Smaller version for grid view (lazy-loaded)
        ocr_result: Extracted text (None if OCR not yet performed)
        rotation_angle: Detected rotation in degrees (0, 90, 180, 270)
    """
    
    page_number: int
    image_data: NDArray[np.uint8]
    dimensions: tuple[int, int]
    detected_boundary: Optional[DetectedBoundary] = None
    confidence_score: float = 0.0
    adjustment_status: AdjustmentStatus = AdjustmentStatus.AUTO
    is_borderline_confidence: bool = False
    preview_thumbnail: Optional[NDArray[np.uint8]] = None
    ocr_result: Optional[object] = None  # Typed as object to avoid circular import
    rotation_angle: int = 0
    
    def __post_init__(self) -> None:
        """Validate page properties."""
        if self.page_number < 1:
            raise ValueError("page_number must be >= 1")
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError("confidence_score must be in [0.0, 1.0]")
        if self.rotation_angle not in {0, 90, 180, 270}:
            raise ValueError("rotation_angle must be in {0, 90, 180, 270}")
        
        # Auto-set flags based on confidence
        if self.confidence_score < 0.80 and self.adjustment_status == AdjustmentStatus.AUTO:
            object.__setattr__(self, 'adjustment_status', AdjustmentStatus.FLAGGED)
        if 0.80 <= self.confidence_score <= 0.85:
            object.__setattr__(self, 'is_borderline_confidence', True)
    
    @property
    def needs_review(self) -> bool:
        """True if confidence < 0.80 or flagged for review."""
        return self.confidence_score < 0.80 or self.adjustment_status == AdjustmentStatus.FLAGGED
    
    @property
    def has_manual_adjustment(self) -> bool:
        """True if user manually adjusted boundaries."""
        return self.adjustment_status == AdjustmentStatus.MANUAL
