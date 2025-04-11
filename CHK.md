# Project Checklist: Medical Image OCR & Classification System

Based on the [Implementation Plan](IMP_PLAN.md).

## Phase 1: Core Infrastructure & Setup

- [X] Set up Python environment (3.8+)
- [X] Install core dependencies (`os`, `sys`, `json`, `re`, `argparse`)
- [X] Implement directory scanner module
    - [X] Recursive directory traversal
    - [X] Image file filtering (e.g., `.jpg`, `.png`, `.tiff`)
    - [X] Generate list of image file paths
- [X] Implement basic image loading (using Pillow)
- [X] Define initial JSON output structure
- [X] Implement basic JSON writing functionality
- [X] Create command-line interface using `argparse`

## Phase 2: Image Preprocessing & OCR Pipeline

- [X] Install image processing dependencies (`opencv-python`, `pillow`)
- [X] Implement image preprocessing module (using OpenCV)
    - [X] Image normalization (resizing, contrast enhancement)
    - [X] Noise reduction techniques
    - [X] Binarization and thresholding
    - [X] Rotation/deskew correction (optional but recommended)
- [X] Install Tesseract OCR engine (system-level) - *Assumed installed*
- [X] Install Tesseract Python wrapper (`pytesseract`)
- [X] Implement OCR engine module
    - [X] Integrate `pytesseract` for text extraction
    - [X] Handle potential OCR errors (e.g., empty results, poor quality)
- [X] Test text extraction quality on sample images - *Unit tests added*
- [ ] *Optional: Install and integrate `easyocr` as a fallback OCR engine*

## Phase 3: Classification Engine

- [X] Install text processing dependencies (`nltk`, `spacy`)
- [X] Download necessary `nltk` data (e.g., stopwords, punkt, wordnet)
- [X] Download `spacy` model (`en_core_web_sm`)
- [X] Implement rule-based classification engine module
    - [X] Develop text pattern matching functions (using `re`)
    - [X] Implement classification rules for X-rays (keywords, format)
    - [X] Implement classification rules for One-step TB tests (keywords, dates, format)
    - [X] Implement classification rules for Two-step TB tests (keywords, dates, format)
    - [X] Implement classification rules for Blood tests (keywords, format, units)
- [X] Implement field extraction logic
    - [X] Name extraction (regex, heuristics, spaCy NER)
    - [X] Date extraction (regex, keywords, validation)
    - [X] X-ray type identification (regex, context)
- [ ] Implement confidence scoring for classifications (optional but recommended)
- [X] Integrate classification results into the JSON output structure

## Phase 4: Optimization & Enhancements

- [ ] Install performance/utility dependencies (`concurrent.futures`, `tqdm`)
- [ ] Implement parallel processing (`concurrent.futures`) for:
    - [ ] Image loading/preprocessing
    - [ ] OCR processing
- [ ] Add progress monitoring using `tqdm`
- [ ] Refine error handling for edge cases (e.g., corrupted images, unsupported formats)
- [ ] Optimize memory management (e.g., explicit garbage collection, resource cleanup)
- [ ] Configure Tesseract (`--psm`, `--oem`, language models) for better accuracy
- [ ] *Optional: Implement custom dictionaries for medical terms in Tesseract*

## Phase 5: Testing & Validation

- [ ] Write unit tests for individual modules (Scanner, Preprocessor, OCR, Classifier)
    - [ ] Use mocking for dependencies
    - [ ] Cover diverse inputs and edge cases
- [ ] Write integration tests for the end-to-end pipeline
    - [ ] Test with different directory structures
    - [ ] Test with various image formats and qualities
- [ ] Perform validation testing
    - [ ] Prepare a labeled dataset of diverse test images
    - [ ] Run the system on the labeled dataset
    - [ ] Calculate accuracy metrics (overall, per class)
    - [ ] Generate a confusion matrix
    - [ ] Analyze misclassifications and refine rules/preprocessing
- [ ] Perform performance testing
    - [ ] Measure processing time for different dataset sizes
    - [ ] Monitor CPU and memory usage
    - [ ] Assess scalability

## Phase 6: Documentation & Finalization

- [ ] Write `README.md` with setup instructions, usage guide, and dependencies.
- [ ] Add comments to the code, explaining complex logic.
- [ ] Final code review and cleanup.
- [ ] Package the application (if necessary). 