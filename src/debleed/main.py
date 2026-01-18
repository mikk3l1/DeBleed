"""Application entry point for DeBleed."""

import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from debleed.ui.main_window import MainWindow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def check_tesseract_available() -> bool:
    """Check if Tesseract OCR is available.
    
    Returns:
        True if Tesseract is found, False otherwise
        
    Note:
        For MVP, OCR is not used, but we check availability
        for future functionality (FR-046, SC-020).
    """
    try:
        import pytesseract
        
        # Try to get Tesseract version
        version = pytesseract.get_tesseract_version()
        logger.info(f"Tesseract OCR found: version {version}")
        return True
    except Exception as e:
        logger.warning(f"Tesseract OCR not available: {e}")
        return False


def show_tesseract_warning(app: QApplication) -> None:
    """Show warning dialog about missing Tesseract.
    
    Args:
        app: QApplication instance
    """
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Icon.Warning)
    msg.setWindowTitle("Tesseract OCR Not Found")
    msg.setText(
        "Tesseract OCR engine is not installed or not found in PATH.\n\n"
        "OCR functionality will not be available.\n"
        "The application will still work for boundary detection and PDF cropping."
    )
    msg.setInformativeText(
        "To install Tesseract:\n\n"
        "Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki\n"
        "macOS: brew install tesseract\n"
        "Linux: sudo apt-get install tesseract-ocr\n\n"
        "After installation, restart the application."
    )
    msg.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg.exec()


def main() -> int:
    """Main application entry point.
    
    Application initialization:
    1. Create QApplication
    2. Check Tesseract OCR availability (warn if missing)
    3. Create and show MainWindow
    4. Start event loop
    
    Returns:
        Exit code (0 = success, non-zero = error)
    """
    logger.info("Starting DeBleed application")
    
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("DeBleed")
    app.setOrganizationName("DeBleed")
    
    # Check OCR engine availability
    tesseract_available = check_tesseract_available()
    if not tesseract_available:
        show_tesseract_warning(app)
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    logger.info("Application started")
    
    # Start event loop
    exit_code = app.exec()
    
    logger.info(f"Application exiting with code {exit_code}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
