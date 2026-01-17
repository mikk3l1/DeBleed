# Developer Quickstart Guide

**Feature**: Desktop Scan Cleaner Application  
**Target Audience**: New developers joining the project  
**Time to First Success**: ~30 minutes

---

## Prerequisites

### Required Software
- **Python 3.11+**: Download from [python.org](https://www.python.org/downloads/)
- **Git**: For cloning repository
- **Tesseract OCR**: Required for text extraction
  - Windows: Download from [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)
  - macOS: `brew install tesseract`
  - Linux: `sudo apt-get install tesseract-ocr`

### Verify Installation

```powershell
# Check Python version
python --version  # Should be 3.11.0 or higher

# Check Tesseract installation
tesseract --version  # Should show Tesseract version 5.x

# Check pip
pip --version
```

---

## Environment Setup (5 minutes)

### 1. Clone Repository

```powershell
git clone <repository-url>
cd DeBleed
```

### 2. Create Virtual Environment

```powershell
# Create venv
python -m venv .venv

# Activate (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Activate (Windows CMD)
.\.venv\Scripts\activate.bat

# Activate (macOS/Linux)
source .venv/bin/activate
```

### 3. Install Dependencies

```powershell
# Upgrade pip
python -m pip install --upgrade pip

# Install core dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

**Expected packages**:
- opencv-python (image processing)
- pytesseract (OCR wrapper)
- pymupdf (PDF rendering)
- PySide6 (Qt GUI framework)
- numpy (array operations)
- pytest, pytest-qt (testing)
- mypy, black, ruff (code quality)

---

## Project Structure

```
DeBleed/
├── src/
│   └── debleed/               # Main application package
│       ├── core/              # Processing pipeline
│       │   ├── preprocessing.py
│       │   ├── layout_detection.py
│       │   ├── ocr_integration.py
│       │   └── export.py
│       ├── models/            # Data classes (from data-model.md)
│       │   ├── document.py
│       │   ├── page.py
│       │   └── ocr.py
│       ├── ui/                # Qt-based GUI
│       │   ├── main_window.py
│       │   ├── preview_widget.py
│       │   └── batch_dialog.py
│       ├── config/            # Configuration management
│       │   └── settings.py
│       └── main.py            # Entry point
├── tests/
│   ├── unit/                  # Unit tests for each module
│   ├── integration/           # Pipeline integration tests
│   └── fixtures/              # Test PDFs and expected outputs
├── specs/                     # Feature specifications
├── .specify/                  # Project governance
├── requirements.txt           # Production dependencies
├── requirements-dev.txt       # Development dependencies
└── pyproject.toml             # Project metadata
```

---

## Running Your First Pipeline Test (10 minutes)

### 1. Verify Test Environment

```powershell
# Run simple sanity check
pytest tests/unit/test_preprocessing.py::test_render_simple_pdf -v
```

**Expected output**:
```
tests/unit/test_preprocessing.py::test_render_simple_pdf PASSED [100%]
```

### 2. Run Full Pipeline on Sample Document

```powershell
# Run integration test
pytest tests/integration/test_full_pipeline.py -v
```

This test:
1. Loads `tests/fixtures/sample_scan.pdf`
2. Preprocesses page to RGB image
3. Detects page boundary (should be high confidence)
4. Runs OCR on detected region
5. Exports cleaned PDF to temp directory

**Success indicators**:
- All stages complete without errors
- Confidence score >= 0.80
- Exported PDF contains text layer

### 3. Interactive Testing (Optional)

```powershell
# Run single page through pipeline
python -m debleed.core.pipeline tests/fixtures/sample_scan.pdf --page 1 --debug
```

This outputs:
- Detected boundary coordinates
- Confidence score
- OCR text preview
- Debug images (edge map, contours)

---

## Understanding the Pipeline (15 minutes)

### Data Flow Diagram

```
PDF File
  ↓
[Preprocessing] → RGB Image (H×W×3 uint8)
  ↓
[Layout Detection] → Primary Region Coordinates + Confidence
  ↓
[OCR Integration] → Text Content + Text Blocks + Confidence
  ↓
[Export] → Cleaned PDF (with optional text layer)
```

### Key Contracts

Each pipeline stage has a strict contract (see `/contracts/`):

1. **Preprocessing**: `PreprocessingInput` → `PreprocessingOutput`
   - Input: PDF path + page number
   - Output: RGB image array
   - Guarantees: Always 3-channel RGB, deterministic

2. **Layout Detection**: `LayoutDetectionInput` → `LayoutDetectionOutput`
   - Input: RGB image
   - Output: Bounding box + confidence
   - Guarantees: Geometric detection (no ML), confidence in [0.0, 1.0]

3. **OCR**: `OCRInput` → `OCROutput`
   - Input: Cropped image region
   - Output: Text + word confidences
   - Guarantees: Flags words below 0.75 confidence

4. **Export**: `ExportInput` → `ExportOutput`
   - Input: Document + pages + format
   - Output: PDF/text file paths
   - Guarantees: Byte-identical output (excluding timestamps)

### Reading the Code

**Start here**:
1. `src/debleed/models/page.py` - Core data structures
2. `src/debleed/core/preprocessing.py` - Simplest stage
3. `tests/unit/test_preprocessing.py` - Example tests

**Key patterns**:
- All functions use type hints: `def preprocess(input: PreprocessingInput) -> PreprocessingOutput`
- Errors raise typed exceptions: `raise PreprocessingError(error_code="PDF_UNREADABLE", ...)`
- All stages are pure functions (no global state)

---

## Development Workflow

### 1. Make Code Changes

Edit any file in `src/debleed/`. For example, improve edge detection in `layout_detection.py`.

### 2. Run Type Checking

```powershell
# Check type safety with mypy
mypy src/debleed
```

Fix any type errors before proceeding.

### 3. Format Code

```powershell
# Auto-format with black
black src/ tests/

# Lint with ruff
ruff check src/ tests/
```

### 4. Run Tests

```powershell
# Run all unit tests
pytest tests/unit/ -v

# Run specific test file
pytest tests/unit/test_layout_detection.py -v

# Run with coverage
pytest --cov=src/debleed --cov-report=html
```

### 5. Commit Changes

```powershell
git add .
git commit -m "Improve edge detection confidence calculation"
git push
```

---

## Common Tasks

### Add a New Configuration Parameter

1. Edit `src/debleed/config/settings.py`:
   ```python
   @dataclass
   class DetectionConfig:
       new_param: float = 0.5  # Add here
   ```

2. Update contract documentation: `specs/001-desktop-scan-cleaner/contracts/layout.md`

3. Add test: `tests/unit/test_config.py`

### Add a New Pipeline Stage

1. Create module: `src/debleed/core/new_stage.py`
2. Define input/output schemas (dataclasses)
3. Write contract: `specs/001-desktop-scan-cleaner/contracts/new_stage.md`
4. Implement stage function with type hints
5. Write unit tests: `tests/unit/test_new_stage.py`
6. Add to integration test: `tests/integration/test_full_pipeline.py`

### Run the GUI (When Available)

```powershell
# Launch desktop application
python -m debleed
```

This opens the Qt GUI where you can:
- Load PDF documents
- Preview detected boundaries
- Manually adjust regions
- Export cleaned PDFs

---

## UI Development (Using Qt)

### Qt Designer Workflow

1. Design UI in Qt Designer (optional):
   ```powershell
   pyside6-designer
   ```

2. Convert .ui files to Python:
   ```powershell
   pyside6-uic path/to/design.ui -o src/debleed/ui/design_ui.py
   ```

3. Import in your widget:
   ```python
   from debleed.ui.design_ui import Ui_MainWindow
   
   class MainWindow(QMainWindow, Ui_MainWindow):
       def __init__(self):
           super().__init__()
           self.setupUi(self)
   ```

### Testing Qt Widgets

```python
import pytest
from pytestqt.qtbot import QtBot
from debleed.ui.main_window import MainWindow

def test_load_document_button(qtbot: QtBot):
    window = MainWindow()
    qtbot.addWidget(window)
    
    # Simulate button click
    qtbot.mouseClick(window.load_button, Qt.LeftButton)
    
    # Verify dialog appeared
    assert window.document is not None
```

Run Qt tests:
```powershell
pytest tests/ui/ --qt-show-output
```

---

## Troubleshooting

### Issue: `ImportError: No module named 'cv2'`

**Solution**: Install opencv-python
```powershell
pip install opencv-python
```

### Issue: `pytesseract.TesseractNotFoundError`

**Solution**: Tesseract not in PATH. Set explicitly:
```python
# In src/debleed/core/ocr_integration.py
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

### Issue: Tests fail with "FileNotFoundError: sample_scan.pdf"

**Solution**: Generate test fixtures
```powershell
python scripts/generate_test_fixtures.py
```

### Issue: GUI doesn't launch on macOS

**Solution**: Install Qt platform plugin
```powershell
pip install --upgrade PySide6
```

### Issue: High memory usage during batch processing

**Solution**: Process pages sequentially, not in parallel:
```python
# BAD: Loads all pages into memory
pages = [preprocess(page_num) for page_num in range(1, 101)]

# GOOD: Processes one at a time
for page_num in range(1, 101):
    page = preprocess(page_num)
    process_page(page)
```

---

## Next Steps

### Learn More
- Read feature spec: `specs/001-desktop-scan-cleaner/spec.md`
- Study pipeline contracts: `specs/001-desktop-scan-cleaner/contracts/`
- Review constitution: `.specify/memory/constitution.md`

### Contribute
- Pick a task from `specs/001-desktop-scan-cleaner/tasks.md` (when available)
- Follow constitutional principles (determinism, explainability, etc.)
- Write tests before implementation (TDD)
- Submit pull request with clear description

### Advanced Topics
- **Performance tuning**: Profile with `pytest-benchmark`
- **Cross-platform packaging**: Build with PyInstaller
- **Continuous integration**: GitHub Actions workflow (`.github/workflows/`)

---

## Getting Help

- **Code questions**: Check contract documentation in `/contracts/`
- **Test failures**: Read error messages carefully - they include error codes
- **Performance issues**: Run profiler: `python -m cProfile -o profile.stats -m debleed.core.pipeline`
- **Constitutional compliance**: Review `.specify/memory/constitution.md` principles

**Welcome to the team! 🚀**
