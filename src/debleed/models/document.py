"""
Document data model for DeBleed application.

This module contains the ScannedDocument dataclass representing
an input PDF file with its processing state and pages.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from debleed.models.enums import ProcessingStatus
from debleed.models.page import Page


@dataclass
class ScannedDocument:
    """Represents an input PDF file containing imperfect scans.
    
    Attributes:
        file_path: Absolute path to source PDF file
        page_count: Total number of pages in document
        processing_status: Current state (LOADED, ANALYZING, READY, EXPORTING, COMPLETE, ERROR)
        pages: Collection of pages in reading order
        created_at: Timestamp when document was loaded
        file_size_bytes: Size of source file for memory estimation
    
    State Transitions:
        LOADED → ANALYZING (when layout detection starts)
        ANALYZING → READY (when all pages analyzed)
        READY → EXPORTING (when user initiates export)
        EXPORTING → COMPLETE (when export finishes)
        Any state → ERROR (on failure)
    """
    
    file_path: Path
    page_count: int
    processing_status: ProcessingStatus = ProcessingStatus.LOADED
    pages: list[Page] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    file_size_bytes: int = 0
    
    def __post_init__(self) -> None:
        """Validate document properties."""
        if not self.file_path.exists():
            raise ValueError(f"File does not exist: {self.file_path}")
        if not self.file_path.is_file():
            raise ValueError(f"Path is not a file: {self.file_path}")
        if self.page_count <= 0:
            raise ValueError("page_count must be > 0")
        if len(self.pages) > 0 and len(self.pages) != self.page_count:
            raise ValueError("pages length must equal page_count")
    
    def update_status(self, new_status: ProcessingStatus) -> None:
        """Update processing status with validation of state transitions."""
        # Valid transitions
        valid_transitions = {
            ProcessingStatus.LOADED: [ProcessingStatus.ANALYZING, ProcessingStatus.ERROR],
            ProcessingStatus.ANALYZING: [ProcessingStatus.READY, ProcessingStatus.ERROR],
            ProcessingStatus.READY: [ProcessingStatus.EXPORTING, ProcessingStatus.ERROR],
            ProcessingStatus.EXPORTING: [ProcessingStatus.COMPLETE, ProcessingStatus.ERROR],
            ProcessingStatus.COMPLETE: [],
            ProcessingStatus.ERROR: [],
        }
        
        if new_status not in valid_transitions.get(self.processing_status, []):
            raise ValueError(
                f"Invalid state transition: {self.processing_status.name} → {new_status.name}"
            )
        
        self.processing_status = new_status
