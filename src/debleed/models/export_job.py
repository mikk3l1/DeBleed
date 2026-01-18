"""
Export job data models for DeBleed application.

This module contains dataclasses for export jobs and batch processing queues.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from uuid import uuid4

from debleed.models.document import ScannedDocument
from debleed.models.enums import ExportFormat, JobStatus


@dataclass
class ExportJob:
    """Processing task for generating cleaned PDF and/or text output.
    
    Attributes:
        job_id: Unique identifier (UUID)
        source_document: Reference to input document
        selected_pages: Page numbers to include in export (empty = all pages)
        output_format: SEARCHABLE_PDF, PDF_AND_TEXT, or TEXT_ONLY
        output_path: Destination file path
        ocr_enabled: Whether to perform OCR
        status: QUEUED, PROCESSING, COMPLETE, or FAILED
        progress_percentage: Completion progress (0.0-100.0)
        error_message: Error details if status == FAILED
        created_at: When job was created
        completed_at: When job finished (success or failure)
    """
    
    source_document: ScannedDocument
    output_format: ExportFormat
    output_path: Path
    job_id: str = field(default_factory=lambda: str(uuid4()))
    selected_pages: list[int] = field(default_factory=list)
    ocr_enabled: bool = True
    status: JobStatus = JobStatus.QUEUED
    progress_percentage: float = 0.0
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    def __post_init__(self) -> None:
        """Validate export job properties."""
        if not 0.0 <= self.progress_percentage <= 100.0:
            raise ValueError("progress_percentage must be in [0.0, 100.0]")
        if self.status == JobStatus.COMPLETE:
            if self.completed_at is None:
                raise ValueError("completed_at must be set when status is COMPLETE")
            if self.progress_percentage != 100.0:
                raise ValueError("progress_percentage must be 100.0 when status is COMPLETE")
        if self.status == JobStatus.FAILED and self.error_message is None:
            raise ValueError("error_message must be set when status is FAILED")
        # Validate selected pages
        if self.selected_pages:
            if any(p < 1 or p > self.source_document.page_count for p in self.selected_pages):
                raise ValueError("selected_pages contains invalid page numbers")
    
    @property
    def elapsed_time(self) -> timedelta:
        """Time from creation to completion (or now)."""
        end_time = self.completed_at if self.completed_at else datetime.now()
        return end_time - self.created_at
    
    @property
    def is_complete(self) -> bool:
        """True if job is finished (success or failure)."""
        return self.status in {JobStatus.COMPLETE, JobStatus.FAILED}
    
    @property
    def requires_ocr(self) -> bool:
        """True if output format requires OCR."""
        return self.output_format != ExportFormat.TEXT_ONLY or self.ocr_enabled


@dataclass
class BatchQueue:
    """Collection of export jobs for multi-document processing.
    
    Attributes:
        queue_id: Unique identifier (UUID)
        export_jobs: Jobs in processing order
        current_job_index: Index of currently processing job (-1 if none active)
        overall_progress: Percentage of all jobs complete (0.0-100.0)
        successful_exports: Count of jobs with status == COMPLETE
        failed_exports: Count of jobs with status == FAILED
        flagged_for_review: Count of documents with pages needing review
        created_at: When batch was created
        completed_at: When all jobs finished
    """
    
    export_jobs: list[ExportJob]
    queue_id: str = field(default_factory=lambda: str(uuid4()))
    current_job_index: int = -1
    overall_progress: float = 0.0
    successful_exports: int = 0
    failed_exports: int = 0
    flagged_for_review: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    def __post_init__(self) -> None:
        """Validate batch queue properties."""
        if not 0.0 <= self.overall_progress <= 100.0:
            raise ValueError("overall_progress must be in [0.0, 100.0]")
        if self.current_job_index >= len(self.export_jobs):
            raise ValueError("current_job_index must be valid index or -1")
        if self.successful_exports + self.failed_exports > len(self.export_jobs):
            raise ValueError("successful + failed cannot exceed total jobs")
    
    @property
    def total_jobs(self) -> int:
        """Total number of jobs in queue."""
        return len(self.export_jobs)
    
    @property
    def remaining_jobs(self) -> int:
        """Number of jobs not yet complete."""
        return self.total_jobs - (self.successful_exports + self.failed_exports)
    
    @property
    def is_complete(self) -> bool:
        """True if all jobs finished."""
        return self.current_job_index >= self.total_jobs or self.remaining_jobs == 0
    
    @property
    def success_rate(self) -> float:
        """Ratio of successful exports to total jobs."""
        return self.successful_exports / self.total_jobs if self.total_jobs > 0 else 0.0
