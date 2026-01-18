"""Main window for DeBleed application."""

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from debleed.core.document_loader import load_document
from debleed.core.exceptions import DeBleedError, ExportError, LayoutDetectionError, PreprocessingError
from debleed.core.export import ExportInput, export_document
from debleed.core.pipeline import ProcessingProgress, process_document
from debleed.models.document import ScannedDocument
from debleed.models.enums import AdjustmentStatus

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window for DeBleed.
    
    UI Components:
    - File picker button for PDF selection
    - Page list view showing page numbers and confidence scores
    - Export button for generating cleaned PDF
    - Progress bar during processing
    - Status bar for messages
    
    Workflow:
    1. User clicks "Open PDF" → file picker dialog
    2. Load document → process pipeline → display pages
    3. User reviews pages (confidence scores, flagged pages)
    4. User clicks "Export Clean PDF" → save cleaned version
    """
    
    # Signal emitted when processing completes
    processing_complete = Signal()
    
    def __init__(self):
        """Initialize main window."""
        super().__init__()
        
        self.document: Optional[ScannedDocument] = None
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self) -> None:
        """Set up user interface components."""
        self.setWindowTitle("DeBleed - Scan Cleaner")
        self.setMinimumSize(600, 400)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout
        layout = QVBoxLayout(central_widget)
        
        # Title label
        title_label = QLabel("DeBleed - Remove Bleed Marks from Scanned PDFs")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title_label)
        
        # Open PDF button
        self.open_button = QPushButton("Open PDF")
        self.open_button.setMinimumHeight(40)
        layout.addWidget(self.open_button)
        
        # Page list
        list_label = QLabel("Pages:")
        layout.addWidget(list_label)
        
        self.page_list = QListWidget()
        self.page_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        layout.addWidget(self.page_list)
        
        # Export button
        self.export_button = QPushButton("Export Clean PDF")
        self.export_button.setMinimumHeight(40)
        self.export_button.setEnabled(False)  # Disabled until document loaded
        layout.addWidget(self.export_button)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)  # Hidden until processing starts
        layout.addWidget(self.progress_bar)
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def _connect_signals(self) -> None:
        """Connect UI signals to slots."""
        self.open_button.clicked.connect(self.on_open_pdf)
        self.export_button.clicked.connect(self.on_export_pdf)
        self.processing_complete.connect(self.on_processing_complete)
    
    @Slot()
    def on_open_pdf(self) -> None:
        """Handle Open PDF button click."""
        # Show file picker dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select PDF File",
            "",
            "PDF Files (*.pdf)",
        )
        
        if not file_path:
            # User cancelled
            return
        
        # Load and process document
        self._load_and_process_document(Path(file_path))
    
    def _load_and_process_document(self, file_path: Path) -> None:
        """Load PDF and run processing pipeline.
        
        Args:
            file_path: Path to PDF file
        """
        try:
            # Update UI state
            self.open_button.setEnabled(False)
            self.export_button.setEnabled(False)
            self.progress_bar.setValue(0)
            self.progress_bar.setVisible(True)
            self.page_list.clear()
            self.statusBar().showMessage(f"Loading {file_path.name}...")
            
            # Load document
            logger.info(f"Loading document: {file_path}")
            self.document = load_document(file_path)
            
            # Process document through pipeline
            logger.info(f"Processing {self.document.page_count} pages...")
            self.document = process_document(
                self.document,
                progress_callback=self._on_progress_update,
            )
            
            # Processing complete
            self.processing_complete.emit()
            
        except PreprocessingError as e:
            self._show_error("PDF Loading Error", e.message)
            self._reset_ui()
        except LayoutDetectionError as e:
            self._show_error("Layout Detection Error", e.message)
            self._reset_ui()
        except DeBleedError as e:
            self._show_error("Processing Error", e.message)
            self._reset_ui()
        except Exception as e:
            logger.exception("Unexpected error during processing")
            self._show_error("Unexpected Error", str(e))
            self._reset_ui()
    
    def _on_progress_update(self, progress: ProcessingProgress) -> None:
        """Handle progress updates from pipeline.
        
        Args:
            progress: Current processing progress
        """
        self.progress_bar.setValue(int(progress.progress_percentage))
        self.statusBar().showMessage(progress.status_message)
    
    @Slot()
    def on_processing_complete(self) -> None:
        """Handle pipeline processing completion."""
        if self.document is None:
            return
        
        logger.info(f"Processing complete: {len(self.document.pages)} pages")
        
        # Populate page list
        self.page_list.clear()
        for page in self.document.pages:
            # Format: "Page 1 - Confidence: 0.92 ✓"
            confidence_str = f"{page.confidence_score:.2f}"
            
            # Status indicator
            if page.adjustment_status == AdjustmentStatus.FLAGGED:
                status_icon = "⚠️"  # Flagged for review
                status_text = "NEEDS REVIEW"
            elif page.is_borderline_confidence:
                status_icon = "⚠"  # Borderline confidence
                status_text = "Borderline"
            else:
                status_icon = "✓"  # Good
                status_text = "OK"
            
            item_text = f"Page {page.page_number} - Confidence: {confidence_str} - {status_text} {status_icon}"
            
            item = QListWidgetItem(item_text)
            
            # Color coding
            if page.adjustment_status == AdjustmentStatus.FLAGGED:
                item.setForeground(Qt.GlobalColor.red)
            elif page.is_borderline_confidence:
                item.setForeground(Qt.GlobalColor.darkYellow)
            else:
                item.setForeground(Qt.GlobalColor.darkGreen)
            
            self.page_list.addItem(item)
        
        # Update UI state
        self.progress_bar.setVisible(False)
        self.open_button.setEnabled(True)
        self.export_button.setEnabled(True)
        self.statusBar().showMessage(f"Loaded {self.document.page_count} pages - Ready to export")
        
        # Show summary
        flagged_count = sum(
            1 for p in self.document.pages 
            if p.adjustment_status == AdjustmentStatus.FLAGGED
        )
        if flagged_count > 0:
            self._show_info(
                "Pages Flagged for Review",
                f"{flagged_count} page(s) have low confidence and are flagged for review.\n"
                "These pages will still be exported with detected boundaries.",
            )
    
    @Slot()
    def on_export_pdf(self) -> None:
        """Handle Export Clean PDF button click."""
        if self.document is None:
            return
        
        try:
            # Update UI
            self.export_button.setEnabled(False)
            self.statusBar().showMessage("Exporting clean PDF...")
            
            # Export document
            logger.info(f"Exporting document: {self.document.file_path}")
            export_input = ExportInput(document=self.document)
            export_output = export_document(export_input)
            
            # Success
            logger.info(f"Export complete: {export_output.output_path}")
            self.statusBar().showMessage(f"Exported to {export_output.output_path.name}")
            
            self._show_info(
                "Export Successful",
                f"Cleaned PDF saved to:\n{export_output.output_path}\n\n"
                f"Pages exported: {export_output.pages_exported}\n"
                f"File size: {export_output.file_size_bytes / 1024:.1f} KB",
            )
            
        except ExportError as e:
            self._show_error("Export Error", e.message)
        except DeBleedError as e:
            self._show_error("Export Error", e.message)
        except Exception as e:
            logger.exception("Unexpected error during export")
            self._show_error("Unexpected Error", str(e))
        finally:
            self.export_button.setEnabled(True)
    
    def _show_error(self, title: str, message: str) -> None:
        """Show error dialog.
        
        Args:
            title: Dialog title
            message: Error message
        """
        QMessageBox.critical(self, title, message)
    
    def _show_info(self, title: str, message: str) -> None:
        """Show information dialog.
        
        Args:
            title: Dialog title
            message: Info message
        """
        QMessageBox.information(self, title, message)
    
    def _reset_ui(self) -> None:
        """Reset UI to initial state after error."""
        self.document = None
        self.open_button.setEnabled(True)
        self.export_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.page_list.clear()
        self.statusBar().showMessage("Ready")
