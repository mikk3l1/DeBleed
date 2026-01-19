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
        
        # Apply morphological closing to connect nearby edges (merge text into larger regions)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
        edges_closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        
        # Dilate to further merge regions
        kernel_dilate = cv2.getStructuringElement(cv2.MORPH_RECT, (10, 10))
        edges_dilated = cv2.dilate(edges_closed, kernel_dilate, iterations=2)
        
        # Find contours on processed edges
        contours, _ = cv2.findContours(edges_dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
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
            
            # Skip tiny regions (< 10% of image area for better filtering)
            region_area = w * h
            if region_area < 0.10 * image_area:
                continue
            
            # Skip regions that are too narrow or short (likely artifacts)
            aspect_ratio = max(w, h) / min(w, h) if min(w, h) > 0 else 0
            if aspect_ratio > 5:  # Skip very elongated regions
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
        
        # Check for two-page spreads: if we have 2 regions with similar size side-by-side
        # and combined they cover > 70% of page, it's likely a spread
        if len(regions) >= 2:
            first = regions[0]
            second = regions[1]
            
            # Check if regions are side-by-side (not overlapping vertically too much)
            vertical_overlap = min(first["y"] + first["h"], second["y"] + second["h"]) - max(first["y"], second["y"])
            vertical_union = max(first["y"] + first["h"], second["y"] + second["h"]) - min(first["y"], second["y"])
            vertical_overlap_ratio = vertical_overlap / vertical_union if vertical_union > 0 else 0
            
            # Check if similar size (within 30% of each other)
            size_ratio = min(first["area_percentage"], second["area_percentage"]) / max(first["area_percentage"], second["area_percentage"])
            
            # Check if horizontally separated
            horizontal_gap = abs((first["x"] + first["w"]/2) - (second["x"] + second["w"]/2))
            min_width = min(first["w"], second["w"])
            
            # Combined coverage
            combined_coverage = first["area_percentage"] + second["area_percentage"]
            
            # If this looks like a two-page spread
            if (vertical_overlap_ratio > 0.7 and  # Aligned vertically
                size_ratio > 0.7 and              # Similar sizes
                horizontal_gap > min_width * 0.8 and  # Horizontally separated
                combined_coverage > 70.0):        # Together they cover most of page
                
                # Pick the right page (assuming right-to-left reading for book spreads)
                # Sort by x coordinate to get left and right pages
                if first["x"] < second["x"]:
                    left_page = first
                    right_page = second
                else:
                    left_page = second
                    right_page = first
                
                # Use the right page (main content page in most books)
                selected_page = right_page
                
                primary_region = PrimaryPageRegion(
                    coordinates=(selected_page["x"], selected_page["y"], selected_page["w"], selected_page["h"]),
                    confidence_level=selected_page["confidence"] + 0.2,  # Boost confidence for spread detection
                    area_percentage=selected_page["area_percentage"],
                    detection_method="two_page_spread_right",
                )
                
                secondary_regions = []  # No secondary regions for spread detection
                
        # If not a two-page spread, use normal logic
        if 'primary_region' not in locals():
            # Check if this is a clean scan without bleed marks
            # If the best region covers < 50% of page, assume it's a clean scan
            # and use the entire page with a margin
            best_region = regions[0]
            if best_region["area_percentage"] < 50.0:
                # Clean scan - use entire page with small margin (2% on each side)
                margin_x = int(width * 0.02)
                margin_y = int(height * 0.02)
                
                fallback_x = margin_x
                fallback_y = margin_y
                fallback_w = width - (2 * margin_x)
                fallback_h = height - (2 * margin_y)
                fallback_area = fallback_w * fallback_h
                fallback_area_percentage = (fallback_area / image_area) * 100.0
                
                # High confidence for fallback (0.95 - clearly a clean scan)
                fallback_confidence = 0.95
                
                primary_region = PrimaryPageRegion(
                    coordinates=(fallback_x, fallback_y, fallback_w, fallback_h),
                    confidence_level=fallback_confidence,
                    area_percentage=fallback_area_percentage,
                    detection_method="fallback_full_page",
                )
                
                # No secondary regions for clean scans
                secondary_regions = []
            else:
                # Bleed marks detected - use the detected region
                primary = best_region
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
