"""
OCR result data models for DeBleed application.

This module contains dataclasses representing OCR extraction results,
including text content, confidence scores, and structural text blocks.
"""

from dataclasses import dataclass, field


@dataclass
class TextBlock:
    """Structural unit of extracted text (paragraph or text region).
    
    Attributes:
        content: Text within this block
        position: (x, y, width, height) relative to page
        reading_order_index: Position in reading sequence
        confidence: OCR confidence for this block (0.0-1.0)
        is_multi_column_part: True if part of multi-column layout
    """
    
    content: str
    position: tuple[int, int, int, int]
    reading_order_index: int
    confidence: float
    is_multi_column_part: bool = False
    
    def __post_init__(self) -> None:
        """Validate text block properties."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be in [0.0, 1.0]")
        if self.reading_order_index < 0:
            raise ValueError("reading_order_index must be >= 0")
    
    @property
    def word_count(self) -> int:
        """Number of words in content."""
        return len(self.content.split())
    
    @property
    def is_low_confidence(self) -> bool:
        """True if confidence < 0.75."""
        return self.confidence < 0.75


@dataclass
class OCRResult:
    """Extracted text from a page region.
    
    Attributes:
        text_content: Full extracted text
        text_blocks: Structural breakdown of text into paragraphs/regions
        overall_confidence: Average confidence across all text blocks (0.0-1.0)
        detected_language: ISO 639-1 language code (e.g., 'en', 'es')
        reading_order: Indices of text_blocks in correct reading order
        flagged_words: Words with confidence < 0.75 and their scores
        processing_time_seconds: Time taken for OCR execution
    """
    
    text_content: str
    text_blocks: list[TextBlock]
    overall_confidence: float
    detected_language: str
    reading_order: list[int]
    flagged_words: list[tuple[str, float]] = field(default_factory=list)
    processing_time_seconds: float = 0.0
    
    def __post_init__(self) -> None:
        """Validate OCR result properties."""
        if not 0.0 <= self.overall_confidence <= 1.0:
            raise ValueError("overall_confidence must be in [0.0, 1.0]")
        if len(self.reading_order) != len(self.text_blocks):
            raise ValueError("reading_order length must equal text_blocks length")
        if self.reading_order:
            max_idx = max(self.reading_order)
            min_idx = min(self.reading_order)
            if max_idx >= len(self.text_blocks) or min_idx < 0:
                raise ValueError("reading_order contains invalid indices")
        # Validate flagged words have confidence < 0.75
        for word, conf in self.flagged_words:
            if conf >= 0.75:
                raise ValueError(f"Flagged word '{word}' has confidence {conf} >= 0.75")
    
    @property
    def plain_text(self) -> str:
        """Text content with [?] markers added after flagged words."""
        result = self.text_content
        # Sort flagged words by position (reverse to avoid index shifting)
        flagged_dict = {word: conf for word, conf in self.flagged_words}
        for word in sorted(flagged_dict.keys(), key=lambda w: result.rfind(w), reverse=True):
            # Add [?] marker after last occurrence of flagged word
            last_pos = result.rfind(word)
            if last_pos != -1:
                insert_pos = last_pos + len(word)
                result = result[:insert_pos] + "[?]" + result[insert_pos:]
        return result
    
    @property
    def word_count(self) -> int:
        """Total number of words in text_content."""
        return len(self.text_content.split())
    
    @property
    def flagged_word_count(self) -> int:
        """Number of flagged words."""
        return len(self.flagged_words)
