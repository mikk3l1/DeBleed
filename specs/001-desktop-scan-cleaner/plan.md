# Implementation Plan: Desktop Scan Cleaner Application with OCR

**Branch**: `001-desktop-scan-cleaner` | **Date**: 2026-01-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-desktop-scan-cleaner/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Build a desktop application that enables educators and students to convert imperfect scanned book pages (with multi-page bleed) into clean, searchable, single-page PDFs with OCR text extraction for accessibility. The application uses deterministic image processing for layout detection and primary page region identification, then applies OCR to extracted regions, producing searchable PDFs and plain text output compatible with screen readers. The system emphasizes explainability, determinism, and local processing without cloud dependencies.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: 
- PIL/Pillow (image processing)
- OpenCV or scikit-image (layout detection, geometric analysis)
- Tesseract OCR or pytesseract (text extraction)
- PyMuPDF or PyPDF2 (PDF rendering and generation)
- Qt (PySide6/PyQt6) or Tkinter (cross-platform GUI)
- NumPy (numerical operations for image analysis)

**Storage**: File system only (source PDFs, exported PDFs, text files) - N/A for database  
**Testing**: pytest (unit, integration, contract tests), pytest-qt (GUI testing)  
**Target Platform**: Desktop (Windows 10+, macOS 11+, Linux with GUI) - packaged as standalone executable  
**Project Type**: Single desktop application with GUI + core processing library  
**Performance Goals**: 
- Page detection: <500ms per page (performance target), 5s timeout per FR-047
- OCR processing: <2 seconds per page (performance target), 10s timeout per FR-047
- Memory: <500MB total application RSS memory regardless of document size (incremental processing)
- Load time: <5 seconds for 100-page document, 10s timeout per FR-047

**Constraints**: 
- Deterministic processing (same input → same output)
- Offline-capable (no cloud/internet required)
- Self-contained packaging (no Python installation required by end users)
- Cross-platform desktop support
- Page-by-page processing (avoid loading entire documents into memory)

**Scale/Scope**: 
- Target: Individual users processing 1-100 documents at a time
- Document size: Up to 500 pages per document
- Batch processing: Up to 20 documents (400 total pages) without user intervention

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Correctness & Determinism ✅

**Requirement**: Same input must produce same output; no hidden state or randomness

- **Compliance**: Python with deterministic image processing (OpenCV geometric analysis, connected components) ensures reproducibility
- **Evidence**: Layout detection uses only geometric properties (coordinates, areas, angles) - no random initialization or sampling
- **Configuration**: All thresholds (80% confidence for page detection, 75% for OCR) are explicit and configurable
- **Testing**: Unit tests with fixed input images verify deterministic output

**Status**: PASS - Architecture supports deterministic processing

### Principle II: Explainability & Traceability ✅

**Requirement**: Use explainable techniques (geometric analysis, heuristics) before ML; centralize thresholds

- **Compliance**: Layout detection based on connected components, contour analysis, text density heuristics (no ML for P1)
- **Evidence**: Tesseract OCR is explainable (character recognition with confidence scores), not a black-box neural model
- **Configuration**: Confidence thresholds centralized in config module; preprocessing steps documented
- **Future-proofing**: Architecture allows optional ML enhancement in Phase 2+ with baseline comparison

**Status**: PASS - Deterministic techniques prioritized; OCR engine provides confidence scores

### Principle III: Layout-First Processing ✅

**Requirement**: Identify primary page region before OCR; differentiate primary vs secondary elements

- **Compliance**: Pipeline enforces: load → preprocess → detect layout → identify primary region → OCR on verified region only
- **Evidence**: FR-003, FR-005 mandate layout analysis and region distinction before text extraction
- **Failure handling**: Pages with <80% confidence flagged for manual review (FR-012) - no OCR on uncertain regions
- **Testing**: Layout detection tested independently of OCR execution

**Status**: PASS - Mandatory layout-first workflow enforced in pipeline architecture

### Principle IV: Modular Pipeline Architecture ✅

**Requirement**: Clear separation of pipeline stages with well-defined inputs/outputs

- **Compliance**: Distinct modules: preprocessing, layout detection, OCR integration, PDF assembly, UI layer
- **Evidence**: Each stage independently testable; UI is thin layer over core pipeline
- **Contracts**: Data contracts between stages (Page → DetectedBoundary → OCRResult → ExportJob)
- **Testing**: Unit tests validate each stage without full pipeline execution

**Status**: PASS - Modular design with explicit stage boundaries

### Principle V: Testing & Validation ✅

**Requirement**: Unit tests without OCR dependency; real-world scan validation; edge case coverage

- **Compliance**: pytest for unit/integration tests; layout detection uses representative scanned samples
- **Evidence**: Edge cases documented (skew, rotation, multi-column, blanks, gutters, artifacts)
- **Regression**: Baseline outputs maintained for layout detection accuracy validation
- **Contract tests**: Pipeline stage interfaces validated independently

**Status**: PASS - Testing strategy aligns with validation requirements

### Principle VI: Explicit Failure Handling ✅

**Requirement**: Fail explicitly with actionable errors; surface confidence scores

- **Compliance**: Pages <80% confidence flagged for review; OCR words <75% marked with [?]
- **Evidence**: FR-012, FR-013, FR-019, FR-026 require clear indicators and error messages
- **User visibility**: Confidence scores exposed in UI; flagged pages visually distinct
- **No silent failures**: Uncertain detection prevents automatic export

**Status**: PASS - Explicit confidence thresholds and user-facing error reporting

### Principle VII: Performance & Scalability ✅

**Requirement**: Incremental processing; memory scales with single page, not document size

- **Compliance**: Page-by-page processing; <500MB memory limit regardless of document size (FR-018, SC-007)
- **Evidence**: PDF rendering and export performed incrementally, not in-memory for entire document
- **Performance**: <500ms page detection, <2s OCR per page (SC-014)
- **Batch processing**: Supports parallelization for multiple documents (FR-014)

**Status**: PASS - Incremental processing architecture meets scalability requirements

### Gate Evaluation Summary

**All 7 constitutional principles: PASS ✅**

No violations identified. The Python desktop architecture with modular pipeline design, deterministic image processing, explicit confidence thresholds, and incremental page handling fully complies with constitutional requirements.

**Proceed to Phase 0 (Research)**

## Project Structure

### Documentation (this feature)

```text
specs/001-desktop-scan-cleaner/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
debleed/                          # Root project directory
├── src/
│   ├── debleed/                  # Main package
│   │   ├── __init__.py
│   │   ├── config.py             # Centralized configuration and thresholds
│   │   ├── pipeline/             # Core processing pipeline
│   │   │   ├── __init__.py
│   │   │   ├── preprocessing.py  # Image normalization, artifact removal
│   │   │   ├── layout.py         # Page layout detection, boundary identification
│   │   │   ├── ocr.py            # OCR integration (Tesseract wrapper)
│   │   │   └── export.py         # PDF assembly, text file generation
│   │   ├── models/               # Data models
│   │   │   ├── __init__.py
│   │   │   ├── document.py       # ScannedDocument, Page
│   │   │   ├── boundary.py       # DetectedBoundary, PrimaryPageRegion
│   │   │   ├── ocr_result.py     # OCRResult, TextBlock
│   │   │   └── export_job.py     # ExportJob, BatchQueue
│   │   └── ui/                   # GUI layer (thin wrapper)
│   │       ├── __init__.py
│   │       ├── main_window.py    # Main application window
│   │       ├── preview_widget.py # Page preview and thumbnail grid
│   │       ├── boundary_editor.py # Manual boundary adjustment
│   │       └── batch_processor.py # Batch processing UI
│   └── debleed_app.py            # Application entry point
├── tests/
│   ├── unit/                     # Unit tests (no OCR execution)
│   │   ├── test_preprocessing.py
│   │   ├── test_layout.py
│   │   └── test_models.py
│   ├── integration/              # Integration tests (with OCR)
│   │   ├── test_pipeline.py
│   │   └── test_export.py
│   ├── contract/                 # Contract tests for pipeline stages
│   │   └── test_stage_contracts.py
│   └── fixtures/                 # Test data (sample scanned PDFs)
│       ├── single_page_clean.pdf
│       ├── multi_page_bleed.pdf
│       ├── rotated_pages.pdf
│       └── multi_column.pdf
├── docs/                         # User documentation
│   ├── user_guide.md
│   └── developer_guide.md
├── pyproject.toml                # Python project configuration
├── requirements.txt              # Python dependencies
├── README.md                     # Project overview
└── .gitignore
```

**Structure Decision**: Single desktop application structure selected. The project is organized as a Python package (`debleed/`) with clear separation between core processing logic (`pipeline/`), data models (`models/`), and UI layer (`ui/`). This structure supports the constitutional requirement for modular pipeline architecture while enabling independent testing of core logic without UI or OCR dependencies. The `src/` layout follows modern Python packaging best practices for distribution as a standalone executable via PyInstaller or similar tooling.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitutional violations identified. This section is not applicable.

---

## Phase 0: Research & Technology Decisions ✅

**Status**: COMPLETED  
**Output**: [research.md](research.md)

### Technology Stack Selected

**Core Processing**:
- Python 3.11+ (type hints, performance improvements)
- OpenCV 4.x (deterministic geometric analysis for layout detection)
- Pillow 10.x (image format handling, preprocessing)
- Tesseract OCR 5.x via pytesseract (text extraction with confidence scoring)
- PyMuPDF (fitz) 1.23+ (fast PDF rendering and generation)

**User Interface**:
- PySide6 (Qt for Python) 6.6+ (cross-platform GUI framework)
- Qt Widgets for desktop UI components
- Qt threads for non-blocking pipeline execution

**Testing & Quality**:
- pytest 7.x (unit, integration, contract tests)
- pytest-qt (Qt widget testing)
- mypy (static type checking)
- black + ruff (code formatting and linting)

**Distribution**:
- PyInstaller 6.x (standalone executable packaging)
- Bundled Tesseract executable and language data

### Research Outcomes

All technology choices documented in [research.md](research.md) align with constitutional principles:

- **Determinism**: OpenCV geometric algorithms (no random sampling), fixed Tesseract configuration
- **Explainability**: Contour analysis, connected components (no ML black boxes for P1)
- **Performance**: PyMuPDF for fast PDF I/O, incremental page processing
- **Modularity**: Clear separation between Qt UI and core pipeline logic
- **Testing**: pytest enables independent unit tests without GUI or OCR execution

---

## Phase 1: Design Artifacts ✅

**Status**: COMPLETED  
**Outputs**: [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

### Data Model

[data-model.md](data-model.md) defines 8 core entities:

1. **ScannedDocument**: Input PDF with processing status tracking
2. **Page**: Individual page with rendered image, detected boundary, OCR result
3. **PrimaryPageRegion**: Geometric region representing intended page content
4. **DetectedBoundary**: Calculated coordinates with confidence metadata
5. **OCRResult**: Extracted text with block structure and flagged words
6. **TextBlock**: Structural unit (paragraph) with position and confidence
7. **ExportJob**: Processing task for PDF/text generation
8. **BatchQueue**: Collection of export jobs with progress tracking

**Key Design Decisions**:
- All entities use Python dataclasses with full type hints (mypy compliance)
- Confidence thresholds (0.80 for layout, 0.75 for OCR) embedded in model validation
- State machine for document processing (LOADED → ANALYZING → READY → EXPORTING → COMPLETE)
- Optional fields (`detected_boundary: DetectedBoundary | None`) for pipeline stages that haven't executed yet

### Pipeline Contracts

Four stage contracts documented in [contracts/](contracts/):

1. **[preprocessing.md](contracts/preprocessing.md)**: PDF → RGB Image
   - Input: PDF path + page number + target DPI
   - Output: RGB uint8 array (H×W×3)
   - Guarantees: Deterministic rendering, color normalization
   - Performance: <200ms per page

2. **[layout.md](contracts/layout.md)**: Image → Detected Boundary
   - Input: RGB image + detection config
   - Output: Primary region coordinates + confidence (0.0-1.0)
   - Algorithm: Canny edge detection → contour extraction → geometric ranking
   - Guarantees: No randomness, confidence >= 0.80 for production-ready detection
   - Performance: <500ms per page

3. **[ocr.md](contracts/ocr.md)**: Cropped Region → Text + Confidence
   - Input: Cropped image region + language + config
   - Output: Text content + text blocks + flagged words (confidence < 0.75)
   - Algorithm: Tesseract with fixed PSM/OEM modes for determinism
   - Guarantees: Word-level confidence scores, reading order determination
   - Performance: <2 seconds per page

4. **[export.md](contracts/export.md)**: Document + Pages → PDF/Text Files
   - Input: ScannedDocument + selected pages + output format
   - Output: Cleaned PDF with optional text layer + plain text file
   - Guarantees: Byte-identical output (excluding metadata timestamps)
   - Formats: SEARCHABLE_PDF, PDF_AND_TEXT, TEXT_ONLY

**Contract Testing Strategy**: Each contract includes:
- Input/output schemas with validation rules
- Error codes for explicit failure handling
- Performance requirements with measurement approach
- Unit tests for happy path + edge cases
- Integration tests for pipeline flow

### Developer Onboarding

[quickstart.md](quickstart.md) provides:
- 30-minute setup guide (Python 3.11+, venv, dependencies, Tesseract installation)
- First pipeline test walkthrough (preprocessing → layout → OCR → export)
- Project structure explanation with file-by-file breakdown
- Development workflow (mypy → black → pytest → commit)
- Common tasks (add config parameter, add pipeline stage, run GUI)
- Troubleshooting section (Tesseract PATH, Qt dependencies, memory issues)

### Agent Context Update

Updated `.github/agents/copilot-instructions.md` with:
- Language: Python 3.11+ with type hints
- Database: File system only (no SQL/NoSQL)
- Project type: Desktop application with modular pipeline
- Technology stack: OpenCV, Tesseract, PyMuPDF, PySide6

---

## Constitution Check Re-Evaluation (Post-Design)

**Gate**: Verify Phase 1 design maintains constitutional compliance

### Principle I: Correctness & Determinism ✅

**Design Validation**:
- Data model uses deterministic types (no floats without bounds, all enums explicit)
- Pipeline contracts specify fixed algorithm parameters (Canny thresholds, Tesseract PSM/OEM modes)
- Export contract guarantees byte-identical PDFs (excluding metadata timestamps)

**Status**: PASS - Design preserves determinism

### Principle II: Explainability & Traceability ✅

**Design Validation**:
- Layout contract documents geometric algorithms step-by-step (edge detection → contours → ranking)
- OCR contract exposes confidence scores per word, not just overall accuracy
- Data model includes `debug_info` field for visualization of intermediate steps

**Status**: PASS - Design enables explainability

### Principle III: Layout-First Processing ✅

**Design Validation**:
- Pipeline contracts enforce sequential execution: preprocessing.md → layout.md → ocr.md → export.md
- Data model enforces `Page.detected_boundary` must exist before `Page.ocr_result` is populated
- Export contract validates `document.processing_status == READY` (layout complete) before export

**Status**: PASS - Design enforces layout-first workflow

### Principle IV: Modular Pipeline Architecture ✅

**Design Validation**:
- Four independent contracts with no circular dependencies
- Each contract specifies "Depends On" and "No Dependencies On" sections
- Data model entities cleanly map to pipeline stages (Page → DetectedBoundary → OCRResult → ExportJob)

**Status**: PASS - Design maintains modularity

### Principle V: Testing & Validation ✅

**Design Validation**:
- Each contract includes dedicated "Testing Requirements" section (unit, integration, contract tests)
- Quickstart provides example unit tests and pytest commands
- Data model entities use type hints enabling mypy static validation

**Status**: PASS - Design supports comprehensive testing

### Principle VI: Explicit Failure Handling ✅

**Design Validation**:
- All contracts define error schemas with typed error codes
- Data model includes validation rules (e.g., `confidence_score` must be in [0.0, 1.0])
- Export contract specifies exact error conditions (INVALID_OUTPUT_PATH, OCR_MISSING, DISK_FULL)

**Status**: PASS - Design enforces explicit error handling

### Principle VII: Performance & Scalability ✅

**Design Validation**:
- Pipeline contracts specify performance limits (preprocessing: <200ms, layout: <500ms, OCR: <2s)
- Data model includes lazy-loading (`preview_thumbnail: ndarray | None`) to avoid memory bloat
- Export contract documents sequential page processing (not all-in-memory)

**Status**: PASS - Design meets performance requirements

### Gate Evaluation Summary (Post-Design)

**All 7 constitutional principles: PASS ✅**

Phase 1 design artifacts maintain full constitutional compliance. No new violations introduced. The detailed contracts, data model, and quickstart guide provide a solid foundation for implementation.

**Cleared for Phase 2 (Task Breakdown)**

---

## Next Steps

**This command (`/speckit.plan`) ends here.** The following artifacts have been generated:

✅ [plan.md](plan.md) - This implementation plan (technical context, constitution check, project structure)  
✅ [research.md](research.md) - Technology stack decisions with rationale  
✅ [data-model.md](data-model.md) - 8 core entities with relationships and validation rules  
✅ [contracts/preprocessing.md](contracts/preprocessing.md) - PDF to RGB image conversion contract  
✅ [contracts/layout.md](contracts/layout.md) - Layout detection contract with geometric algorithms  
✅ [contracts/ocr.md](contracts/ocr.md) - Text extraction contract with confidence scoring  
✅ [contracts/export.md](contracts/export.md) - PDF/text export contract with determinism guarantees  
✅ [quickstart.md](quickstart.md) - Developer onboarding guide (30-minute setup)  
✅ `.github/agents/copilot-instructions.md` - Updated agent context

**To proceed with implementation planning**, run:

```bash
/speckit.tasks
```

This will generate [tasks.md](tasks.md) with a prioritized breakdown of implementation tasks (Phase 2).
