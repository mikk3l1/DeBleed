"""
Data model enumerations for DeBleed application.

This module defines all enum types used throughout the application for
representing processing states, export formats, and status values.
"""

from enum import Enum, auto


class ProcessingStatus(Enum):
    """Current state of document processing pipeline."""
    
    LOADED = auto()      # Document loaded into application
    ANALYZING = auto()   # Layout detection in progress
    READY = auto()       # Analysis complete, ready for export
    EXPORTING = auto()   # Export operation in progress
    COMPLETE = auto()    # Export finished successfully
    ERROR = auto()       # Processing failed


class AdjustmentStatus(Enum):
    """Status of page boundary adjustment."""
    
    AUTO = auto()     # Automatic detection, not modified by user
    MANUAL = auto()   # User manually adjusted boundaries
    FLAGGED = auto()  # Automatic detection had low confidence


class ExportFormat(Enum):
    """Output format for cleaned documents."""
    
    SEARCHABLE_PDF = auto()  # PDF with embedded OCR text layer
    PDF_AND_TEXT = auto()    # Searchable PDF + separate .txt file
    TEXT_ONLY = auto()       # Only .txt file output


class JobStatus(Enum):
    """Status of export job execution."""
    
    QUEUED = auto()      # Waiting to be processed
    PROCESSING = auto()  # Currently being processed
    COMPLETE = auto()    # Successfully finished
    FAILED = auto()      # Encountered error
