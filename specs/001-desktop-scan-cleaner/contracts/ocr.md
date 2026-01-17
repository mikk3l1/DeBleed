# Contract: OCR Integration Stage

**Stage**: OCR Text Extraction  
**Purpose**: Extract text from detected page regions with confidence scoring  
**Constitutional Alignment**: Confidence-based flagging, Deterministic (given fixed config)

---

## Interface

### Input Schema

```python
@dataclass
class OCRInput:
    image: NDArray[np.uint8]  # Cropped region from LayoutDetectionOutput.primary_region
    page_number: int  # For logging
    language: str = "eng"  # Tesseract language code (eng, spa, fra, etc.)
    config: OCRConfig  # Tesseract parameters
```

**Validation**:
- `image.shape` must be (H, W, 3) RGB
- `language` must be valid Tesseract language code
- Image dimensions must be >= 100x100 pixels (too small for OCR)

---

### Output Schema

```python
@dataclass
class OCROutput:
    text_content: str  # Full extracted text
    text_blocks: list[TextBlock]  # Structural breakdown (paragraphs)
    overall_confidence: float  # Average confidence across all words (0.0-1.0)
    detected_language: str  # Tesseract's detected language (may differ from input)
    reading_order: list[int]  # Indices of text_blocks in reading order
    flagged_words: list[tuple[str, float]]  # Words with confidence < 0.75
    processing_time_ms: int  # Time for OCR execution
    warnings: list[str]  # Non-fatal issues (e.g., "No text detected")
```

**Guarantees**:
- `overall_confidence` is weighted average of word confidences
- `flagged_words` contains only words below OCR_confidence_threshold (0.75)
- `reading_order` uses left-to-right, top-to-bottom for English-like languages
- `text_blocks` always has >= 1 entry (even if empty text)

---

### Error Schema

```python
class OCRError(Exception):
    """Raised when OCR cannot complete"""
    
    error_code: str  # One of: TESSERACT_NOT_FOUND, LANGUAGE_NOT_AVAILABLE, INVALID_IMAGE, TIMEOUT
    page_number: int
    details: str
```

**Error Codes**:
- `TESSERACT_NOT_FOUND`: Tesseract executable not in PATH or bundled
- `LANGUAGE_NOT_AVAILABLE`: Requested language data not installed
- `INVALID_IMAGE`: Image too small or wrong format
- `TIMEOUT`: OCR exceeded max_ocr_time_per_page_s (2 seconds)

---

## Functional Requirements

### FR-OCR-001: Text Extraction
**Requirement**: Use Tesseract to extract all readable text from image  
**Input**: Cropped page region (RGB)  
**Output**: Plain text string  
**Success Criteria**: Extracted text matches visible text in image  
**Error Handling**: Return empty string if no text detected (not an error)

### FR-OCR-002: Confidence Scoring
**Requirement**: Calculate per-word confidence scores from Tesseract  
**Input**: Tesseract detailed output  
**Output**: List of (word, confidence) tuples  
**Success Criteria**: Confidence values in [0.0, 1.0] range  
**Error Handling**: N/A (Tesseract always provides confidence)

### FR-OCR-003: Low-Confidence Flagging
**Requirement**: Identify words with confidence < 0.75 for user review  
**Input**: Word confidence scores  
**Output**: flagged_words list  
**Success Criteria**: Flagged words appear in final text with [?] markers  
**Error Handling**: N/A (filtering always succeeds)

### FR-OCR-004: Text Block Extraction
**Requirement**: Segment text into logical paragraphs/regions  
**Input**: Tesseract block-level output  
**Output**: List of TextBlock entities with positions  
**Success Criteria**: Blocks correspond to visual paragraphs  
**Error Handling**: Single block if segmentation fails

### FR-OCR-005: Reading Order Determination
**Requirement**: Order text blocks for proper reading flow  
**Input**: TextBlock positions  
**Output**: reading_order list (indices)  
**Logic**:
```
For single-column: Top-to-bottom ordering
For multi-column: Left-to-right columns, then top-to-bottom within column
```
**Success Criteria**: Reading order matches natural reading flow  
**Error Handling**: Fall back to top-to-bottom if column detection ambiguous

### FR-OCR-006: Multi-Language Support
**Requirement**: Support common languages via Tesseract language packs  
**Input**: language parameter (e.g., "eng", "spa+eng" for multilingual)  
**Output**: Text extracted using specified language model  
**Success Criteria**: Language model bundled with application  
**Error Handling**: Raise `LANGUAGE_NOT_AVAILABLE` if language pack missing

### FR-OCR-007: Deterministic Output
**Requirement**: Same input image + config produces identical text  
**Input**: Identical OCRInput  
**Output**: Identical text_content and confidence scores  
**Success Criteria**: Tesseract configuration disables non-deterministic features  
**Error Handling**: N/A (determinism via config)

---

## Performance Requirements

### PERF-OCR-001: Processing Speed
**Limit**: < 2 seconds per page (from PerformanceConfig)  
**Measurement**: OCROutput.processing_time_ms  
**Mitigation**: Use Tesseract fast mode, limit image size

### PERF-OCR-002: Memory Usage
**Limit**: Tesseract process < 200MB per page  
**Measurement**: System memory monitoring  
**Mitigation**: Downsample very large images before OCR

---

## Testing Requirements

### Unit Tests

1. **test_simple_text_extraction**: Clean printed page, verify text matches expected
2. **test_low_quality_scan**: Blurry image, verify low confidence scores
3. **test_confidence_flagging**: Mixed quality text, verify words below 0.75 flagged
4. **test_empty_page**: Blank image, verify empty text_content (no error)
5. **test_multi_column_layout**: Two-column page, verify reading order correct
6. **test_language_detection**: Spanish text, verify detected_language = "spa"
7. **test_deterministic_ocr**: Run twice on same image, verify identical output
8. **test_missing_language**: Request unavailable language, expect LANGUAGE_NOT_AVAILABLE
9. **test_timeout**: Artificially large image, expect TIMEOUT error

### Integration Tests

1. **test_ocr_after_layout**: Full pipeline from PDF → preprocessing → layout → OCR
2. **test_batch_ocr**: Process 100 pages, verify memory doesn't grow unbounded

### Contract Tests

1. **test_output_schema_compliance**: Every successful run produces valid OCROutput
2. **test_confidence_range**: All confidence values in [0.0, 1.0]
3. **test_flagged_words_threshold**: All flagged words have confidence < 0.75

---

## Dependencies

**Required Libraries**:
- `pytesseract`: Python wrapper for Tesseract
- `tesseract-ocr`: Tesseract executable (bundled via PyInstaller)
- `numpy`: Array operations

**Language Data**:
- `eng.traineddata`: English (required)
- `spa.traineddata`: Spanish (optional)
- `fra.traineddata`: French (optional)

**Depends On**:
- Layout Detection stage (uses primary_region to crop image)
- Preprocessing stage (indirectly, via layout)

**No Dependencies On**:
- Export stage (OCR runs before export)
- GUI components

---

## Configuration

```python
@dataclass
class OCRConfig:
    confidence_threshold: float = 0.75  # Flag words below this
    tesseract_psm: int = 3  # Page segmentation mode (3 = fully automatic)
    tesseract_oem: int = 3  # OCR engine mode (3 = default, LSTM + legacy)
    language: str = "eng"  # Primary language
    enable_column_detection: bool = True  # Detect multi-column layouts
    timeout_seconds: int = 2  # From PerformanceConfig.max_ocr_time_per_page_s
```

**Tesseract PSM Modes**:
- `3`: Fully automatic page segmentation (default)
- `6`: Assume uniform block of text
- `11`: Sparse text (find as much text as possible)

**Tesseract OEM Modes**:
- `3`: Default (LSTM + legacy engines)
- `1`: LSTM only (faster, requires eng.traineddata)
- `0`: Legacy only (slower, better for low-DPI)

---

## Algorithm Specification

### Text Block Segmentation

**Steps**:
1. Run Tesseract with `output_type=pytesseract.Output.DICT`
2. Extract block-level data: `blocks = data['block_num']`
3. Group words by block number into TextBlock entities
4. Calculate per-block bounding boxes from word positions
5. Sort blocks by reading order (see FR-OCR-005)

### Reading Order Algorithm

```python
def determine_reading_order(text_blocks: list[TextBlock]) -> list[int]:
    """Sort blocks by reading flow (top-left to bottom-right)"""
    if is_multi_column(text_blocks):
        # Group into columns by x-coordinate
        columns = group_into_columns(text_blocks)
        # Sort columns left-to-right
        columns.sort(key=lambda col: min(b.position[0] for b in col))
        # Within each column, sort top-to-bottom
        ordered = []
        for col in columns:
            col.sort(key=lambda b: b.position[1])
            ordered.extend(col)
        return [text_blocks.index(b) for b in ordered]
    else:
        # Simple top-to-bottom
        sorted_blocks = sorted(text_blocks, key=lambda b: b.position[1])
        return [text_blocks.index(b) for b in sorted_blocks]

def is_multi_column(blocks: list[TextBlock]) -> bool:
    """Heuristic: If blocks cluster into 2+ vertical groups"""
    x_positions = [b.position[0] for b in blocks]
    # Use simple gap detection: if large gap exists, assume columns
    sorted_x = sorted(x_positions)
    gaps = [sorted_x[i+1] - sorted_x[i] for i in range(len(sorted_x)-1)]
    max_gap = max(gaps) if gaps else 0
    avg_gap = sum(gaps) / len(gaps) if gaps else 0
    return max_gap > 3 * avg_gap  # Large gap indicates column boundary
```

### Confidence Aggregation

```python
def calculate_overall_confidence(word_confidences: list[float]) -> float:
    """Weighted average (longer words count more)"""
    if not word_confidences:
        return 0.0
    # Simple average for now (could weight by word length)
    return sum(word_confidences) / len(word_confidences)
```

---

## Example Usage

```python
from ocr_integration import extract_text, OCRInput, OCRConfig
from layout_detection import detect_layout

# Detect layout first
layout_output = detect_layout(layout_input)
primary_region = layout_output.primary_region

# Crop image to primary region
x, y, w, h = primary_region.coordinates
cropped_image = original_image[y:y+h, x:x+w]

# Extract text
ocr_config = OCRConfig(
    confidence_threshold=0.75,
    language="eng",
    tesseract_psm=3
)

ocr_input = OCRInput(
    image=cropped_image,
    page_number=1,
    language="eng",
    config=ocr_config
)

try:
    ocr_output = extract_text(ocr_input)
    
    print(f"Extracted {len(ocr_output.text_content.split())} words")
    print(f"Overall confidence: {ocr_output.overall_confidence:.2f}")
    
    if ocr_output.flagged_words:
        print(f"⚠ {len(ocr_output.flagged_words)} low-confidence words flagged")
        for word, conf in ocr_output.flagged_words[:5]:  # Show first 5
            print(f"  - '{word}' ({conf:.2f})")
    
    # Export with [?] markers
    plain_text_with_flags = ocr_output.plain_text  # Uses derived property
    
except OCRError as e:
    print(f"OCR failed: {e.error_code} - {e.details}")
```

---

## Bundling Tesseract

**PyInstaller Configuration**:
```python
# In spec file for PyInstaller
datas = [
    ('path/to/tesseract.exe', 'tesseract'),
    ('path/to/tessdata/', 'tessdata')  # Language data
]
```

**Runtime Detection**:
```python
def get_tesseract_path() -> str:
    """Find Tesseract executable (bundled or system)"""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle
        base_path = sys._MEIPASS
        return os.path.join(base_path, 'tesseract', 'tesseract.exe')
    else:
        # Development mode, use system Tesseract
        return 'tesseract'  # Assumes in PATH
```

---

## Traceability

**Implements Functional Requirements**:
- FR-021 (perform OCR on detected pages) - core functionality
- FR-022 (extract text for accessibility) - text_content output
- FR-023 (embed text layer in PDF) - provides text for PDF export
- FR-024 (flag low-confidence text) - flagged_words mechanism
- FR-025 (provide plain text export option) - text_content usable directly
- FR-026 (mark uncertain text with [?]) - plain_text derived property
- FR-027 (maintain reading order) - reading_order calculation
- FR-028 (support English) - eng.traineddata bundled
- FR-029 (deterministic OCR) - fixed Tesseract config
- FR-030 (OCR timeout) - max_ocr_time_per_page_s limit

**Supports Constitution Principles**:
- **Explainability**: Confidence scores expose uncertainty
- **Determinism**: Tesseract config avoids non-deterministic modes
- **Explicit Failure Handling**: Typed error codes
- **Performance & Scalability**: Timeout limits, memory monitoring

**Referenced By**:
- [Export Contract](export.md) - uses OCROutput for PDF text layer
- [data-model.md](../data-model.md) - OCRResult matches output schema
