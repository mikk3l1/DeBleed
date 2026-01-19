"""PDF export stage - generate cleaned PDFs with cropped pages."""

import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
import numpy as np
from PIL import Image

from debleed.config.export_config import ExportConfig
from debleed.core.exceptions import ExportError
from debleed.models.document import ScannedDocument
from debleed.models.enums import ProcessingStatus


@dataclass
class ExportInput:
    """Input for export stage.
    
    Attributes:
        document: ScannedDocument to export (must be in READY or COMPLETE state)
        output_path: Destination path for cleaned PDF (None = auto-generate)
        selected_pages: Page numbers to export (empty = all pages)
        config: Export configuration (compression, suffix, etc.)
    """
    
    document: ScannedDocument
    output_path: Optional[Path] = None
    selected_pages: list[int] = field(default_factory=list)
    config: ExportConfig = field(default_factory=ExportConfig)
    
    def __post_init__(self) -> None:
        """Validate export input."""
        if self.document.processing_status not in (ProcessingStatus.READY, ProcessingStatus.COMPLETE):
            raise ValueError(
                f"Document must be in READY or COMPLETE state, got {self.document.processing_status}"
            )
        
        # Validate selected_pages if provided
        if self.selected_pages:
            for page_num in self.selected_pages:
                if page_num < 1 or page_num > self.document.page_count:
                    raise ValueError(
                        f"Invalid page number {page_num} (document has {self.document.page_count} pages)"
                    )


@dataclass
class ExportOutput:
    """Output from export stage.
    
    Attributes:
        output_path: Path to generated PDF
        file_size_bytes: Size of exported PDF in bytes
        pages_exported: Number of pages included in export
        export_time_seconds: Time taken to generate PDF
    """
    
    output_path: Path
    file_size_bytes: int
    pages_exported: int
    export_time_seconds: float


def check_disk_space(output_path: Path, required_bytes: int) -> bool:
    """Check if sufficient disk space is available.
    
    Args:
        output_path: Destination path for file
        required_bytes: Minimum required space in bytes
        
    Returns:
        True if sufficient space available, False otherwise
    """
    try:
        stat = shutil.disk_usage(output_path.parent)
        return stat.free >= required_bytes
    except Exception:
        # If we can't check, assume sufficient space (fail later if not)
        return True


def export_document(input_data: ExportInput) -> ExportOutput:
    """Export cleaned PDF with cropped pages.
    
    Export pipeline:
    1. Validate output path or auto-generate filename
    2. Check disk space (require 2x estimated size per FR-051)
    3. Create new PDF document
    4. For each selected page:
        a. Crop image to primary_region coordinates
        b. Compress with configured JPEG quality
        c. Add as PDF page
    5. Save PDF with deterministic generation (no timestamps if configured)
    6. Transition document state (READY → EXPORTING → COMPLETE)
    
    Args:
        input_data: Export configuration
        
    Returns:
        ExportOutput with file path and metadata
        
    Raises:
        ExportError: If path is invalid, disk full, or write fails
    """
    start_time = datetime.now()
    
    # Determine output path
    if input_data.output_path is None:
        # Auto-generate filename (FR-015: same directory + "_cleaned" suffix)
        output_path = input_data.document.file_path.parent / (
            input_data.document.file_path.stem + 
            input_data.config.default_suffix + 
            ".pdf"
        )
    else:
        output_path = input_data.output_path
    
    # Validate output path
    if output_path.exists() and not output_path.is_file():
        raise ExportError(
            message=f"Output path exists but is not a file: {output_path}",
            error_code="INVALID_OUTPUT_PATH",
            output_path=str(output_path),
        )
    
    # Ensure parent directory exists
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise ExportError(
            message=f"Cannot create output directory: {output_path.parent}",
            error_code="PERMISSION_DENIED",
            output_path=str(output_path),
            details={"error": str(e)},
        )
    
    # Determine pages to export
    if input_data.selected_pages:
        page_numbers = input_data.selected_pages
    else:
        page_numbers = list(range(1, input_data.document.page_count + 1))
    
    # Estimate output size (rough: 100KB per page)
    estimated_size = len(page_numbers) * 100 * 1024
    
    # Check disk space (require 2x estimated size per FR-051)
    required_space = estimated_size * 2
    if not check_disk_space(output_path, required_space):
        raise ExportError(
            message=f"Insufficient disk space. Need ~{required_space / (1024**2):.1f} MB",
            error_code="DISK_FULL",
            output_path=str(output_path),
            details={"required_bytes": required_space},
        )
    
    # Transition to EXPORTING
    input_data.document.update_status(ProcessingStatus.EXPORTING)
    
    try:
        # Create new PDF
        pdf_doc = fitz.open()
        
        # Process each selected page
        for page_num in page_numbers:
            # Get Page object (0-indexed in list, 1-indexed page_number)
            page = input_data.document.pages[page_num - 1]
            
            # Crop image to primary region
            primary = page.detected_boundary.primary_region
            primary_x, primary_y, primary_w, primary_h = primary.coordinates
            cropped_image = page.image_data[
                primary_y:primary_y + primary_h,
                primary_x:primary_x + primary_w,
            ]
            
            # Convert numpy array to PIL Image for JPEG compression
            pil_image = Image.fromarray(cropped_image)
            
            # Save to temporary bytes buffer with compression
            import io
            img_buffer = io.BytesIO()
            pil_image.save(
                img_buffer,
                format="JPEG",
                quality=input_data.config.compression_quality,
                optimize=True,
            )
            img_bytes = img_buffer.getvalue()
            
            # Create PDF page from image
            img_doc = fitz.open("jpeg", img_bytes)
            pdf_page = pdf_doc.new_page(
                width=primary_w,
                height=primary_h,
            )
            pdf_page.insert_image(
                pdf_page.rect,
                stream=img_bytes,
            )
            img_doc.close()
        
        # Save PDF
        try:
            # Deterministic generation: disable metadata timestamps (FR-015, contracts/export.md)
            if input_data.config.deterministic_generation:
                # Clear metadata
                pdf_doc.set_metadata({})
            
            # Preserve metadata from source if configured
            if input_data.config.preserve_metadata:
                # TODO: Copy metadata from source PDF
                pass
            
            pdf_doc.save(
                str(output_path),
                deflate=True,  # Enable compression
                clean=True,  # Remove redundant objects
            )
        except PermissionError as e:
            raise ExportError(
                message=f"No write permission to {output_path}",
                error_code="PERMISSION_DENIED",
                output_path=str(output_path),
                details={"error": str(e)},
            )
        except OSError as e:
            # Catch disk full errors
            if "No space left on device" in str(e) or e.errno == 28:
                raise ExportError(
                    message="Disk full during export",
                    error_code="DISK_FULL",
                    output_path=str(output_path),
                    details={"error": str(e)},
                )
            else:
                raise ExportError(
                    message=f"Failed to write PDF: {str(e)}",
                    error_code="WRITE_FAILED",
                    output_path=str(output_path),
                    details={"error": str(e)},
                )
        finally:
            pdf_doc.close()
        
        # Get file size
        file_size_bytes = output_path.stat().st_size
        
        # Transition to COMPLETE
        input_data.document.update_status(ProcessingStatus.COMPLETE)
        
        # Calculate export time
        export_time = (datetime.now() - start_time).total_seconds()
        
        return ExportOutput(
            output_path=output_path,
            file_size_bytes=file_size_bytes,
            pages_exported=len(page_numbers),
            export_time_seconds=export_time,
        )
        
    except ExportError:
        # Transition to ERROR on export failure
        input_data.document.update_status(ProcessingStatus.ERROR)
        raise
    except Exception as e:
        input_data.document.update_status(ProcessingStatus.ERROR)
        raise ExportError(
            message=f"Unexpected error during export: {str(e)}",
            error_code="WRITE_FAILED",
            output_path=str(output_path),
            details={"error": str(e)},
        )
