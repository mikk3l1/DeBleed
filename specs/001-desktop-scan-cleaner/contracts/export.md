# Contract: Export Stage

**Stage**: PDF/Text Export  
**Purpose**: Generate cleaned PDFs with optional OCR text layer and plain text files  
**Constitutional Alignment**: Deterministic output, Explicit failure handling

---

## Interface

### Input Schema

```python
@dataclass
class ExportInput:
    document: ScannedDocument  # Source document with processed pages
    selected_pages: list[int]  # Page numbers to export (empty = all)
    output_format: ExportFormat  # SEARCHABLE_PDF, PDF_AND_TEXT, TEXT_ONLY
    output_path: Path  # Destination file path
    config: ExportConfig  # PDF settings (compression, DPI, etc.)
```

**Validation**:
- `document.processing_status == ProcessingStatus.READY` (layout detection complete)
- `selected_pages` must be valid page numbers or empty
- `output_path` parent directory must exist and be writable
- If `output_format == SEARCHABLE_PDF`, all selected pages must have `ocr_result != None`

---

### Output Schema

```python
@dataclass
class ExportOutput:
    pdf_path: Path | None  # Path to generated PDF (None if TEXT_ONLY)
    text_path: Path | None  # Path to generated .txt file (None if SEARCHABLE_PDF only)
    exported_page_count: int  # Number of pages exported
    file_size_bytes: int  # Total size of exported files
    processing_time_ms: int  # Time for export operation
    warnings: list[str]  # Non-fatal issues (e.g., "Page 3 had low OCR confidence")
```

**Guarantees**:
- At least one of `pdf_path` or `text_path` is not None
- `exported_page_count == len(selected_pages)` or `== document.page_count` if all pages
- Files at `pdf_path` and `text_path` are valid and complete

---

### Error Schema

```python
class ExportError(Exception):
    """Raised when export cannot complete"""
    
    error_code: str  # One of: INVALID_OUTPUT_PATH, OCR_MISSING, WRITE_FAILED, DISK_FULL
    page_number: int | None  # Page where error occurred (if applicable)
    details: str
```

**Error Codes**:
- `INVALID_OUTPUT_PATH`: Output directory doesn't exist or isn't writable
- `OCR_MISSING`: SEARCHABLE_PDF requested but OCR not performed on some pages
- `WRITE_FAILED`: I/O error during file writing
- `DISK_FULL`: Insufficient disk space for output

---

## Functional Requirements

### FR-EXP-001: PDF Page Creation
**Requirement**: Create new PDF with cropped pages at original DPI  
**Input**: List of Page entities with detected_boundary  
**Output**: PDF file with one page per input page  
**Success Criteria**: Each PDF page shows only primary_region content  
**Error Handling**: Raise `WRITE_FAILED` if PDF creation fails

### FR-EXP-002: OCR Text Layer Embedding
**Requirement**: Embed invisible text layer for searchability  
**Input**: Page.ocr_result for each page  
**Output**: PDF with text layer aligned to visual content  
**Success Criteria**: PDF text search finds words from OCR  
**Error Handling**: Raise `OCR_MISSING` if ocr_result is None

### FR-EXP-003: Plain Text Export
**Requirement**: Generate .txt file with extracted text  
**Input**: OCROutput.text_content for selected pages  
**Output**: Text file with pages separated by "--- Page N ---"  
**Success Criteria**: Text file readable in any text editor  
**Error Handling**: Raise `WRITE_FAILED` if file creation fails

### FR-EXP-004: Filename Generation
**Requirement**: Generate output filename by appending "_cleaned" to source  
**Input**: Source PDF path "/path/scanned.pdf"  
**Output**: "/path/scanned_cleaned.pdf" (same directory)  
**Success Criteria**: Filename never overwrites source  
**Error Handling**: Raise `INVALID_OUTPUT_PATH` if directory not writable

### FR-EXP-005: Compression
**Requirement**: Apply JPEG compression to images in PDF  
**Input**: ExportConfig.pdf_compression_quality (1-100)  
**Output**: Smaller PDF file without significant quality loss  
**Success Criteria**: File size reduced while preserving readability  
**Error Handling**: N/A (compression always succeeds)

### FR-EXP-006: Progress Tracking
**Requirement**: Report export progress for UI updates  
**Input**: ExportJob.progress_percentage  
**Output**: Float in [0.0, 100.0] updated during export  
**Success Criteria**: Progress reaches 100.0 when complete  
**Error Handling**: N/A (progress tracking is best-effort)

### FR-EXP-007: Deterministic Export
**Requirement**: Same input produces byte-identical output  
**Input**: Identical ExportInput  
**Output**: Byte-for-byte identical PDF (excluding metadata timestamps)  
**Success Criteria**: PDF content streams are deterministic  
**Error Handling**: N/A (determinism via library config)

---

## Performance Requirements

### PERF-EXP-001: Export Speed
**Limit**: < 1 second per page for PDF generation  
**Measurement**: ExportOutput.processing_time_ms / exported_page_count  
**Mitigation**: Use PyMuPDF for fast PDF writing

### PERF-EXP-002: Memory Usage
**Limit**: Export process < 300MB total memory  
**Measurement**: System memory monitoring  
**Mitigation**: Process pages sequentially, not all in memory

---

## Testing Requirements

### Unit Tests

1. **test_single_page_export**: Export 1-page PDF, verify output exists
2. **test_multi_page_export**: Export 10-page PDF, verify page count
3. **test_searchable_pdf**: Export with OCR, verify text layer searchable
4. **test_pdf_and_text**: Verify both .pdf and .txt files created
5. **test_text_only**: Verify only .txt file created
6. **test_filename_generation**: Verify "_cleaned" suffix added correctly
7. **test_compression**: Verify compressed PDF smaller than uncompressed
8. **test_missing_ocr**: Request SEARCHABLE_PDF without OCR, expect OCR_MISSING
9. **test_invalid_output_path**: Write to non-existent directory, expect INVALID_OUTPUT_PATH
10. **test_deterministic_export**: Export twice, verify byte-identical PDFs (ignoring metadata)

### Integration Tests

1. **test_full_pipeline_export**: PDF → preprocess → layout → OCR → export
2. **test_batch_export**: Export 100 documents sequentially

### Contract Tests

1. **test_output_schema_compliance**: Every successful export produces valid ExportOutput
2. **test_file_exists**: Verify pdf_path and text_path point to real files
3. **test_progress_range**: progress_percentage always in [0.0, 100.0]

---

## Dependencies

**Required Libraries**:
- `pymupdf (fitz)`: PDF creation and manipulation
- `pillow`: Image format conversions (if needed)
- `pathlib`: Path handling

**Depends On**:
- Layout Detection (uses detected_boundary for cropping)
- OCR Integration (uses ocr_result for text layer)
- Preprocessing (indirectly, via layout)

**No Dependencies On**:
- GUI components (export is headless)

---

## Configuration

```python
@dataclass
class ExportConfig:
    default_output_suffix: str = "_cleaned"  # Appended to source filename
    pdf_compression_quality: int = 85  # JPEG quality (1-100)
    preserve_original_dpi: bool = True  # Maintain source DPI
    embed_metadata: bool = True  # Include creator, creation date
    text_file_encoding: str = "utf-8"  # Encoding for .txt files
    page_separator: str = "\n\n--- Page {page_num} ---\n\n"  # For multi-page text
```

---

## Algorithm Specification

### PDF Creation with OCR Layer

**Steps**:
1. Create new PyMuPDF document: `pdf = fitz.open()`
2. For each page in selected_pages:
   a. Crop original page to primary_region coordinates
   b. Create new PDF page with cropped image
   c. If OCR available, add invisible text layer:
      ```python
      for text_block in page.ocr_result.text_blocks:
          pdf_page.insert_text(
              point=(text_block.position[0], text_block.position[1]),
              text=text_block.content,
              fontsize=calculate_font_size(text_block),
              render_mode=3  # Invisible text
          )
      ```
   d. Update progress: `progress = (i / total_pages) * 100`
3. Save PDF: `pdf.save(output_path, deflate=True, garbage=4)`
4. Close document: `pdf.close()`

**Determinism Notes**:
- Disable PDF metadata timestamps: `pdf.set_metadata({"creationDate": "", "modDate": ""})`
- Use fixed compression settings
- Process pages in consistent order

### Text File Generation

**Steps**:
1. Open output file: `with open(text_path, 'w', encoding='utf-8') as f:`
2. For each page in selected_pages:
   a. Write page separator: `f.write(f"\n\n--- Page {page_num} ---\n\n")`
   b. Write OCR text content: `f.write(page.ocr_result.text_content)`
   c. If flagged words exist, append summary:
      ```
      \n[Low-confidence words: word1[?], word2[?], ...]
      ```
3. Close file

---

## Example Usage

```python
from export import export_document, ExportInput, ExportConfig, ExportFormat
from pathlib import Path

# Prepare export
document = load_scanned_document(Path("/path/to/scanned.pdf"))
# ... run preprocessing, layout, OCR ...

export_config = ExportConfig(
    pdf_compression_quality=85,
    preserve_original_dpi=True
)

export_input = ExportInput(
    document=document,
    selected_pages=[],  # Export all pages
    output_format=ExportFormat.SEARCHABLE_PDF,
    output_path=Path("/path/to/scanned_cleaned.pdf"),
    config=export_config
)

try:
    output = export_document(export_input)
    
    print(f"✓ Exported {output.exported_page_count} pages")
    print(f"  PDF: {output.pdf_path} ({output.file_size_bytes / 1024:.1f} KB)")
    
    if output.warnings:
        print(f"⚠ Warnings:")
        for warning in output.warnings:
            print(f"  - {warning}")
    
except ExportError as e:
    print(f"Export failed: {e.error_code} - {e.details}")
```

---

## Batch Export

```python
from export import BatchQueue, ExportJob

# Create batch
batch = BatchQueue(
    queue_id=str(uuid.uuid4()),
    export_jobs=[
        ExportJob(source_document=doc1, ...),
        ExportJob(source_document=doc2, ...),
        # ... more jobs
    ]
)

# Process batch
for i, job in enumerate(batch.export_jobs):
    batch.current_job_index = i
    try:
        output = export_document(job)
        job.status = JobStatus.COMPLETE
        batch.successful_exports += 1
    except ExportError as e:
        job.status = JobStatus.FAILED
        job.error_message = str(e)
        batch.failed_exports += 1
    
    batch.overall_progress = ((i + 1) / batch.total_jobs) * 100

print(f"Batch complete: {batch.successful_exports}/{batch.total_jobs} successful")
```

---

## Traceability

**Implements Functional Requirements**:
- FR-004 (export cleaned pages to new PDF) - core PDF creation
- FR-007 (generate searchable PDFs) - OCR text layer embedding
- FR-010 (same-directory export) - filename generation logic
- FR-011 (batch processing) - BatchQueue support
- FR-012 (report batch progress) - progress_percentage tracking
- FR-014 (provide plain text option) - text file generation
- FR-023 (embed text layer in PDF) - invisible text insertion
- FR-025 (export plain text) - TEXT_ONLY format

**Supports Constitution Principles**:
- **Correctness & Determinism**: Byte-identical outputs (excluding metadata)
- **Explicit Failure Handling**: Typed error codes for all failure modes
- **Performance & Scalability**: Sequential page processing, memory limits
- **Modular Architecture**: Clear separation from OCR and layout stages

**Referenced By**:
- [data-model.md](../data-model.md) - ExportJob matches input schema
- [spec.md](../spec.md) - Fulfills export-related user stories
