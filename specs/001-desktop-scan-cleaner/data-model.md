# Data Model: Desktop Scan Cleaner Application

**Feature**: 001-desktop-scan-cleaner  
**Date**: 2026-01-17  
**Source**: Entities from [spec.md](spec.md)

## Core Entities

### 1. ScannedDocument

**Purpose**: Represents an input PDF file containing imperfect scans

**Attributes**:
- `file_path: Path` - Absolute path to source PDF file
- `page_count: int` - Total number of pages in document
- `processing_status: ProcessingStatus` - Current state (LOADED, ANALYZING, READY, EXPORTING, COMPLETE, ERROR)
- `pages: list[Page]` - Collection of pages in reading order
- `created_at: datetime` - Timestamp when document was loaded
- `file_size_bytes: int` - Size of source file for memory estimation

**Validation Rules**:
- `file_path` must exist and be readable
- `page_count` must be > 0
- `pages` length must equal `page_count`

**State Transitions**:
- LOADED → ANALYZING (when layout detection starts)
- ANALYZING → READY (when all pages analyzed)
- READY → EXPORTING (when user initiates export)
- EXPORTING → COMPLETE (when export finishes)
- Any state → ERROR (on failure)

---

### 2. Page

**Purpose**: Individual page within a scanned document

**Attributes**:
- `page_number: int` - 1-based page index in document
- `image_data: ndarray` - NumPy array containing rendered page image (from PyMuPDF)
- `dimensions: tuple[int, int]` - (width, height) in pixels
- `detected_boundary: DetectedBoundary | None` - Identified primary page region (None if not yet detected)
- `confidence_score: float` - Overall confidence in boundary detection (0.0-1.0)
- `adjustment_status: AdjustmentStatus` - AUTO, MANUAL, FLAGGED
- `preview_thumbnail: ndarray | None` - Smaller version for grid view (lazy-loaded)
- `ocr_result: OCRResult | None` - Extracted text (None if OCR not yet performed)
- `rotation_angle: int` - Detected rotation in degrees (0, 90, 180, 270)

**Validation Rules**:
- `page_number` must be >= 1
- `confidence_score` must be in range [0.0, 1.0]
- If `confidence_score < 0.80`, `adjustment_status` should be FLAGGED
- `rotation_angle` must be in {0, 90, 180, 270} for auto-corrected; other angles flag for review

**Derived Properties**:
- `needs_review: bool` - True if confidence < 0.80 or adjustment_status == FLAGGED
- `has_manual_adjustment: bool` - True if adjustment_status == MANUAL

---

### 3. PrimaryPageRegion

**Purpose**: Geometric region representing intended page content

**Attributes**:
- `coordinates: tuple[int, int, int, int]` - (x, y, width, height) in pixels, relative to Page.image_data
- `confidence_level: float` - Confidence in this region being correct (0.0-1.0)
- `area_percentage: float` - Percentage of total page area occupied by this region
- `detection_method: str` - Method used ("contour_analysis", "connected_components", "manual")

**Validation Rules**:
- `coordinates` must be within Page.dimensions bounds
- `confidence_level` must be in range [0.0, 1.0]
- `area_percentage` must be in range (0.0, 100.0]
- If `detection_method == "manual"`, confidence_level should be 1.0

**Derived Properties**:
- `bounding_box: tuple[tuple[int, int], ...]` - Four corner points for visualization
- `cropped_region: ndarray` - Extract region from parent Page.image_data

---

### 4. DetectedBoundary

**Purpose**: Calculated coordinates defining the primary page region with metadata

**Attributes**:
- `primary_region: PrimaryPageRegion` - The main content region
- `secondary_regions: list[PrimaryPageRegion]` - Other detected regions (gutters, bleed, adjacent pages) - for debugging
- `detection_timestamp: datetime` - When detection was performed
- `detection_config: dict` - Configuration used (thresholds, parameters) for reproducibility

**Validation Rules**:
- `primary_region` must exist
- `primary_region.confidence_level` must be highest among all regions
- `detection_config` must include all thresholds used

**Derived Properties**:
- `is_confident: bool` - True if primary_region.confidence_level >= 0.80
- `flagged_for_review: bool` - True if not is_confident

---

### 5. OCRResult

**Purpose**: Extracted text from a page region

**Attributes**:
- `text_content: str` - Full extracted text
- `text_blocks: list[TextBlock]` - Structural breakdown of text into paragraphs/regions
- `overall_confidence: float` - Average confidence across all text blocks (0.0-1.0)
- `detected_language: str` - ISO 639-1 language code (e.g., "en", "es")
- `reading_order: list[int]` - Indices of text_blocks in correct reading order
- `flagged_words: list[tuple[str, float]]` - Words with confidence < 0.75 and their scores
- `processing_time_seconds: float` - Time taken for OCR execution

**Validation Rules**:
- `overall_confidence` must be in range [0.0, 1.0]
- `reading_order` length must equal `text_blocks` length
- All indices in `reading_order` must be valid indices into `text_blocks`
- `flagged_words` should only contain words with confidence < 0.75

**Derived Properties**:
- `plain_text: str` - text_content with [?] markers added after flagged words
- `word_count: int` - Total number of words in text_content
- `flagged_word_count: int` - Length of flagged_words list

---

### 6. TextBlock

**Purpose**: Structural unit of extracted text (paragraph or text region)

**Attributes**:
- `content: str` - Text within this block
- `position: tuple[int, int, int, int]` - (x, y, width, height) relative to page
- `reading_order_index: int` - Position in reading sequence
- `confidence: float` - OCR confidence for this block (0.0-1.0)
- `is_multi_column_part: bool` - True if part of multi-column layout

**Validation Rules**:
- `confidence` must be in range [0.0, 1.0]
- `reading_order_index` must be >= 0
- `position` must be within page bounds

**Derived Properties**:
- `word_count: int` - Number of words in content
- `is_low_confidence: bool` - True if confidence < 0.75

---

### 7. ExportJob

**Purpose**: Processing task for generating cleaned PDF and/or text output

**Attributes**:
- `job_id: str` - Unique identifier (UUID)
- `source_document: ScannedDocument` - Reference to input document
- `selected_pages: list[int]` - Page numbers to include in export (empty = all pages)
- `output_format: ExportFormat` - SEARCHABLE_PDF, PDF_AND_TEXT, TEXT_ONLY
- `output_path: Path` - Destination file path
- `ocr_enabled: bool` - Whether to perform OCR (always True for formats requiring text)
- `status: JobStatus` - QUEUED, PROCESSING, COMPLETE, FAILED
- `progress_percentage: float` - Completion progress (0.0-100.0)
- `error_message: str | None` - Error details if status == FAILED
- `created_at: datetime` - When job was created
- `completed_at: datetime | None` - When job finished (success or failure)

**Validation Rules**:
- `progress_percentage` must be in range [0.0, 100.0]
- If `status == COMPLETE`, `completed_at` must be set and `progress_percentage == 100.0`
- If `status == FAILED`, `error_message` must be set
- `selected_pages` must contain valid page numbers from source_document

**Derived Properties**:
- `elapsed_time: timedelta` - created_at to (completed_at or now)
- `is_complete: bool` - status in {COMPLETE, FAILED}
- `requires_ocr: bool` - output_format != ExportFormat.PDF_ONLY (if we add that option)

---

### 8. BatchQueue

**Purpose**: Collection of export jobs for multi-document processing

**Attributes**:
- `queue_id: str` - Unique identifier (UUID)
- `export_jobs: list[ExportJob]` - Jobs in processing order
- `current_job_index: int` - Index of currently processing job
- `overall_progress: float` - Percentage of all jobs complete (0.0-100.0)
- `successful_exports: int` - Count of jobs with status == COMPLETE
- `failed_exports: int` - Count of jobs with status == FAILED
- `flagged_for_review: int` - Count of documents with pages needing review
- `created_at: datetime` - When batch was created
- `completed_at: datetime | None` - When all jobs finished

**Validation Rules**:
- `overall_progress` must be in range [0.0, 100.0]
- `current_job_index` must be valid index or -1 if no job active
- `successful_exports + failed_exports` must be <= len(export_jobs)

**Derived Properties**:
- `total_jobs: int` - len(export_jobs)
- `remaining_jobs: int` - total_jobs - (successful_exports + failed_exports)
- `is_complete: bool` - current_job_index >= total_jobs or all jobs finished
- `success_rate: float` - successful_exports / total_jobs if total_jobs > 0

---

## Enumerations

### ProcessingStatus
- LOADED - Document loaded into application
- ANALYZING - Layout detection in progress
- READY - Analysis complete, ready for export
- EXPORTING - Export operation in progress
- COMPLETE - Export finished successfully
- ERROR - Processing failed

### AdjustmentStatus
- AUTO - Automatic detection, not modified by user
- MANUAL - User manually adjusted boundaries
- FLAGGED - Automatic detection had low confidence

### ExportFormat
- SEARCHABLE_PDF - PDF with embedded OCR text layer
- PDF_AND_TEXT - Searchable PDF + separate .txt file
- TEXT_ONLY - Only .txt file output

### JobStatus
- QUEUED - Waiting to be processed
- PROCESSING - Currently being processed
- COMPLETE - Successfully finished
- FAILED - Encountered error

---

## Relationships

```
ScannedDocument (1) ──< (N) Page
Page (1) ──< (0..1) DetectedBoundary
DetectedBoundary (1) ──< (1) PrimaryPageRegion
DetectedBoundary (1) ──< (N) PrimaryPageRegion (secondary_regions)
Page (1) ──< (0..1) OCRResult
OCRResult (1) ──< (N) TextBlock
ExportJob (1) ──< (1) ScannedDocument
BatchQueue (1) ──< (N) ExportJob
```

**Cardinality Notes**:
- A Page has 0 or 1 DetectedBoundary (None until detection runs)
- A Page has 0 or 1 OCRResult (None until OCR runs)
- A DetectedBoundary has exactly 1 primary region and 0+ secondary regions
- An OCRResult has 1+ TextBlocks (at least one paragraph)

---

## Pipeline Data Flow

```
Input: PDF File
    ↓
ScannedDocument (LOADED status)
    ↓
[For each Page]
    ↓
Page (image_data loaded from PDF)
    ↓
[Layout Detection]
    ↓
DetectedBoundary + PrimaryPageRegion (confidence calculated)
    ↓
Page.detected_boundary set, confidence_score set
    ↓
[If confidence < 0.80: adjustment_status = FLAGGED]
[If user adjusts: adjustment_status = MANUAL, confidence = 1.0]
    ↓
ScannedDocument (READY status)
    ↓
[User initiates export]
    ↓
ExportJob created
    ↓
[For each Page in selected_pages]
    ↓
[OCR on Page.detected_boundary.primary_region]
    ↓
OCRResult + TextBlocks (reading_order determined)
    ↓
Page.ocr_result set
    ↓
[Export to PDF/Text based on ExportFormat]
    ↓
ExportJob (COMPLETE status)
```

---

## Configuration Data Model

### DetectionConfig
- `page_confidence_threshold: float = 0.80` - Threshold for flagging pages
- `ocr_confidence_threshold: float = 0.75` - Threshold for flagging words
- `rotation_auto_correct_angles: list[int] = [90, 180, 270]` - Auto-correctable rotations
- `max_secondary_regions: int = 5` - Maximum secondary regions to track for debugging

### PerformanceConfig
- `max_memory_mb: int = 500` - Memory limit for processing
- `max_page_detection_time_ms: int = 500` - Per-page detection timeout
- `max_ocr_time_per_page_s: int = 2` - Per-page OCR timeout
- `preview_thumbnail_size: tuple[int, int] = (200, 200)` - Thumbnail dimensions

### ExportConfig
- `default_output_suffix: str = "_cleaned"` - Suffix for exported filenames
- `default_export_format: ExportFormat = ExportFormat.SEARCHABLE_PDF`
- `pdf_compression_quality: int = 85` - JPEG quality for embedded images (1-100)
- `preserve_original_dpi: bool = True` - Maintain source PDF resolution

---

## Type Annotations Summary

All entities use Python type hints for contracts:

```python
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from datetime import datetime
import numpy as np
from numpy.typing import NDArray

# Example entity with full type annotations
@dataclass
class Page:
    page_number: int
    image_data: NDArray[np.uint8]
    dimensions: tuple[int, int]
    detected_boundary: DetectedBoundary | None = None
    confidence_score: float = 0.0
    adjustment_status: AdjustmentStatus = AdjustmentStatus.AUTO
    preview_thumbnail: NDArray[np.uint8] | None = None
    ocr_result: OCRResult | None = None
    rotation_angle: int = 0
    
    @property
    def needs_review(self) -> bool:
        return self.confidence_score < 0.80 or self.adjustment_status == AdjustmentStatus.FLAGGED
```

This model supports the Constitution requirement for type safety and enables static analysis with mypy.
