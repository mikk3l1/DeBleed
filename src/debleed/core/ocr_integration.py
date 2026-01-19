"""OCR text extraction pipeline stage."""

from dataclasses import dataclass, field
from typing import Optional

import pytesseract
from numpy.typing import NDArray
from PIL import Image

from debleed.config.ocr_config import OCRConfig
from debleed.core.exceptions import OCRError
from debleed.models.ocr_result import OCRResult, TextBlock


@dataclass
class OCRInput:
    """Input for OCR stage.
    
    Attributes:
        image_data: RGB image as numpy array (H, W, 3) with dtype uint8 (cropped to content area)
        page_number: 1-indexed page number being processed
        config: OCR configuration (language, confidence threshold, etc.)
    """
    
    image_data: NDArray
    page_number: int
    config: OCRConfig = field(default_factory=OCRConfig)
    
    def __post_init__(self) -> None:
        """Validate OCR input."""
        if self.image_data.ndim != 3:
            raise ValueError(f"image_data must be 3D array (H,W,C), got shape {self.image_data.shape}")
        if self.page_number < 1:
            raise ValueError(f"page_number must be >= 1, got {self.page_number}")


@dataclass
class OCROutput:
    """Output from OCR stage.
    
    Attributes:
        ocr_result: Extracted text with blocks and confidence
        processing_time_seconds: Time taken for OCR extraction
    """
    
    ocr_result: OCRResult
    processing_time_seconds: float


def get_tesseract_path() -> Optional[str]:
    """Detect Tesseract executable path.
    
    Checks for:
    1. System Tesseract (in PATH)
    2. Bundled Tesseract (future enhancement)
    
    Returns:
        Path to tesseract executable, or None if not found
    """
    try:
        # Try to get Tesseract version (validates it's available)
        pytesseract.get_tesseract_version()
        return pytesseract.pytesseract.tesseract_cmd
    except Exception:
        return None


def verify_language_available(language: str) -> bool:
    """Check if Tesseract language pack is installed.
    
    Args:
        language: ISO 639-2 language code (e.g., 'eng', 'spa', 'fra', 'deu')
        
    Returns:
        True if language is available, False otherwise
    """
    try:
        # Get list of available languages
        langs = pytesseract.get_languages(config='')
        return language in langs
    except Exception:
        return False


def extract_text(input_data: OCRInput) -> OCROutput:
    """Extract text from image using Tesseract OCR.
    
    OCR pipeline:
    1. Check Tesseract availability
    2. Verify language packs
    3. Convert numpy array to PIL Image
    4. Run Tesseract with fixed PSM=3 (fully automatic), OEM=3 (default)
    5. Extract word-level confidence scores
    6. Flag low-confidence words (< 0.75)
    7. Segment into text blocks
    8. Determine reading order (left-to-right columns)
    
    Args:
        input_data: Image and configuration for OCR
        
    Returns:
        OCROutput with extracted text and metadata
        
    Raises:
        OCRError: If Tesseract not found, language unavailable, or extraction fails
    """
    import time
    start_time = time.time()
    
    try:
        # Check Tesseract availability
        tesseract_path = get_tesseract_path()
        if tesseract_path is None:
            raise OCRError(
                message="Tesseract OCR engine not found. Please install Tesseract.",
                error_code="TESSERACT_NOT_FOUND",
                page_number=input_data.page_number,
            )
        
        # Verify primary language
        if input_data.config.supported_languages:
            primary_lang = input_data.config.supported_languages[0]
            if not verify_language_available(primary_lang):
                raise OCRError(
                    message=f"Language pack '{primary_lang}' not installed",
                    error_code="LANGUAGE_NOT_AVAILABLE",
                    page_number=input_data.page_number,
                    language=primary_lang,
                )
        
        # Convert numpy array to PIL Image
        pil_image = Image.fromarray(input_data.image_data)
        
        # Tesseract configuration
        # PSM 3: Fully automatic page segmentation (no OSD)
        # OEM 3: Default (uses what's available - LSTM, Legacy, or both)
        config_str = f"--psm {input_data.config.tesseract_psm} --oem 3"
        
        # Language specification
        lang_str = '+'.join(input_data.config.supported_languages)
        
        # Extract detailed OCR data
        try:
            ocr_data = pytesseract.image_to_data(
                pil_image,
                lang=lang_str,
                config=config_str,
                output_type=pytesseract.Output.DICT,
            )
        except Exception as e:
            raise OCRError(
                message=f"Tesseract execution failed: {str(e)}",
                error_code="INVALID_IMAGE",
                page_number=input_data.page_number,
                details={"error": str(e)},
            )
        
        # Parse OCR data into text blocks
        text_blocks = []
        flagged_words = []
        full_text = []
        
        # Group words by block
        block_texts = {}
        block_boxes = {}
        block_confidences = {}
        
        for i, word_text in enumerate(ocr_data['text']):
            if not word_text.strip():
                continue
            
            conf = float(ocr_data['conf'][i])
            block_num = ocr_data['block_num'][i]
            x = ocr_data['left'][i]
            y = ocr_data['top'][i]
            w = ocr_data['width'][i]
            h = ocr_data['height'][i]
            
            # Track low-confidence words
            if conf < input_data.config.confidence_threshold * 100:  # Tesseract uses 0-100 scale
                flagged_words.append((word_text, conf / 100.0))
            
            # Group by block
            if block_num not in block_texts:
                block_texts[block_num] = []
                block_boxes[block_num] = []
                block_confidences[block_num] = []
            
            block_texts[block_num].append(word_text)
            block_boxes[block_num].append((x, y, w, h))
            block_confidences[block_num].append(conf)
        
        # Create TextBlock objects
        reading_order_index = 0
        for block_num in sorted(block_texts.keys()):
            words = block_texts[block_num]
            boxes = block_boxes[block_num]
            confidences = block_confidences[block_num]
            
            if not words:
                continue
            
            # Calculate block bounding box
            min_x = min(b[0] for b in boxes)
            min_y = min(b[1] for b in boxes)
            max_x = max(b[0] + b[2] for b in boxes)
            max_y = max(b[1] + b[3] for b in boxes)
            
            block_content = ' '.join(words)
            avg_confidence = sum(confidences) / len(confidences) / 100.0  # Convert to 0.0-1.0
            
            text_block = TextBlock(
                content=block_content,
                position=(min_x, min_y, max_x - min_x, max_y - min_y),
                reading_order_index=reading_order_index,
                confidence=avg_confidence,
                is_multi_column_part=False,  # TODO: Multi-column detection in future
            )
            
            text_blocks.append(text_block)
            full_text.append(block_content)
            reading_order_index += 1
        
        # Determine detected language (use first specified language for now)
        detected_language = input_data.config.supported_languages[0] if input_data.config.supported_languages else "eng"
        
        # Calculate overall confidence
        if block_confidences:
            all_confidences = [c for block_confs in block_confidences.values() for c in block_confs]
            overall_confidence = sum(all_confidences) / len(all_confidences) / 100.0
        else:
            overall_confidence = 0.0
        
        # Create OCRResult
        ocr_result = OCRResult(
            text_content='\n\n'.join(full_text),
            text_blocks=text_blocks,
            overall_confidence=overall_confidence,
            detected_language=detected_language,
            reading_order_indices=[tb.reading_order_index for tb in text_blocks],
            flagged_words=flagged_words,
            processing_time_seconds=time.time() - start_time,
        )
        
        return OCROutput(
            ocr_result=ocr_result,
            processing_time_seconds=time.time() - start_time,
        )
        
    except OCRError:
        raise
    except Exception as e:
        raise OCRError(
            message=f"Unexpected error during OCR: {str(e)}",
            error_code="INVALID_IMAGE",
            page_number=input_data.page_number,
            details={"error": str(e)},
        )
