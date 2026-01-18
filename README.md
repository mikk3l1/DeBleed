# DeBleed - Scan Cleaner

Desktop application for removing bleed marks from scanned PDFs.

## Installation

### Prerequisites

- Python 3.11 or higher
- Tesseract OCR (optional for MVP, required for text extraction features)

### Install Dependencies

```powershell
# From repository root
pip install -e .
```

Or install from requirements.txt:

```powershell
pip install -r requirements.txt
```

### Install Tesseract OCR (Optional)

**Windows:**
Download installer from: https://github.com/UB-Mannheim/tesseract/wiki

**macOS:**
```bash
brew install tesseract
```

**Linux:**
```bash
sudo apt-get install tesseract-ocr
```

## Running the Application

### Method 1: Using entry point (after pip install)

```powershell
debleed
```

### Method 2: Direct Python execution

```powershell
python src/debleed/main.py
```

### Method 3: As Python module

```powershell
python -m debleed.main
```

## Usage

1. **Open PDF**: Click "Open PDF" button and select a scanned PDF file
2. **Review Pages**: View detected page boundaries and confidence scores
   - ✓ Green: Good confidence (≥ 0.85)
   - ⚠ Yellow: Borderline confidence (0.80-0.85)
   - ⚠️ Red: Flagged for review (< 0.80)
3. **Export**: Click "Export Clean PDF" to save cropped version
   - Output saved as `<filename>_cleaned.pdf` in same directory

## Features (MVP)

- ✅ PDF loading and preprocessing
- ✅ Automatic page boundary detection (Canny edge detection)
- ✅ Confidence scoring (0.0-1.0 scale)
- ✅ Visual review of detected boundaries
- ✅ PDF export with cropped pages
- ✅ Progress tracking
- ✅ Error handling with user-friendly messages

## Architecture

```
src/debleed/
├── config/           # Configuration dataclasses
├── core/             # Pipeline stages
│   ├── preprocessing.py      # PDF → RGB image
│   ├── layout_detection.py   # Edge detection → boundaries
│   ├── document_loader.py    # Document initialization
│   ├── pipeline.py           # Orchestration
│   ├── export.py             # PDF generation
│   └── exceptions.py         # Error types
├── models/           # Data models
│   ├── enums.py             # Status enumerations
│   ├── page.py              # Page, DetectedBoundary
│   ├── document.py          # ScannedDocument
│   ├── ocr_result.py        # OCR models (future)
│   └── export_job.py        # Export tracking
├── ui/               # PySide6 GUI
│   ├── main_window.py       # Main application window
│   └── __init__.py
└── main.py           # Entry point
```

## Development

### Running Tests

```powershell
pytest tests/
```

### Code Quality

```powershell
# Type checking
mypy src/

# Formatting
black src/

# Linting
ruff check src/
```

## Known Limitations (MVP)

- No OCR text extraction (Phase 4 feature)
- No manual boundary adjustment (Phase 5 feature)
- No batch processing (Phase 6 feature)
- Timeout mechanism uses SIGALRM (Unix only, Windows skips timeout)
- Rotation detection is stubbed (placeholder only)

## Troubleshooting

### "Tesseract OCR Not Found"
OCR is not required for MVP functionality (boundary detection + PDF cropping). Install Tesseract for future features.

### "No page boundaries detected"
Try adjusting Canny thresholds in `DetectionConfig` if scans have low contrast.

### Export fails with "Disk full"
Ensure at least 2x estimated output size is available (roughly 200KB per page).

## License

See LICENSE file for details.
