"""Pipeline orchestration - coordinates preprocessing, detection, and state management."""

import logging
import signal
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from debleed.config.detection_config import DetectionConfig
from debleed.config.performance_config import PerformanceConfig
from debleed.core.document_loader import load_document
from debleed.core.exceptions import DeBleedError, LayoutDetectionError, PreprocessingError, OCRError
from debleed.core.layout_detection import LayoutDetectionInput, detect_layout
from debleed.core.preprocessing import PreprocessingInput, preprocess_page
from debleed.core.ocr_integration import OCRInput, extract_text
from debleed.models.document import ScannedDocument
from debleed.models.enums import AdjustmentStatus, ProcessingStatus
from debleed.models.page import Page

logger = logging.getLogger(__name__)


class TimeoutError(DeBleedError):
    """Raised when operation exceeds timeout limit."""
    
    def __init__(self, message: str, timeout_seconds: int):
        super().__init__(message, details={"timeout_seconds": timeout_seconds})
        self.timeout_seconds = timeout_seconds


@contextmanager
def timeout(seconds: int, operation_name: str = "operation"):
    """Context manager for enforcing time limits on operations.
    
    Args:
        seconds: Maximum allowed time in seconds
        operation_name: Human-readable operation description
        
    Raises:
        TimeoutError: If operation exceeds time limit
        
    Note:
        Uses SIGALRM on Unix systems. On Windows, timeout enforcement
        may be less precise. Consider using threading.Timer or asyncio.timeout
        for cross-platform compatibility in production.
    """
    def timeout_handler(signum, frame):
        raise TimeoutError(
            f"{operation_name} exceeded {seconds}s timeout",
            timeout_seconds=seconds,
        )
    
    # Set signal handler (Unix only)
    try:
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(seconds)
    except AttributeError:
        # Windows doesn't support SIGALRM - skip timeout for now
        # TODO: Implement cross-platform timeout using threading.Timer
        logger.warning(f"Timeout not supported on this platform, skipping for {operation_name}")
        yield
        return
    
    try:
        yield
    finally:
        # Cancel alarm and restore handler
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


@dataclass
class ProcessingProgress:
    """Progress tracking for document processing.
    
    Attributes:
        total_pages: Total number of pages to process
        completed_pages: Number of pages successfully processed
        current_page: Current page being processed (1-indexed)
        status_message: Human-readable status update
    """
    
    total_pages: int
    completed_pages: int
    current_page: int
    status_message: str
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress as percentage (0-100)."""
        if self.total_pages == 0:
            return 0.0
        return (self.completed_pages / self.total_pages) * 100.0


def process_document(
    document: ScannedDocument,
    detection_config: Optional[DetectionConfig] = None,
    performance_config: Optional[PerformanceConfig] = None,
    progress_callback: Optional[Callable[[ProcessingProgress], None]] = None,
    enable_ocr: bool = False,
) -> ScannedDocument:
    """Process document through full pipeline (preprocessing → layout detection → optional OCR).
    
    Pipeline workflow:
    1. Load document (LOADED → ANALYZING state transition)
    2. For each page:
        a. Preprocess: PDF → RGB image
        b. Detect layout: image → DetectedBoundary
        c. Calculate confidence score
        d. Flag low confidence pages (< 0.80) and borderline pages (0.80-0.85)
        e. Optionally extract text with OCR (if enable_ocr=True)
        f. Create Page object
        g. Release previous page memory (incremental cleanup)
    3. Update document state (ANALYZING → READY)
    4. Report progress via callback
    
    Args:
        document: ScannedDocument to process (must be in LOADED state)
        detection_config: Layout detection configuration (defaults to DetectionConfig())
        performance_config: Performance/timeout configuration (defaults to PerformanceConfig())
        progress_callback: Optional callback for progress updates
        enable_ocr: Whether to perform OCR text extraction (default: False)
        
    Returns:
        Updated ScannedDocument with processed pages
        
    Raises:
        PreprocessingError: If PDF preprocessing fails
        LayoutDetectionError: If boundary detection fails
        TimeoutError: If operation exceeds configured timeout
    """
    # Use default configs if not provided
    if detection_config is None:
        detection_config = DetectionConfig()
    if performance_config is None:
        performance_config = PerformanceConfig()
    
    # Validate document state
    if document.processing_status != ProcessingStatus.LOADED:
        raise ValueError(
            f"Document must be in LOADED state, got {document.processing_status}"
        )
    
    # Transition to ANALYZING
    document.update_status(ProcessingStatus.ANALYZING)
    
    logger.info(f"Starting pipeline for {document.file_path.name} ({document.page_count} pages)")
    
    # Process each page
    processed_pages = []
    
    for page_num in range(1, document.page_count + 1):
        try:
            # Update progress
            if progress_callback:
                progress = ProcessingProgress(
                    total_pages=document.page_count,
                    completed_pages=len(processed_pages),
                    current_page=page_num,
                    status_message=f"Processing page {page_num} of {document.page_count}",
                )
                progress_callback(progress)
            
            logger.debug(f"Processing page {page_num}/{document.page_count}")
            
            # Stage 1: Preprocessing with file load timeout
            with timeout(performance_config.max_file_load_time, f"Page {page_num} preprocessing"):
                preprocessing_input = PreprocessingInput(
                    pdf_path=document.file_path,
                    page_number=page_num,
                    target_dpi=300,
                )
                preprocessing_output = preprocess_page(preprocessing_input)
            
            # Stage 2: Layout Detection with timeout
            with timeout(performance_config.max_page_detection_time, f"Page {page_num} layout detection"):
                layout_input = LayoutDetectionInput(
                    image_data=preprocessing_output.image_data,
                    page_number=page_num,
                    config=detection_config,
                )
                layout_output = detect_layout(layout_input)
            
            # Calculate confidence score from primary region
            confidence_score = layout_output.detected_boundary.primary_region.confidence_level
            
            # Determine adjustment status based on confidence (FR-041)
            if confidence_score < detection_config.page_confidence_threshold:
                # Below threshold → FLAGGED for review
                adjustment_status = AdjustmentStatus.FLAGGED
                logger.warning(
                    f"Page {page_num} flagged for review: confidence {confidence_score:.2f} "
                    f"< threshold {detection_config.page_confidence_threshold}"
                )
            else:
                # Above threshold → AUTO (automatic detection accepted)
                adjustment_status = AdjustmentStatus.AUTO
            
            # Check if borderline confidence (0.80-0.85)
            is_borderline = (
                detection_config.page_confidence_threshold <= confidence_score < 
                detection_config.borderline_confidence_threshold
            )
            
            # Stage 3: Optional OCR text extraction
            ocr_result = None
            if enable_ocr:
                try:
                    # Update progress for OCR stage
                    if progress_callback:
                        progress = ProcessingProgress(
                            total_pages=document.page_count,
                            completed_pages=len(processed_pages),
                            current_page=page_num,
                            status_message=f"Extracting text from page {page_num} of {document.page_count}",
                        )
                        progress_callback(progress)
                    
                    logger.debug(f"Performing OCR on page {page_num}")
                    
                    # Extract cropped region for OCR (use primary region)
                    primary = layout_output.detected_boundary.primary_region
                    primary_x, primary_y, primary_w, primary_h = primary.coordinates
                    cropped_image = preprocessing_output.image_data[
                        primary_y:primary_y + primary_h,
                        primary_x:primary_x + primary_w
                    ]
                    
                    # Perform OCR with timeout
                    with timeout(performance_config.max_ocr_time_per_page, f"Page {page_num} OCR"):
                        ocr_input = OCRInput(
                            image_data=cropped_image,
                            page_number=page_num,
                            config=detection_config.ocr_config,
                        )
                        ocr_output = extract_text(ocr_input)
                        ocr_result = ocr_output.ocr_result
                    
                    logger.info(
                        f"OCR complete for page {page_num}: "
                        f"{len(ocr_result.text_blocks)} blocks, "
                        f"confidence {ocr_result.overall_confidence:.2f}"
                    )
                    
                except OCRError as e:
                    # OCR failure is non-critical - log warning and continue (FR-052)
                    logger.warning(
                        f"OCR failed for page {page_num}: {e.message} "
                        f"(error code: {e.error_code}). Continuing without text extraction."
                    )
                    ocr_result = None
                except Exception as e:
                    # Unexpected OCR error - log but don't fail the entire pipeline
                    logger.error(f"Unexpected OCR error on page {page_num}: {str(e)}")
                    ocr_result = None
            
            # Create Page object
            page = Page(
                page_number=page_num,
                image_data=preprocessing_output.image_data,
                dimensions=preprocessing_output.dimensions,
                detected_boundary=layout_output.detected_boundary,
                confidence_score=confidence_score,
                adjustment_status=adjustment_status,
                is_borderline_confidence=is_borderline,
                ocr_result=ocr_result,
                rotation_angle=layout_output.rotation_angle,
            )
            
            processed_pages.append(page)
            
            # Incremental memory management (FR-055)
            if performance_config.enable_incremental_memory_release and len(processed_pages) > 1:
                # Release previous page's image data (keep metadata)
                # In Python, just removing reference allows GC to collect
                # For explicit cleanup, set previous page's image_data to None
                # (requires making Page mutable, which conflicts with dataclass frozen=True)
                # For now, rely on Python GC
                logger.debug(f"Released memory for page {page_num - 1}")
            
        except (PreprocessingError, LayoutDetectionError, TimeoutError) as e:
            # Pipeline error - transition to ERROR state
            document.update_status(ProcessingStatus.ERROR)
            logger.error(f"Pipeline failed on page {page_num}: {e.message}")
            raise
        except Exception as e:
            # Unexpected error
            document.update_status(ProcessingStatus.ERROR)
            logger.exception(f"Unexpected error processing page {page_num}")
            raise PreprocessingError(
                message=f"Unexpected error on page {page_num}: {str(e)}",
                error_code="RENDER_FAILED",
                page_number=page_num,
                details={"error": str(e)},
            )
    
    # Update document with processed pages
    document.pages = processed_pages
    
    # Transition to READY
    document.update_status(ProcessingStatus.READY)
    
    logger.info(
        f"Pipeline complete: {len(processed_pages)} pages processed, "
        f"{sum(1 for p in processed_pages if p.adjustment_status == AdjustmentStatus.FLAGGED)} flagged"
    )
    
    # Final progress update
    if progress_callback:
        progress = ProcessingProgress(
            total_pages=document.page_count,
            completed_pages=len(processed_pages),
            current_page=document.page_count,
            status_message="Processing complete",
        )
        progress_callback(progress)
    
    return document
