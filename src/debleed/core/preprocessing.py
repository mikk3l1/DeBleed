"""Preprocessing pipeline stage - PDF to normalized RGB images."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
import numpy as np
from numpy.typing import NDArray
from PIL import Image

from debleed.core.exceptions import PreprocessingError


@dataclass
class PreprocessingInput:
    """Input for preprocessing stage.
    
    Attributes:
        pdf_path: Path to source PDF file
        page_number: 1-indexed page number to extract
        target_dpi: Desired DPI for output image (won't upscale beyond native)
    """
    
    pdf_path: Path
    page_number: int
    target_dpi: int = 300
    
    def __post_init__(self) -> None:
        """Validate preprocessing input."""
        if not self.pdf_path.exists():
            raise ValueError(f"PDF file not found: {self.pdf_path}")
        if not self.pdf_path.is_file():
            raise ValueError(f"PDF path is not a file: {self.pdf_path}")
        if self.page_number < 1:
            raise ValueError(f"page_number must be >= 1, got {self.page_number}")
        if self.target_dpi < 72:
            raise ValueError(f"target_dpi must be >= 72, got {self.target_dpi}")


@dataclass
class PreprocessingOutput:
    """Output from preprocessing stage.
    
    Attributes:
        image_data: RGB image as numpy array (H, W, 3) with dtype uint8
        original_dpi: DPI of the original PDF page
        actual_dpi: DPI of the output image (may differ from target if downscaled)
        dimensions: Output image dimensions (width, height)
    """
    
    image_data: NDArray[np.uint8]
    original_dpi: float
    actual_dpi: float
    dimensions: tuple[int, int]
    
    def __post_init__(self) -> None:
        """Validate preprocessing output."""
        if self.image_data.ndim != 3:
            raise ValueError(f"image_data must be 3D array (H,W,C), got shape {self.image_data.shape}")
        if self.image_data.shape[2] != 3:
            raise ValueError(f"image_data must have 3 channels (RGB), got {self.image_data.shape[2]}")
        if self.image_data.dtype != np.uint8:
            raise ValueError(f"image_data must be uint8, got {self.image_data.dtype}")
        if self.dimensions[0] != self.image_data.shape[1] or self.dimensions[1] != self.image_data.shape[0]:
            raise ValueError(
                f"dimensions {self.dimensions} don't match image shape "
                f"({self.image_data.shape[1]}, {self.image_data.shape[0]})"
            )


def preprocess_page(input_data: PreprocessingInput) -> PreprocessingOutput:
    """Convert PDF page to normalized RGB image.
    
    Preprocessing pipeline:
    1. Open PDF and validate page number
    2. Render page to RGB image at appropriate DPI
    3. Normalize color space (grayscale → RGB, RGBA → RGB)
    4. Apply DPI adjustment (respect target_dpi, avoid upscaling)
    
    Args:
        input_data: Preprocessing configuration
        
    Returns:
        PreprocessingOutput with RGB image and metadata
        
    Raises:
        PreprocessingError: If PDF cannot be read, page is invalid, or rendering fails
    """
    try:
        # Open PDF document
        try:
            doc = fitz.open(input_data.pdf_path)
        except Exception as e:
            raise PreprocessingError(
                message=f"Cannot open PDF file: {input_data.pdf_path.name}",
                error_code="PDF_UNREADABLE",
                details={"path": str(input_data.pdf_path), "error": str(e)},
            )
        
        # Validate page number
        if input_data.page_number > doc.page_count:
            raise PreprocessingError(
                message=f"Page {input_data.page_number} does not exist (document has {doc.page_count} pages)",
                error_code="PAGE_OUT_OF_RANGE",
                page_number=input_data.page_number,
                details={"page_count": doc.page_count},
            )
        
        # Get page (0-indexed in PyMuPDF)
        page = doc[input_data.page_number - 1]
        
        # Determine DPI scaling
        # PyMuPDF default is 72 DPI, we calculate zoom factor
        original_dpi = 72.0
        zoom_factor = input_data.target_dpi / original_dpi
        
        # Render page to pixmap
        try:
            matrix = fitz.Matrix(zoom_factor, zoom_factor)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
        except Exception as e:
            raise PreprocessingError(
                message=f"Failed to render page {input_data.page_number}",
                error_code="RENDER_FAILED",
                page_number=input_data.page_number,
                details={"error": str(e)},
            )
        
        # Convert pixmap to numpy array
        # PyMuPDF pixmaps are in RGB format by default (alpha=False)
        img_bytes = pix.samples
        img_array = np.frombuffer(img_bytes, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        
        # Ensure RGB format (handle grayscale edge case)
        if img_array.shape[2] == 1:
            # Grayscale → RGB: replicate channel
            img_array = np.repeat(img_array, 3, axis=2)
        elif img_array.shape[2] == 4:
            # RGBA → RGB: drop alpha channel
            img_array = img_array[:, :, :3]
        
        doc.close()
        
        return PreprocessingOutput(
            image_data=img_array,
            original_dpi=original_dpi,
            actual_dpi=input_data.target_dpi,
            dimensions=(pix.width, pix.height),
        )
        
    except PreprocessingError:
        raise
    except MemoryError as e:
        raise PreprocessingError(
            message=f"Insufficient memory to process page {input_data.page_number}",
            error_code="MEMORY_EXCEEDED",
            page_number=input_data.page_number,
            details={"error": str(e)},
        )
    except Exception as e:
        raise PreprocessingError(
            message=f"Unexpected error during preprocessing: {str(e)}",
            error_code="RENDER_FAILED",
            page_number=input_data.page_number,
            details={"error": str(e)},
        )
