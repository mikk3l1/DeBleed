# Tasks: Desktop Scan Cleaner Application

**Input**: Design documents from `/specs/001-desktop-scan-cleaner/`  
**Branch**: `001-desktop-scan-cleaner`  
**Prerequisites**: plan.md, spec.md (5 user stories), data-model.md (8 entities), contracts/ (4 stages)

**Tests**: OPTIONAL - Not explicitly requested in specification. Focus on implementation with contract validation.

**Organization**: Tasks grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4, US5)
- All paths relative to repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure  
**Duration**: ~2-4 hours  
**Blocking**: Must complete before Phase 2

- [ ] T001 Create project directory structure: src/debleed/, tests/, docs/
- [ ] T002 Initialize Python 3.11+ project with pyproject.toml and requirements.txt
- [ ] T003 [P] Configure mypy for type checking with strict mode
- [ ] T004 [P] Configure black and ruff for code formatting and linting
- [ ] T005 [P] Setup pytest with pytest-qt for testing framework
- [ ] T006 Create src/debleed/__init__.py with version and package exports
- [ ] T007 Create src/debleed/config/settings.py for centralized configuration (thresholds, paths)
- [ ] T008 Create .gitignore for Python project (venv/, __pycache__/, *.pyc, .pytest_cache/)

**Checkpoint**: Basic project structure ready, dependencies installable via `pip install -e .`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story implementation  
**Duration**: ~6-10 hours  
**Blocking**: No user story work can begin until this phase is complete

### Data Models (Foundational - All Stories Depend On These)

- [X] T009 [P] Create src/debleed/models/__init__.py with enum exports (ProcessingStatus, AdjustmentStatus, ExportFormat, JobStatus)
- [X] T010 [P] Create src/debleed/models/enums.py with all enumerations (ProcessingStatus, AdjustmentStatus, ExportFormat, JobStatus)
- [X] T011 [P] Create src/debleed/models/page.py with Page and PrimaryPageRegion dataclasses
- [X] T012 [P] Create src/debleed/models/boundary.py with DetectedBoundary dataclass
- [X] T013 [P] Create src/debleed/models/document.py with ScannedDocument dataclass
- [X] T014 [P] Create src/debleed/models/ocr_result.py with OCRResult and TextBlock dataclasses
- [X] T015 [P] Create src/debleed/models/export_job.py with ExportJob and BatchQueue dataclasses

### Configuration System

- [X] T016 Create src/debleed/config/__init__.py with config exports
- [X] T017 Create src/debleed/config/detection_config.py with DetectionConfig dataclass (page_confidence_threshold=0.80, canny thresholds)
- [X] T018 [P] Create src/debleed/config/ocr_config.py with OCRConfig dataclass (confidence_threshold=0.75, tesseract_psm, timeout)
- [X] T019 [P] Create src/debleed/config/export_config.py with ExportConfig dataclass (default_suffix="_cleaned", compression_quality)
- [X] T020 [P] Create src/debleed/config/performance_config.py with PerformanceConfig dataclass (memory limits, timeouts)

### Error Handling Infrastructure

- [X] T021 Create src/debleed/core/__init__.py with exception exports
- [X] T022 Create src/debleed/core/exceptions.py with typed exceptions (PreprocessingError, LayoutDetectionError, OCRError, ExportError)

**Checkpoint**: Foundation complete - all models, configs, and error types available for user story implementation


## Phase 3: User Story 1 - Single Document Cleanup (Priority: P1) 🎯 MVP

**Goal**: Load PDF, detect page boundaries automatically, export cleaned PDF  
**Independent Test**: Load sample multi-page-bleed PDF, verify boundaries detected with >80% confidence, export cleaned PDF with only primary regions  
**MVP Scope**: This story represents minimum viable product - delivers core value

### Pipeline Stage 1: Preprocessing (US1 - Required for Layout Detection)

- [X] T023 [P] [US1] Create src/debleed/core/preprocessing.py with PreprocessingInput/Output dataclasses
- [X] T024 [US1] Implement preprocess_page() function: PDF → RGB image using PyMuPDF
- [X] T025 [US1] Add color normalization (grayscale → RGB, RGBA → RGB) with deterministic output
- [X] T026 [US1] Add DPI adjustment logic (respect target_dpi, avoid upscaling)
- [X] T027 [US1] Add error handling for PDF_UNREADABLE, PAGE_OUT_OF_RANGE, RENDER_FAILED, MEMORY_EXCEEDED

### Pipeline Stage 2: Layout Detection (US1 - Core Functionality)

- [X] T028 [P] [US1] Create src/debleed/core/layout_detection.py with LayoutDetectionInput/Output dataclasses
- [X] T029 [US1] Implement detect_layout() function: image → DetectedBoundary
- [X] T030 [US1] Add Canny edge detection with fixed thresholds (50, 150) for determinism
- [X] T031 [US1] Add contour extraction using OpenCV findContours()
- [X] T032 [US1] Implement region ranking by area, rectangularity, edge strength
- [X] T033 [US1] Calculate confidence score (0.5*area + 0.3*rectangularity + 0.2*edge_strength)
- [X] T034 [US1] Add rotation detection for 90°/180°/270° auto-correction (stub for MVP)
- [X] T035 [US1] Add error handling for INVALID_IMAGE, NO_REGIONS_FOUND, TIMEOUT, MEMORY_EXCEEDED
- [X] T036 [US1] Add debug_info generation (edge_map, contours, bounding_boxes) when enabled

### Document Loading & State Management (US1)

- [X] T037 [P] [US1] Create src/debleed/core/document_loader.py with load_document() function
- [X] T038 [US1] Implement ScannedDocument creation from PDF file path
- [X] T039 [US1] Add page count extraction and validation (>0 pages)
- [X] T040 [US1] Implement state transitions (LOADED → ANALYZING → READY)
- [X] T041 [US1] Add file size calculation for memory estimation
- [X] T042 [US1] Add error handling for non-existent files, non-PDF files (FR-042), encrypted PDFs (FR-031)

### Pipeline Orchestration (US1 - Ties Everything Together)

- [X] T043 [US1] Create src/debleed/core/pipeline.py with process_document() function
- [X] T044 [US1] Implement page-by-page processing loop (iterate through document.pages)
- [X] T045 [US1] Wire preprocessing → layout detection per page
- [X] T046 [US1] Add confidence flagging (score < 0.80 → adjustment_status = FLAGGED; 0.80-0.85 → is_borderline_confidence = True per FR-041)
- [X] T047 [US1] Implement incremental memory management (release page N-1 after processing N per FR-055)
- [X] T048 [US1] Add progress tracking (update processing_status states)
- [X] T049 [US1] Add timeout enforcement wrapper for pipeline stages (10s file load, 5s layout timeout, integrate with per-stage error handling per FR-047)
- [X] T049a [US1] Implement timeout mechanism using threading.Timer or asyncio.timeout for interruptible operations
- [X] T049b [US1] Add timeout exception handling that converts to user-facing error messages (FR-037 to FR-040)

### Export Stage (US1 - Produces Cleaned PDF)

- [X] T050 [P] [US1] Create src/debleed/core/export.py with ExportInput/Output dataclasses
- [X] T050a [US1] Add disk space validation function (check available space >= 2x estimated output size per FR-051)
- [X] T051 [US1] Implement export_document() function for PDF-only export (call T050a before starting export)
- [X] T052 [US1] Add PDF page creation with PyMuPDF: crop to primary_region coordinates
- [X] T053 [US1] Implement filename generation (source + "_cleaned" suffix in same directory per FR-015, Clarifications)
- [X] T054 [US1] Add JPEG compression with configurable quality (default 85 per ExportConfig)
- [X] T055 [US1] Add error handling for INVALID_OUTPUT_PATH, WRITE_FAILED, DISK_FULL per FR-040
- [X] T056 [US1] Implement disk space checking before export (require 2x estimated size per FR-051)
- [X] T057 [US1] Add deterministic PDF generation (disable metadata timestamps per contracts/export.md)

### Basic GUI (US1 - Minimal UI for MVP)

- [X] T058 [P] [US1] Create src/debleed/ui/__init__.py with Qt imports
- [X] T059 [US1] Create src/debleed/ui/main_window.py with MainWindow class (PySide6 QMainWindow)
- [X] T060 [US1] Add file picker dialog (QFileDialog) for PDF selection
- [X] T061 [US1] Add simple page list view showing page numbers and confidence scores
- [X] T062 [US1] Add "Export Clean PDF" button with click handler
- [X] T063 [US1] Add progress indicator (QProgressBar) during processing
- [X] T064 [US1] Add status messages (QStatusBar) for load/process/export operations
- [X] T065 [US1] Wire UI → pipeline.process_document() → export.export_document()
- [X] T066 [US1] Add error dialog display for pipeline errors (QMessageBox)

### Application Entry Point (US1)

- [X] T067 [US1] Create src/debleed/main.py with QApplication initialization
- [X] T068 [US1] Add OCR engine detection at startup (check Tesseract availability per FR-046, SC-020)
- [X] T069 [US1] Display initialization error if Tesseract missing (with installation instructions)
- [X] T070 [US1] Launch MainWindow and start event loop

**Checkpoint**: ✅ MVP Complete - User can load PDF, see detected boundaries, export cleaned PDF


## Phase 4: User Story 5 - Text Extraction for Accessibility (Priority: P1)

**Goal**: Add OCR text extraction for searchable PDFs and screen reader compatibility  
**Independent Test**: Load scanned document, process with OCR, export searchable PDF + text file, verify text readable by NVDA/JAWS  
**Why P1**: Core accessibility requirement - critical for primary use case

### Pipeline Stage 3: OCR Integration (US5)

- [ ] T071 [P] [US5] Create src/debleed/core/ocr_integration.py with OCRInput/Output dataclasses
- [ ] T072 [US5] Implement extract_text() function: cropped image → OCROutput
- [ ] T073 [US5] Add Tesseract execution via pytesseract with fixed PSM mode (3) and OEM mode (3)
- [ ] T074 [US5] Implement word-level confidence extraction from Tesseract output
- [ ] T075 [US5] Add low-confidence word flagging (confidence < 0.75 per FR-026, Clarifications)
- [ ] T076 [US5] Implement text block segmentation from Tesseract block-level data
- [ ] T077 [US5] Add reading order determination (left-to-right columns per Clarifications)
- [ ] T078 [US5] Implement multi-column detection heuristic (gap-based clustering)
- [ ] T079 [US5] Add language support (English required, Spanish/French/German bundled per FR-054)
- [ ] T080 [US5] Add error handling for TESSERACT_NOT_FOUND, LANGUAGE_NOT_AVAILABLE, INVALID_IMAGE, TIMEOUT per FR-039
- [ ] T081 [US5] Add timeout enforcement wrapper for OCR execution (10s hard timeout per page per FR-047, SC-021, with 2s performance target)
- [ ] T082 [US5] Add non-text element handling (preserve images/diagrams in PDF output, skip OCR for image-only regions, log skipped regions without errors per FR-053)

### OCR Runtime Detection (US5)

- [ ] T083 [US5] Add get_tesseract_path() function for bundled vs system Tesseract detection
- [ ] T084 [US5] Implement Tesseract initialization check at startup (integrate with T068)
- [ ] T085 [US5] Add language pack verification (check eng.traineddata, spa, fra, deu availability)

### Export Enhancement for OCR (US5)

- [ ] T086 [US5] Enhance export_document() to support SEARCHABLE_PDF format (extends T051)
- [ ] T087 [US5] Implement invisible text layer embedding in PDF using PyMuPDF insert_text()
- [ ] T088 [US5] Add font size calculation for text blocks (match visual text size)
- [ ] T089 [US5] Implement PDF_AND_TEXT format (PDF + .txt file)
- [ ] T090 [US5] Implement TEXT_ONLY format (plain text export)
- [ ] T091 [US5] Add page separator formatting for multi-page text ("--- Page N ---" per contracts/export.md)
- [ ] T092 [US5] Add [?] marker insertion for flagged words in text output (FR-026, data-model §OCRResult.plain_text)
- [ ] T093 [US5] Add paragraph break preservation in text export (FR-030)

### Pipeline Integration for OCR (US5)

- [ ] T094 [US5] Enhance pipeline.process_document() to optionally run OCR after layout detection
- [ ] T095 [US5] Add OCR warning for low-confidence pages (run OCR on all pages with detected primary regions, but surface warnings for pages with confidence < 0.80 per FR-012, FR-026)
- [ ] T096 [US5] Add partial OCR failure handling (18/20 pages succeed per FR-052)
- [ ] T097 [US5] Update progress tracking to include OCR stage

### UI Enhancement for OCR (US5)

- [ ] T098 [US5] Add export format selection dropdown (Searchable PDF, PDF + Text, Text Only) to MainWindow
- [ ] T099 [US5] Add OCR status indication in page list (show OCR confidence if performed)
- [ ] T100 [US5] Add warning display for pages with low OCR confidence (<75%)
- [ ] T101 [US5] Update progress bar to show OCR processing stage

**Checkpoint**: ✅ Accessibility Complete - Searchable PDFs with text layer, screen reader compatible

---

## Phase 5: User Story 2 - Boundary Adjustment (Priority: P2)

**Goal**: Allow manual adjustment of detected boundaries for problematic pages  
**Independent Test**: Load document with one low-confidence page, manually adjust boundary via UI, verify custom boundary used in export  
**Why P2**: Handles edge cases where automatic detection fails

### Boundary Adjustment UI (US2)

- [ ] T102 [P] [US2] Create src/debleed/ui/boundary_editor.py with BoundaryEditorWidget class
- [ ] T103 [US2] Implement page image display with overlay for detected boundary (using QPainter)
- [ ] T104 [US2] Add interactive drag handles for boundary corners (QGraphicsView approach)
- [ ] T105 [US2] Implement real-time preview updates during drag (<100ms latency for FR-011)
- [ ] T106 [US2] Add "Apply" button to save manual adjustment
- [ ] T107 [US2] Add "Reset to Auto" button to restore automatic detection
- [ ] T108 [US2] Update Page.adjustment_status to MANUAL when user applies changes
- [ ] T109 [US2] Set Page.confidence_score to 1.0 for manual adjustments (per data-model.md §PrimaryPageRegion validation)

### Manual Adjustment Persistence (US2)

- [ ] T110 [US2] Implement in-memory storage of manual adjustments in ScannedDocument.pages
- [ ] T111 [US2] Add optional save-to-sidecar-file functionality (JSON next to source PDF per FR-035, SC-018)
- [ ] T112 [US2] Implement load-from-sidecar-file on document open
- [ ] T113 [US2] Add "Save Adjustments" option in UI (checkbox or menu item)

### UI Integration (US2)

- [ ] T114 [US2] Add double-click handler on page thumbnails to open boundary editor (from User Story 4 acceptance scenario 5)
- [ ] T115 [US2] Add exit warning if unsaved manual adjustments exist (FR-049)
- [ ] T116 [US2] Update export to use manual boundaries when adjustment_status == MANUAL

**Checkpoint**: ✅ Manual Adjustment Complete - Users can fix incorrect automatic detections

---

## Phase 6: User Story 4 - Preview Before Export (Priority: P2)

**Goal**: Enable quality review via thumbnail grid and detailed previews  
**Independent Test**: Load 50-page document, navigate thumbnails, filter to flagged pages, verify navigation works  
**Why P2**: Quality assurance before export prevents wasted time

### Thumbnail Generation (US4)

- [ ] T117 [P] [US4] Create src/debleed/ui/preview_widget.py with ThumbnailGridWidget class
- [ ] T118 [US4] Implement lazy thumbnail generation (render on-demand when scrolled into view per CHK009)
- [ ] T119 [US4] Add thumbnail caching (200x200 px size per PerformanceConfig)
- [ ] T120 [US4] Display detected boundary overlay on thumbnails (colored border)
- [ ] T121 [US4] Add visual flagging for low-confidence pages (red border or icon per FR-013)
- [ ] T122 [US4] Add visual flagging for borderline-confidence pages (check Page.is_borderline_confidence, yellow border per FR-041)

### Page Navigation (US4)

- [ ] T123 [US4] Create src/debleed/ui/page_preview_dialog.py with PagePreviewDialog class for detailed view
- [ ] T124 [US4] Add click handler on thumbnails to open detailed preview
- [ ] T125 [US4] Implement arrow key navigation (prev/next page) in preview dialog
- [ ] T126 [US4] Add page number indicator and navigation controls (first/prev/next/last buttons)

### Filtering & Views (US4)

- [ ] T127 [US4] Add filter dropdown to MainWindow (All Pages, Flagged for Review, Manually Adjusted per FR-017)
- [ ] T128 [US4] Implement filter logic for flagged pages (confidence < 0.80)
- [ ] T129 [US4] Implement filter logic for manually adjusted pages (adjustment_status == MANUAL)
- [ ] T130 [US4] Add page count display for each filter state

### Keyboard Shortcuts (US4)

- [ ] T131 [P] [US4] Add keyboard shortcut definitions (e.g., Ctrl+O open, Ctrl+E export, Arrow keys navigate)
- [ ] T132 [US4] Implement QShortcut handlers in MainWindow
- [ ] T133 [US4] Add keyboard shortcut help dialog (F1 or Help menu)

**Checkpoint**: ✅ Preview Complete - Users can review all pages before export

---

## Phase 7: User Story 3 - Batch Processing (Priority: P3)

**Goal**: Process multiple documents sequentially with minimal user interaction  
**Independent Test**: Select 20 PDF files, initiate batch, verify all succeed/fail appropriately, check results summary  
**Why P3**: Power user feature for institutional use cases

### Batch Queue Management (US3)

- [ ] T134 [P] [US3] Create src/debleed/core/batch_processor.py with BatchProcessor class
- [ ] T135 [US3] Implement create_batch_queue() function: list of file paths → BatchQueue
- [ ] T136 [US3] Add ExportJob creation for each document
- [ ] T137 [US3] Implement FIFO processing (process jobs in order per CHK086)
- [ ] T138 [US3] Add overall progress calculation (successful + failed / total)

### Batch Processing Loop (US3)

- [ ] T139 [US3] Implement process_batch() function: iterate through export_jobs
- [ ] T140 [US3] Wire each job to full pipeline: load → process → OCR → export
- [ ] T141 [US3] Add per-document error handling (skip failed, continue with remaining per FR-032, SC-016)
- [ ] T142 [US3] Update BatchQueue.successful_exports and failed_exports counters
- [ ] T143 [US3] Add flagged_for_review tracking (count documents with low-confidence pages)
- [ ] T144 [US3] Implement crash recovery (save queue state periodically per FR-036)
- [ ] T145 [US3] Add resume-from-checkpoint on application restart

### Batch UI (US3)

- [ ] T146 [P] [US3] Create src/debleed/ui/batch_dialog.py with BatchProcessingDialog class
- [ ] T147 [US3] Add multi-file selection (QFileDialog with multiple=True)
- [ ] T148 [US3] Add drag-and-drop support for multiple files (QDragEnterEvent, QDropEvent)
- [ ] T149 [US3] Display batch queue with job list (file name, status, progress)
- [ ] T150 [US3] Add per-document progress bar (0-100% per file)
- [ ] T151 [US3] Add overall batch progress bar (documents complete / total)
- [ ] T152 [US3] Add "Start Batch" and "Cancel Batch" buttons
- [ ] T153 [US3] Implement results summary display (successful, failed, flagged counts)
- [ ] T154 [US3] Add error details display for failed documents (clickable to see error message)

### Batch Processing Enhancements (US3)

- [ ] T155 [US3] Add pause/resume UI controls (for large batches per FR-034, SC-017)
- [ ] T156 [US3] Implement pause logic (stop after current document completes)
- [ ] T157 [US3] Implement resume logic (continue from paused state without reprocessing)
- [ ] T158 [US3] Add exit warning if batch in progress (FR-048)
- [ ] T159 [US3] Add cancellation cleanup (delete partial export files per FR-045)

**Checkpoint**: ✅ Batch Processing Complete - Efficient multi-document workflows enabled

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Non-story-specific features and refinements  
**Duration**: ~4-8 hours

### Error Handling & User Feedback

- [ ] T160 [P] Improve all error messages to be user-friendly with actionable recovery steps (FR-019)
- [ ] T161 [P] Add detailed logging throughout pipeline (use Python logging module)
- [ ] T162 Add operation cancellation support (cancel export mid-process per FR-045, SC-019)
- [ ] T163 Implement partial export functionality with UI feedback (export 100/500 completed pages, display dialog showing partial status, indicate in output filename per FR-056, SC-022)

### Performance Optimization

- [ ] T164 [P] Profile preprocessing stage (verify <200ms per page target per contracts/preprocessing.md)
- [ ] T165 [P] Profile layout detection stage (verify <500ms per page target)
- [ ] T166 [P] Profile OCR stage (verify <2s per page target per contracts/ocr.md)
- [ ] T167 Optimize memory usage (verify <500MB total regardless of document size per SC-007, FR-018)
- [ ] T168 Add oversized page detection and rejection (>100MB per page per FR-050)

### Configuration & Settings

- [ ] T169 [P] Add configuration file support (load DetectionConfig, OCRConfig, ExportConfig from TOML/JSON)
- [ ] T170 [P] Add settings UI dialog for user-configurable thresholds (confidence, timeouts)
- [ ] T171 Add language selection UI for OCR (dropdown with English/Spanish/French/German per FR-054)

### Testing Infrastructure (if time permits)

- [ ] T172 [P] Create tests/fixtures/ directory with sample PDFs (single-page clean, multi-page bleed, rotated, multi-column)
- [ ] T173 [P] Add contract tests for preprocessing stage (verify PreprocessingOutput schema)
- [ ] T174 [P] Add contract tests for layout detection stage (verify confidence in [0.0, 1.0])
- [ ] T175 [P] Add contract tests for OCR stage (verify flagged_words have confidence < 0.75)
- [ ] T176 [P] Add contract tests for export stage (verify byte-identical PDFs)
- [ ] T177 Add integration test for full pipeline (PDF → preprocessed → layout → OCR → export)

### Documentation

- [ ] T178 [P] Update README.md with installation instructions
- [ ] T179 [P] Add user guide in docs/user_guide.md
- [ ] T180 Add inline code documentation (docstrings for all public functions)

### Packaging & Distribution

- [ ] T181 Create PyInstaller spec file for standalone executable
- [ ] T182 Bundle Tesseract executable and language data (eng, spa, fra, deu)
- [ ] T183 Test packaged application on Windows 10+, macOS 11+, Linux
- [ ] T184 Create installer scripts (optional: Inno Setup for Windows, DMG for macOS)

**Checkpoint**: ✅ Application polished and ready for release

---

## Dependencies Between User Stories

**User Story Dependency Graph**:

```
Phase 1 (Setup) ──> Phase 2 (Foundational)
                         │
                         ├──> Phase 3 (US1 - Single Document) ──> Phase 5 (US2 - Boundary Adjustment)
                         │                                                           │
                         │                                                           v
                         │                                             Phase 6 (US4 - Preview)
                         │                                                           │
                         ├──> Phase 4 (US5 - OCR/Accessibility) ────────────────────┘
                         │                                                           │
                         └─────────────────────────────────────────> Phase 7 (US3 - Batch Processing)
                                                                                     │
                                                                                     v
                                                                     Phase 8 (Polish & Cross-Cutting)
```

**Dependency Explanation**:
- **US1 (Single Document)** MUST be complete before US2 (needs boundary editor integration)
- **US1** MUST be complete before US4 (needs thumbnails and preview of detected boundaries)
- **US5 (OCR)** can be developed in parallel with US1 (different pipeline stages)
- **US3 (Batch)** depends on US1 complete + US5 complete (needs full pipeline working)
- **US2 and US4** can be developed in parallel after US1 is complete

**Blocking Tasks** (Cannot proceed without these):
- T001-T008 (Setup): Required for any coding
- T009-T022 (Foundational): Required for all user stories
- T023-T070 (US1 Implementation): Required for MVP

---

## Parallel Execution Opportunities

### Phase 2 (Foundational) - Fully Parallelizable
**Team of 5 developers**:
- Developer A: Data models (T009-T015)
- Developer B: Configuration system (T016-T020)
- Developer C: Error infrastructure (T021-T022)

**Completion**: All Phase 2 tasks can finish in ~3-4 hours

---

### Phase 3 (US1) + Phase 4 (US5) - Parallel Pipeline Development
**Team of 5 developers after Phase 2 complete**:
- Developer A: Preprocessing + Layout Detection (T023-T036)
- Developer B: Document Loading + Pipeline (T037-T049)
- Developer C: Export (T050-T057)
- Developer D: Basic GUI (T058-T066) + Entry Point (T067-T070)
- Developer E: OCR Integration (T071-T082) [US5, can work in parallel]

**Completion**: US1 MVP can be complete in ~8-12 hours  
**Completion**: US5 OCR ready in ~8-12 hours (parallel)

---

### After US1 Complete - Multiple Parallel Streams
**Option 1**: Small team (2-3 developers)
- Developer A: US2 Boundary Adjustment (T102-T116) - ~6 hours
- Developer B: US4 Preview UI (T117-T133) - ~8 hours
- Developer C: US5 Export Enhancement (T086-T093) + Pipeline Integration (T094-T101) - ~6 hours

**Option 2**: Single developer (sequential)
1. Complete US5 export/integration (T086-T101) - ~8 hours
2. Complete US2 boundary adjustment (T102-T116) - ~8 hours
3. Complete US4 preview UI (T117-T133) - ~10 hours

---

### Phase 7 (US3 Batch) - After All Core Features Complete
**Single developer or small team**:
- Batch logic (T134-T145) - ~6 hours
- Batch UI (T146-T159) - ~6 hours

**Total**: ~12 hours sequential, ~8 hours with 2 developers

---

## Implementation Strategy

### MVP-First Approach (Recommended)

**Week 1 Goal**: Deliver US1 (Single Document Cleanup) as working MVP
- Days 1-2: Phase 1 (Setup) + Phase 2 (Foundational)
- Days 3-5: Phase 3 (US1 Implementation)
- End of Week 1: Users can load PDF, see boundaries, export cleaned PDF ✅

**Week 2 Goal**: Add Accessibility (US5)
- Days 1-3: Phase 4 (US5 OCR Integration + Export Enhancement)
- Days 4-5: Testing and bug fixes
- End of Week 2: Searchable PDFs with OCR ✅

**Week 3 Goal**: Quality & User Control (US2 + US4)
- Days 1-2: Phase 5 (US2 Boundary Adjustment)
- Days 3-5: Phase 6 (US4 Preview & Navigation)
- End of Week 3: Production-ready for single-document workflows ✅

**Week 4 Goal**: Batch Processing & Polish (US3 + Phase 8)
- Days 1-3: Phase 7 (US3 Batch Processing)
- Days 4-5: Phase 8 (Polish, Testing, Packaging)
- End of Week 4: Full feature set ready for release ✅

---

## Task Count Summary

**Total Tasks**: 184  
**Breakdown by Phase**:
- Phase 1 (Setup): 8 tasks
- Phase 2 (Foundational): 14 tasks
- Phase 3 (US1 - Single Document): 48 tasks
- Phase 4 (US5 - OCR/Accessibility): 31 tasks
- Phase 5 (US2 - Boundary Adjustment): 15 tasks
- Phase 6 (US4 - Preview): 17 tasks
- Phase 7 (US3 - Batch Processing): 26 tasks
- Phase 8 (Polish): 25 tasks

**Parallel Tasks**: 42 tasks marked with [P] (can run concurrently)  
**Story-Specific Tasks**: 137 tasks mapped to user stories  
**Foundational Tasks**: 22 tasks (Setup + Foundational phases)

**Estimated Timeline**:
- Single developer: ~120-160 hours (~4 weeks full-time)
- Team of 3: ~50-70 hours (~2 weeks full-time)
- Team of 5: ~35-50 hours (~1.5 weeks full-time)

---

## Validation Checklist

Before marking implementation complete, verify:

- [ ] All FR-001 through FR-056 requirements implemented
- [ ] All SC-001 through SC-022 success criteria validated
- [ ] All 5 user stories independently testable
- [ ] All 7 constitutional principles upheld (determinism, explainability, layout-first, modular, testing, error handling, performance)
- [ ] All 4 pipeline contracts (preprocessing, layout, OCR, export) validated
- [ ] All 8 data model entities implemented with validation rules
- [ ] Performance targets met (<500ms layout, <2s OCR, <500MB memory)
- [ ] Cross-platform testing complete (Windows, macOS, Linux)
- [ ] Accessibility validation complete (NVDA, JAWS, VoiceOver)
- [ ] Packaging and distribution tested (PyInstaller standalone executable)
