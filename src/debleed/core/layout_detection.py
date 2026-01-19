"""Layout detection pipeline stage - extract page boundaries from images."""

from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np
from numpy.typing import NDArray

from debleed.config.detection_config import DetectionConfig
from debleed.core.exceptions import LayoutDetectionError
from debleed.models.page import DetectedBoundary, PrimaryPageRegion


@dataclass
class LayoutDetectionInput:
    """Input for layout detection stage.
    
    Attributes:
        image_data: RGB image as numpy array (H, W, 3) with dtype uint8
        page_number: 1-indexed page number being processed
        config: Detection configuration (thresholds, algorithm parameters)
    """
    
    image_data: NDArray[np.uint8]
    page_number: int
    config: DetectionConfig = field(default_factory=DetectionConfig)
    
    def __post_init__(self) -> None:
        """Validate layout detection input."""
        if self.image_data.ndim != 3:
            raise ValueError(f"image_data must be 3D array (H,W,C), got shape {self.image_data.shape}")
        if self.image_data.dtype != np.uint8:
            raise ValueError(f"image_data must be uint8, got {self.image_data.dtype}")
        if self.page_number < 1:
            raise ValueError(f"page_number must be >= 1, got {self.page_number}")


@dataclass
class LayoutDetectionOutput:
    """Output from layout detection stage.
    
    Attributes:
        detected_boundary: Primary and secondary page regions
        rotation_angle: Detected rotation in degrees (0, 90, 180, 270)
        debug_info: Optional debug data (edge maps, contours) if enabled
    """
    
    detected_boundary: DetectedBoundary
    rotation_angle: int = 0
    debug_info: Optional[dict[str, NDArray]] = None
    
    def __post_init__(self) -> None:
        """Validate layout detection output."""
        if self.rotation_angle not in (0, 90, 180, 270):
            raise ValueError(f"rotation_angle must be 0/90/180/270, got {self.rotation_angle}")


def detect_layout(input_data: LayoutDetectionInput) -> LayoutDetectionOutput:
    """Detect page boundaries in scanned document image.
    
    Detection pipeline:
    1. Convert to grayscale for edge detection
    2. Apply Canny edge detection with fixed thresholds (50, 150)
    3. Extract contours using OpenCV findContours()
    4. Rank regions by composite score (area + rectangularity + edge strength)
    5. Calculate confidence score (0.5*area + 0.3*rectangularity + 0.2*edge_strength)
    6. Detect rotation (if enabled) for 90°/180°/270° auto-correction
    
    Args:
        input_data: Image and configuration for detection
        
    Returns:
        LayoutDetectionOutput with primary/secondary regions and metadata
        
    Raises:
        LayoutDetectionError: If image is invalid, no regions found, or timeout exceeded
    """
    try:
        # Validate image
        if input_data.image_data.size == 0:
            raise LayoutDetectionError(
                message="Image is empty or corrupted",
                error_code="INVALID_IMAGE",
                page_number=input_data.page_number,
            )
        
        height, width = input_data.image_data.shape[:2]
        image_area = height * width
        
        # Convert to grayscale for edge detection
        gray = cv2.cvtColor(input_data.image_data, cv2.COLOR_RGB2GRAY)
        
        # Apply Canny edge detection with deterministic thresholds
        edges = cv2.Canny(
            gray,
            input_data.config.canny_threshold_low,
            input_data.config.canny_threshold_high,
        )
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            raise LayoutDetectionError(
                message=f"No page boundaries detected on page {input_data.page_number}",
                error_code="NO_REGIONS_FOUND",
                page_number=input_data.page_number,
                details={"edge_pixels": int(np.sum(edges > 0))},
            )
        
        # Rank regions by composite score
        regions = []
        for contour in contours:
            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)
            
            # Skip tiny regions (< 5% of image)
            region_area = w * h
            if region_area < 0.05 * image_area:
                continue
            
            # Calculate area percentage (0.0-100.0 for storage, 0.0-1.0 for confidence calc)
            area_fraction = region_area / image_area
            area_percentage = area_fraction * 100.0
            
            # Calculate rectangularity (how closely contour fits bounding box)
            contour_area = cv2.contourArea(contour)
            rectangularity = contour_area / region_area if region_area > 0 else 0.0
            
            # Calculate edge strength (average edge intensity in region)
            roi_edges = edges[y:y+h, x:x+w]
            edge_strength = float(np.mean(roi_edges)) / 255.0
            
            # Composite confidence score (using area_fraction 0.0-1.0)
            confidence = (
                0.5 * min(area_fraction, 1.0) +
                0.3 * rectangularity +
                0.2 * edge_strength
            )
            
            regions.append({
                "x": x,
                "y": y,
                "w": w,
                "h": h,
                "area_percentage": area_percentage,
                "rectangularity": rectangularity,
                "edge_strength": edge_strength,
                "confidence": confidence,
            })
        
        if not regions:
            raise LayoutDetectionError(
                message=f"No significant page regions found on page {input_data.page_number}",
                error_code="NO_REGIONS_FOUND",
                page_number=input_data.page_number,
                details={"total_contours": len(contours)},
            )
        
        # Sort by confidence (descending)
        regions.sort(key=lambda r: r["confidence"], reverse=True)
        
        # Primary region (highest confidence)
        primary = regions[0]
        primary_region = PrimaryPageRegion(
            coordinates=(primary["x"], primary["y"], primary["w"], primary["h"]),
            confidence_level=primary["confidence"],
            area_percentage=primary["area_percentage"],
            detection_method="canny_edge",
        )
        
        # Secondary regions (remaining regions with confidence > 0.3)
        secondary_regions = [
            PrimaryPageRegion(
                coordinates=(r["x"], r["y"], r["w"], r["h"]),
                confidence_level=r["confidence"],
                area_percentage=r["area_percentage"],
                detection_method="canny_edge",
            )
            for r in regions[1:] if r["confidence"] > 0.3
        ]
        
        # Create detected boundary
        detected_boundary = DetectedBoundary(
            primary_region=primary_region,
            secondary_regions=secondary_regions,
            detection_config={
                "algorithm": "canny_edge",
                "canny_low": input_data.config.canny_threshold_low,
                "canny_high": input_data.config.canny_threshold_high,
                "total_regions_found": len(regions),
            },
        )
        
        # Detect rotation (placeholder - simplified for MVP)
        rotation_angle = 0
        if input_data.config.enable_rotation_detection:
            # TODO: Implement rotation detection in future iteration
            # For now, assume no rotation
            rotation_angle = 0
        
        # Generate debug info if enabled
        debug_info = None
        if input_data.config.enable_debug_output:
            # Draw bounding boxes on original image
            debug_image = input_data.image_data.copy()
            
            # Unpack primary region coordinates
            primary_x, primary_y, primary_w, primary_h = primary_region.coordinates
            cv2.rectangle(
                debug_image,
                (primary_x, primary_y),
                (primary_x + primary_w, primary_y + primary_h),
                (0, 255, 0),  # Green for primary
                2,
            )
            
            # Draw secondary regions
            for sec_region in secondary_regions:
                sec_x, sec_y, sec_w, sec_h = sec_region.coordinates
                cv2.rectangle(
                    debug_image,
                    (sec_x, sec_y),
                    (sec_x + sec_w, sec_y + sec_h),
                    (255, 0, 0),  # Red for secondary
                    1,
                )
            
            debug_info = {
                "edge_map": edges,
                "annotated_image": debug_image,
            }
        
        return LayoutDetectionOutput(
            detected_boundary=detected_boundary,
            rotation_angle=rotation_angle,
            debug_info=debug_info,
        )
        
    except LayoutDetectionError:
        raise
    except MemoryError as e:
        raise LayoutDetectionError(
            message=f"Insufficient memory to process page {input_data.page_number}",
            error_code="MEMORY_EXCEEDED",
            page_number=input_data.page_number,
            details={"error": str(e)},
        )
    except Exception as e:
        raise LayoutDetectionError(
            message=f"Unexpected error during layout detection: {str(e)}",
            error_code="INVALID_IMAGE",
            page_number=input_data.page_number,
            details={"error": str(e)},
        )
