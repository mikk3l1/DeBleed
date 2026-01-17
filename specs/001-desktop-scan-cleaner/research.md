# Research: Desktop Scan Cleaner Application with OCR

**Feature**: 001-desktop-scan-cleaner  
**Date**: 2026-01-17  
**Status**: Complete

## Research Questions from Technical Context

All technical context fields were specified without "NEEDS CLARIFICATION" markers. The provided architecture details (Python, modular pipeline, deterministic processing, self-contained packaging) fully define the technical approach. This research document consolidates best practices and technology choices to support implementation.

## Technology Stack Research

### 1. Python Version & Distribution

**Decision**: Python 3.11+

**Rationale**: 
- Type hints improvements for better contract documentation (Constitution requirement)
- Performance improvements over 3.10 (15-60% faster for specific workloads)
- Stable release with good library compatibility
- Pattern matching syntax useful for pipeline state handling

**Packaging Strategy**: PyInstaller or cx_Freeze for standalone executables

- **PyInstaller**: Mature, cross-platform, handles Qt dependencies well
- **cx_Freeze**: Alternative with similar capabilities
- Both support bundling Python interpreter + dependencies into single executable
- Eliminates Python installation requirement for end users (Constraint: self-contained packaging)

### 2. Image Processing Library

**Decision**: OpenCV (opencv-python) + Pillow

**Rationale**:
- **OpenCV**: Industry standard for geometric image analysis, contour detection, connected components
- **Deterministic**: No random initialization; operations are reproducible (Principle I)
- **Explainable**: Geometric operations (thresholds, contours, transforms) are mathematically defined (Principle II)
- **Pillow**: Excellent for basic image operations, PDF page rendering via PIL
- **NumPy**: Underlying array operations for both libraries

**Alternatives Considered**:
- scikit-image: More Pythonic API but slower than OpenCV for some operations
- Rejection reason: OpenCV has better performance for real-time preview updates (FR-011, SC-005)

### 3. OCR Engine

**Decision**: Tesseract OCR via pytesseract wrapper

**Rationale**:
- **Open source**: Apache 2.0 license, no licensing costs
- **Bundling**: Can be included in standalone distribution
- **Multi-language support**: English + Spanish, French, German (Assumption section)
- **Confidence scores**: Provides character-level confidence for flagging uncertain text (FR-026)
- **Explainable**: Traditional OCR (not pure neural network black box) aligns with Principle II
- **Cross-platform**: Runs on Windows, macOS, Linux

**Integration Notes**:
- pytesseract provides Python wrapper for Tesseract binary
- Tesseract binary must be bundled with application or installed separately
- For P1: Bundle Tesseract with English language data; additional languages in future releases

**Alternatives Considered**:
- EasyOCR: Neural network-based, higher accuracy but less explainable
- Rejection reason: Violates Principle II (explainability over ML)
- OCRmyPDF: Higher-level tool but less control over pipeline
- Rejection reason: Need fine-grained control for confidence thresholding and region-specific OCR

### 4. PDF Manipulation Library

**Decision**: PyMuPDF (fitz) for rendering; reportlab or PyPDF2 for generation

**Rationale**:
- **PyMuPDF (fitz)**: Fast PDF rendering to images for preview (FR-008, FR-009)
  - Excellent performance for page-by-page rendering (SC-001: <5s for 100 pages)
  - Incremental loading supports large documents without memory issues (Principle VII)
  - Cross-platform, actively maintained
- **reportlab** or **PyPDF2**: PDF generation with embedded text layers (FR-022)
  - reportlab: Create PDFs from scratch with precise text layer positioning
  - PyPDF2: Merge/manipulate existing PDFs
  - Choose based on Phase 1 design (may need both)

**Alternatives Considered**:
- pdfplumber: Good for text extraction but not needed (we use Tesseract)
- PDFMiner: Text extraction focus, not suitable for rendering/generation

### 5. GUI Framework

**Decision**: PySide6 (Qt for Python)

**Rationale**:
- **Cross-platform**: Single codebase for Windows, macOS, Linux (Constraint: platform compatibility)
- **Rich widgets**: Thumbnail grids, preview panels, drag-drop support (FR-002, FR-008)
- **Performance**: Fast rendering for real-time boundary adjustment (FR-011, SC-005)
- **Mature**: Battle-tested for desktop applications
- **LGPL license**: Can be used in commercial/closed-source applications with dynamic linking

**Architecture Pattern**: Model-View separation
- Qt widgets in `ui/` layer (thin wrapper)
- Core pipeline in `pipeline/` (no Qt dependencies)
- Enables testing core logic without GUI (Principle V)

**Alternatives Considered**:
- Tkinter: Built-in but less feature-rich, harder to create modern UI
- PyQt6: Same as PySide6 but GPL license may be restrictive
- wxPython: Cross-platform but less polished than Qt

### 6. Testing Strategy

**Decision**: pytest + pytest-qt + pytest-cov

**Rationale**:
- **pytest**: De facto standard for Python testing, excellent fixture support
- **pytest-qt**: Qt-specific testing utilities (for UI layer when needed)
- **pytest-cov**: Code coverage reporting to verify test completeness
- **pytest-benchmark**: Optional for performance testing (Principle VII)

**Test Organization** (aligns with Constitution Testing Requirements):
- **Unit tests** (`tests/unit/`): Test pipeline stages without OCR execution
  - Mock Tesseract calls to test OCR integration logic without actual text recognition
  - Validate geometric calculations, confidence scoring, threshold application
- **Integration tests** (`tests/integration/`): Test full pipeline with real OCR
  - Use fixture PDFs (representative scans) for regression testing
  - Validate end-to-end accuracy against baseline outputs
- **Contract tests** (`tests/contract/`): Verify pipeline stage interfaces
  - Ensure `preprocessing → layout → ocr → export` contracts are maintained
  - Validate data model transformations between stages

### 7. Configuration Management

**Decision**: Centralized `config.py` module with dataclass-based configuration

**Rationale**:
- **Constitution requirement**: "Magic numbers and thresholds must be centralized" (Code Quality Standards)
- **Type safety**: Use Python dataclasses with type hints for configuration schema
- **Testability**: Easy to override config in unit tests
- **User override**: Support loading config from JSON/YAML file for advanced users

**Example Structure**:
```python
@dataclass
class DetectionConfig:
    page_confidence_threshold: float = 0.80  # 80% for flagging pages
    ocr_confidence_threshold: float = 0.75   # 75% for flagging words
    rotation_auto_correct_angles: list[int] = field(default_factory=lambda: [90, 180, 270])
    
@dataclass
class PerformanceConfig:
    max_memory_mb: int = 500
    max_page_detection_time_ms: int = 500
    max_ocr_time_per_page_s: int = 2
```

### 8. Logging & Diagnostics

**Decision**: Python `logging` module with structured logging

**Rationale**:
- **Explainability**: Log preprocessing decisions, detected boundaries, confidence scores (Principle II)
- **Debugging**: Enable developers and advanced users to diagnose detection issues
- **Failure tracking**: Log all flagged pages and reasons (Principle VI)

**Log Levels**:
- DEBUG: Detailed geometry calculations, threshold comparisons
- INFO: Page processing status, export completion
- WARNING: Low-confidence detections, pages flagged for review
- ERROR: Processing failures, OCR errors

## Best Practices by Technology

### Python Desktop Application Best Practices

1. **Entry Point**: Use `if __name__ == "__main__":` with proper argument parsing (argparse for future CLI support)
2. **Packaging**: Include `pyproject.toml` with build system configuration
3. **Dependencies**: Pin exact versions in `requirements.txt` for reproducibility
4. **Virtual Environments**: Document venv setup for development
5. **Type Hints**: Use throughout for better IDE support and static analysis (mypy)

### Image Processing Best Practices

1. **Color Space**: Convert to grayscale for layout detection (reduces dimensionality)
2. **Preprocessing Pipeline**: Denoise → Normalize → Binarize → Morphological operations
3. **Contour Detection**: Use OpenCV `findContours()` for boundary identification
4. **Connected Components**: Use `cv2.connectedComponentsWithStats()` for region analysis
5. **Rotation Detection**: Use Hough line transform or projection profiles for angle detection

### OCR Integration Best Practices

1. **Image Preprocessing for OCR**: Tesseract works best with clean, binarized images
2. **Language Specification**: Explicitly set language to improve accuracy
3. **Page Segmentation Mode**: Use appropriate PSM (Page Segmentation Mode) for layout
4. **Confidence Parsing**: Extract word-level confidence from `--oem 1` (LSTM engine)
5. **Error Handling**: Tesseract can fail on non-text regions; gracefully handle exceptions

### Qt Desktop Application Best Practices

1. **Threading**: Use QThread for long-running operations (OCR) to keep UI responsive
2. **Signals/Slots**: Qt event system for communication between UI and processing threads
3. **Memory Management**: Use Qt's parent-child relationship for automatic cleanup
4. **High DPI**: Enable high-DPI scaling for modern displays
5. **Accessibility**: Use proper widget labels and keyboard shortcuts (FR-016)

### Testing Best Practices (Constitution Principle V)

1. **Test Fixtures**: Maintain representative scanned PDFs covering edge cases
2. **Baseline Outputs**: Store expected detection results for regression testing
3. **Mock External Dependencies**: Mock Tesseract in unit tests to avoid slow OCR execution
4. **Deterministic Tests**: Ensure tests produce same results across runs (no randomness)
5. **Performance Benchmarks**: Track execution time for layout detection and OCR

## Integration Patterns

### Pipeline Stage Integration

Each pipeline stage follows this contract:

**Input**: Typed data model from previous stage  
**Processing**: Deterministic transformation with logged decisions  
**Output**: Typed data model + confidence score for next stage  
**Failure**: Explicit exceptions with actionable error messages

**Example**: Layout Detection Stage

```python
def detect_layout(page: Page, config: DetectionConfig) -> DetectedBoundary:
    """
    Detect primary page region from scanned page image.
    
    Args:
        page: Page object with image data
        config: Detection configuration with thresholds
        
    Returns:
        DetectedBoundary with coordinates and confidence score
        
    Raises:
        LayoutDetectionError: If no boundary can be detected
    """
    # Preprocessing
    gray_image = preprocess_for_layout(page.image)
    
    # Contour detection
    contours = cv2.findContours(...)
    
    # Boundary identification
    primary_region = identify_primary_region(contours, config)
    
    # Confidence calculation
    confidence = calculate_confidence(primary_region, page.dimensions)
    
    # Logging
    logger.info(f"Detected boundary with confidence {confidence:.2%}")
    if confidence < config.page_confidence_threshold:
        logger.warning(f"Page {page.number} flagged for review")
    
    return DetectedBoundary(
        coordinates=primary_region,
        confidence=confidence,
        method="contour_analysis"
    )
```

### UI to Core Pipeline Integration

**Pattern**: Command pattern with Qt signals

- UI layer emits user actions as signals (load document, adjust boundary, export)
- Controller receives signals and invokes pipeline stages
- Pipeline stages return results via callbacks/signals for UI update
- Long operations (OCR, batch processing) run in QThread to avoid blocking UI

**Threading Model**:
- Main thread: UI rendering, user interaction
- Worker threads: Page processing, OCR execution, PDF export
- Thread-safe queues: Batch processing job queue

## Deployment & Distribution

### Packaging for End Users

**Goal**: Single executable that runs without Python installation

**Tools**: PyInstaller with bundled Tesseract

**Steps**:
1. Create PyInstaller spec file with hidden imports
2. Bundle Tesseract binary and language data files
3. Include Qt plugins for platform-specific features
4. Code signing (Windows Authenticode, macOS notarization) for security warnings
5. Create installers (NSIS for Windows, DMG for macOS, AppImage for Linux)

**Platform-Specific Considerations**:
- **Windows**: Bundle MSVC runtime; sign executable to avoid SmartScreen warnings
- **macOS**: Notarize app for Gatekeeper; handle sandboxing if distributing via App Store
- **Linux**: Provide AppImage or Flatpak for distribution-agnostic deployment

### Development Environment Setup

**Prerequisites**:
- Python 3.11+
- Tesseract OCR installed separately (for development/testing)
- Qt6 development libraries (optional, included via PySide6)

**Setup Commands**:
```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
pip install -r requirements-dev.txt  # pytest, mypy, black, etc.
```

## Research Summary

All technology choices align with constitutional principles:

- **Correctness & Determinism**: OpenCV geometric operations, no random algorithms
- **Explainability**: Tesseract (traditional OCR), geometric layout detection
- **Modularity**: Clear separation of pipeline stages, UI as thin layer
- **Testing**: pytest for unit/integration/contract tests, mock OCR in unit tests
- **Performance**: PyMuPDF for fast rendering, incremental processing architecture
- **Packaging**: PyInstaller for self-contained distribution

**No unresolved technical questions remain.** All dependencies are mature, open-source, and compatible with the constitutional requirements. Phase 1 design can proceed with confidence.
