# Contract: Layout Detection Stage

**Stage**: Layout Detection  
**Purpose**: Identify primary page boundaries within scanned images  
**Constitutional Alignment**: Geometric (explainable), Layout-First (per constitution)

---

## Interface

### Input Schema

```python
@dataclass
class LayoutDetectionInput:
    image: NDArray[np.uint8]  # Shape: (H, W, 3) RGB from preprocessing
    page_number: int  # For logging/error messages
    config: DetectionConfig  # Thresholds and parameters
```

**Validation**:
- `image.shape` must be (H, W, 3)
- `image.dtype == np.uint8`
- `page_number >= 1`

---

### Output Schema

```python
@dataclass
class LayoutDetectionOutput:
    primary_region: PrimaryPageRegion  # Best candidate boundary
    secondary_regions: list[PrimaryPageRegion]  # Up to max_secondary_regions alternatives
    confidence_score: float  # Overall confidence (0.0-1.0)
    detection_method: str  # "contour_analysis" or "connected_components"
    processing_time_ms: int  # Time for detection
    debug_info: dict  # Intermediate steps for visualization (optional)
```

**Guarantees**:
- `primary_region` always exists (even if low confidence)
- `confidence_score` accurately reflects geometric consistency
- `confidence_score >= 0.80` implies production-ready detection
- `secondary_regions` ordered by descending confidence
- `debug_info` includes: edge_map, contours, bounding_boxes (if requested)

---

### Error Schema

```python
class LayoutDetectionError(Exception):
    """Raised when layout detection cannot complete"""
    
    error_code: str  # One of: INVALID_IMAGE, NO_REGIONS_FOUND, TIMEOUT, MEMORY_EXCEEDED
    page_number: int
    details: str
```

**Error Codes**:
- `INVALID_IMAGE`: Image format doesn't match expectations
- `NO_REGIONS_FOUND`: Image is blank or unprocessable
- `TIMEOUT`: Detection exceeded max_page_detection_time_ms
- `MEMORY_EXCEEDED`: Intermediate structures too large

---

## Functional Requirements

### FR-LD-001: Edge Detection
**Requirement**: Detect edges using Canny algorithm with deterministic thresholds  
**Input**: RGB image  
**Output**: Binary edge map  
**Success Criteria**: Edges represent clear boundaries between paper and background  
**Error Handling**: N/A (Canny always produces output)

### FR-LD-002: Contour Extraction
**Requirement**: Identify closed contours representing potential page boundaries  
**Input**: Edge map  
**Output**: List of contours with (x, y, w, h) bounding rectangles  
**Success Criteria**: Largest contour corresponds to primary page  
**Error Handling**: Raise `NO_REGIONS_FOUND` if no contours detected

### FR-LD-003: Region Ranking
**Requirement**: Score candidate regions by area, rectangularity, and position  
**Input**: List of candidate regions  
**Output**: Sorted list with highest confidence first  
**Success Criteria**: Primary region is largest contour with area > 10% of image  
**Error Handling**: N/A (ranking always produces ordered list)

### FR-LD-004: Confidence Calculation
**Requirement**: Calculate confidence based on geometric properties  
**Input**: Primary region bounding box  
**Output**: Float in [0.0, 1.0]  
**Formula**:
```
confidence = (
    0.5 * (region_area / total_image_area) +  # Larger is better
    0.3 * rectangularity_score +              # How rectangular the contour is
    0.2 * edge_strength_score                 # How sharp the boundaries are
)
```
**Success Criteria**: Confidence >= 0.80 for well-scanned pages  
**Error Handling**: N/A (always computes valid float)

### FR-LD-005: Rotation Detection
**Requirement**: Detect if page is rotated 90°, 180°, or 270° and auto-correct  
**Input**: Primary region contour  
**Output**: rotation_angle (0, 90, 180, 270) + corrected image  
**Success Criteria**: Text orientation corrected for standard reading  
**Error Handling**: Warn if rotation not in {0, 90, 180, 270} (flag for manual review)

### FR-LD-006: Deterministic Detection
**Requirement**: Same input always produces identical output regions  
**Input**: Identical LayoutDetectionInput  
**Output**: Identical coordinates and confidence  
**Success Criteria**: No randomness in algorithm (no ML, no sampling)  
**Error Handling**: N/A (determinism enforced by algorithm design)

---

## Performance Requirements

### PERF-LD-001: Detection Speed
**Limit**: < 500ms per page (from PerformanceConfig)  
**Measurement**: LayoutDetectionOutput.processing_time_ms  
**Mitigation**: Use optimized OpenCV functions, avoid Python loops

### PERF-LD-002: Memory Efficiency
**Limit**: Intermediate edge maps and contours < 50MB total  
**Measurement**: Sum of all NumPy array sizes in debug_info  
**Mitigation**: Downsample very large images before edge detection

---

## Testing Requirements

### Unit Tests

1. **test_simple_scan_detection**: Single page on white background, verify high confidence
2. **test_multi_page_scan**: Two pages on scanner bed, verify primary picks largest
3. **test_low_confidence_flagging**: Blurry scan, verify confidence < 0.80
4. **test_rotation_90_degrees**: Rotated scan, verify auto-correction
5. **test_rotation_45_degrees**: Non-standard rotation, verify flagged for review
6. **test_deterministic_detection**: Run twice, verify identical coordinates
7. **test_no_edges_image**: Blank white image, expect NO_REGIONS_FOUND
8. **test_timeout_exceeded**: Artificially slow processing, expect TIMEOUT error

### Integration Tests

1. **test_layout_to_ocr_pipeline**: Verify LayoutDetectionOutput.primary_region feeds cleanly to OCR
2. **test_batch_layout_detection**: Process 100 pages, verify consistent confidence scores

### Contract Tests

1. **test_output_schema_compliance**: Every successful run produces valid LayoutDetectionOutput
2. **test_confidence_range**: Verify confidence always in [0.0, 1.0]
3. **test_coordinates_within_bounds**: primary_region coordinates never exceed image dimensions

---

## Dependencies

**Required Libraries**:
- `opencv-python`: Edge detection, contour finding
- `numpy`: Array operations
- `scikit-image` (optional): Alternative edge detection algorithms

**Depends On**:
- Preprocessing stage (consumes PreprocessingOutput.image_data)

**No Dependencies On**:
- OCR stage
- Export stage
- GUI components

---

## Configuration

```python
@dataclass
class DetectionConfig:
    page_confidence_threshold: float = 0.80  # Flag if below this
    canny_low_threshold: int = 50  # Canny edge detection low threshold
    canny_high_threshold: int = 150  # Canny edge detection high threshold
    min_region_area_percentage: float = 10.0  # Reject regions smaller than this
    max_secondary_regions: int = 5  # How many alternatives to track
    rotation_auto_correct_angles: list[int] = field(default_factory=lambda: [90, 180, 270])
    enable_debug_info: bool = False  # Include intermediate steps in output
```

---

## Algorithm Specification

### Contour Analysis Method

**Steps**:
1. Convert RGB to grayscale: `gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)`
2. Apply Gaussian blur: `blurred = cv2.GaussianBlur(gray, (5, 5), 0)` (deterministic kernel)
3. Detect edges: `edges = cv2.Canny(blurred, canny_low, canny_high)`
4. Find contours: `contours = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)`
5. Filter contours by area: `valid = [c for c in contours if cv2.contourArea(c) > min_area]`
6. Compute bounding rectangles: `rects = [cv2.boundingRect(c) for c in valid]`
7. Rank by area: `primary = max(rects, key=lambda r: r[2] * r[3])`
8. Calculate confidence using formula in FR-LD-004

**Determinism Notes**:
- Gaussian kernel size is fixed (5x5)
- No random sampling in contour detection
- Thresholds are configurable but fixed per run

### Rectangularity Score

```python
def rectangularity_score(contour: NDArray) -> float:
    """How close is contour to a perfect rectangle?"""
    area = cv2.contourArea(contour)
    x, y, w, h = cv2.boundingRect(contour)
    bounding_area = w * h
    return area / bounding_area  # 1.0 = perfect rectangle
```

### Edge Strength Score

```python
def edge_strength_score(edges: NDArray, region: tuple) -> float:
    """How strong are edges around region perimeter?"""
    x, y, w, h = region
    perimeter_mask = create_perimeter_mask(x, y, w, h)  # 10-pixel border
    edge_pixels_in_perimeter = np.sum(edges[perimeter_mask] > 0)
    total_perimeter_pixels = np.sum(perimeter_mask)
    return edge_pixels_in_perimeter / total_perimeter_pixels
```

---

## Example Usage

```python
from layout_detection import detect_layout, LayoutDetectionInput
from preprocessing import preprocess_page

# Preprocess first
preprocessed = preprocess_page(PreprocessingInput(...))

# Detect layout
config = DetectionConfig(
    page_confidence_threshold=0.80,
    enable_debug_info=True  # For visualization
)

input_data = LayoutDetectionInput(
    image=preprocessed.image_data,
    page_number=1,
    config=config
)

try:
    output = detect_layout(input_data)
    
    if output.confidence_score >= 0.80:
        print(f"✓ Confident detection: {output.primary_region.coordinates}")
    else:
        print(f"⚠ Low confidence ({output.confidence_score:.2f}) - flag for review")
    
    # Visualize if needed
    if config.enable_debug_info:
        show_edge_map(output.debug_info['edge_map'])
    
except LayoutDetectionError as e:
    print(f"Layout detection failed: {e.error_code} - {e.details}")
```

---

## Traceability

**Implements Functional Requirements**:
- FR-002 (automatic boundary detection) - primary functionality
- FR-003 (manual boundary adjustment) - provides initial guess for adjustment
- FR-009 (deterministic behavior) - geometric algorithms only
- FR-013 (flag low-confidence pages) - confidence_score mechanism
- FR-015 (handle rotation) - auto-correct standard angles

**Supports Constitution Principles**:
- **Layout-First Processing**: This stage executes before OCR
- **Explainability**: Geometric algorithms with visible intermediate steps
- **Determinism**: No randomness, reproducible coordinates
- **Modular Architecture**: Clear input/output contracts

**Referenced By**:
- [OCR Contract](ocr.md) - uses primary_region to crop image before text extraction
- [data-model.md](../data-model.md) - DetectedBoundary matches output schema
