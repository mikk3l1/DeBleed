# Contract: Preprocessing Stage

**Stage**: Image Preprocessing  
**Purpose**: Convert PDF pages to normalized images ready for layout detection  
**Constitutional Alignment**: Deterministic (pixel-exact), Modular (independent stage)

---

## Interface

### Input Schema

```python
@dataclass
class PreprocessingInput:
    pdf_path: Path  # Absolute path to source PDF
    page_number: int  # 1-based page index
    target_dpi: int = 300  # Rendering resolution
```

**Validation**:
- `pdf_path` must exist and be readable
- `page_number` must be >= 1 and <= document page count
- `target_dpi` must be in range [150, 600] (performance constraint)

---

### Output Schema

```python
@dataclass
class PreprocessingOutput:
    image_data: NDArray[np.uint8]  # Shape: (H, W, 3) RGB uint8
    dimensions: tuple[int, int]  # (width, height) in pixels
    actual_dpi: int  # Actual DPI used (may differ if page is already high-res)
    processing_time_ms: int  # Time taken for this stage
    warnings: list[str]  # Non-fatal issues (e.g., "Page already rotated")
```

**Guarantees**:
- `image_data` is always RGB (3 channels), never grayscale or RGBA
- `image_data.dtype == np.uint8` (values in [0, 255])
- `dimensions == (image_data.shape[1], image_data.shape[0])` (width, height)
- `processing_time_ms` includes PDF rendering + color normalization

---

### Error Schema

```python
class PreprocessingError(Exception):
    """Raised when preprocessing cannot complete"""
    
    error_code: str  # One of: PDF_UNREADABLE, PAGE_OUT_OF_RANGE, RENDER_FAILED, MEMORY_EXCEEDED
    page_number: int
    details: str
```

**Error Codes**:
- `PDF_UNREADABLE`: File not found, corrupted, or encrypted
- `PAGE_OUT_OF_RANGE`: page_number exceeds document page count
- `RENDER_FAILED`: PyMuPDF raised exception during rendering
- `MEMORY_EXCEEDED`: Image would exceed memory threshold (from PerformanceConfig)

---

## Functional Requirements

### FR-PP-001: PDF Rendering
**Requirement**: Convert PDF page to raster image using PyMuPDF  
**Input**: PreprocessingInput  
**Output**: Raw RGB image at specified DPI  
**Success Criteria**: Image contains full page content without cropping  
**Error Handling**: Raise `PreprocessingError(RENDER_FAILED)` if PyMuPDF fails

### FR-PP-002: Color Normalization
**Requirement**: Ensure image is RGB (convert grayscale/RGBA if needed)  
**Input**: Raw rendered image  
**Output**: 3-channel RGB uint8 array  
**Success Criteria**: Output always has shape (H, W, 3)  
**Error Handling**: N/A (conversion always succeeds)

### FR-PP-003: DPI Adjustment
**Requirement**: Respect target_dpi but avoid upscaling if page already high-res  
**Input**: target_dpi, page metadata  
**Output**: Rendered image at appropriate DPI  
**Success Criteria**: actual_dpi >= target_dpi OR actual_dpi == original_page_dpi  
**Error Handling**: Warn if downscaling from very high DPI (>600)

### FR-PP-004: Deterministic Output
**Requirement**: Same input always produces pixel-identical output  
**Input**: Identical PreprocessingInput  
**Output**: Byte-for-byte identical PreprocessingOutput.image_data  
**Success Criteria**: np.array_equal() returns True for repeated runs  
**Error Handling**: N/A (determinism is enforced by avoiding randomness)

---

## Performance Requirements

### PERF-PP-001: Rendering Speed
**Limit**: < 200ms per page for typical documents (DPI=300, A4 size)  
**Measurement**: PreprocessingOutput.processing_time_ms  
**Mitigation**: Use PyMuPDF's native rendering (C++ backend)

### PERF-PP-002: Memory Usage
**Limit**: Single page must not exceed 100MB in memory  
**Calculation**: (width * height * 3 bytes) < 100MB  
**Mitigation**: Reject excessively large pages or reduce DPI

---

## Testing Requirements

### Unit Tests

1. **test_render_simple_pdf**: Verify basic PDF page renders to RGB image
2. **test_grayscale_conversion**: Input grayscale PDF, verify RGB output
3. **test_rgba_conversion**: Input PDF with transparency, verify opaque RGB output
4. **test_dpi_respected**: Request 300 DPI, verify dimensions match expected size
5. **test_deterministic_rendering**: Render same page twice, verify pixel equality
6. **test_invalid_page_number**: Request page 999 from 10-page PDF, expect PAGE_OUT_OF_RANGE
7. **test_corrupted_pdf**: Input unreadable file, expect PDF_UNREADABLE error
8. **test_memory_limit**: Attempt to render extremely large page, expect MEMORY_EXCEEDED

### Integration Tests

1. **test_preprocessing_to_layout_pipeline**: Verify PreprocessingOutput feeds cleanly into layout detection
2. **test_batch_preprocessing**: Process 100 pages, verify no memory leaks

### Contract Tests

1. **test_output_schema_compliance**: Every successful run produces valid PreprocessingOutput
2. **test_error_schema_compliance**: Every failure raises PreprocessingError with valid error_code

---

## Dependencies

**Required Libraries**:
- `pymupdf (fitz)`: PDF rendering
- `numpy`: Array operations
- `pillow`: Format conversions (if needed)

**No Dependencies On**:
- Layout detection stage (unidirectional flow)
- OCR stage
- GUI components

---

## Configuration

```python
@dataclass
class PreprocessingConfig:
    default_dpi: int = 300  # Used if not specified in input
    max_page_dimension: int = 10000  # Reject pages wider/taller than this
    memory_limit_mb: int = 100  # Per-page memory threshold
    color_space: str = "RGB"  # Always RGB for consistency
```

---

## Example Usage

```python
from pathlib import Path
from preprocessing import preprocess_page, PreprocessingInput

# Basic usage
input_data = PreprocessingInput(
    pdf_path=Path("/path/to/scanned.pdf"),
    page_number=1,
    target_dpi=300
)

try:
    output = preprocess_page(input_data)
    print(f"Rendered page: {output.dimensions[0]}x{output.dimensions[1]} px")
    print(f"Processing time: {output.processing_time_ms}ms")
    
    # Pass to next stage
    layout_input = LayoutDetectionInput(image=output.image_data, ...)
    
except PreprocessingError as e:
    print(f"Preprocessing failed: {e.error_code} - {e.details}")
```

---

## Traceability

**Implements Functional Requirements**:
- FR-001 (load and display PDF pages) - provides page rendering
- FR-005 (batch processing setup) - supports multi-page iteration
- FR-009 (deterministic behavior) - guarantees reproducible output

**Supports Constitution Principles**:
- **Correctness & Determinism**: Pixel-exact reproducibility (FR-PP-004)
- **Modular Architecture**: No dependencies on downstream stages
- **Explicit Failure Handling**: All errors have typed error codes
- **Performance & Scalability**: Memory limits and time tracking

**Referenced By**:
- [Layout Detection Contract](layout.md) - consumes PreprocessingOutput
- [data-model.md](../data-model.md) - Page.image_data matches output schema
