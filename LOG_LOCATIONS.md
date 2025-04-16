# Image Extractor Log Locations

## Main Application Logs
Located in `~/Documents/ImageExtractorOutput/logs/`:

### 1. Main Debug Log
- **Current File**: `image_extractor_debug.log`
- **Source**: `launch.py`
- **Purpose**: Records application startup, initialization, and general application events
- **Level**: DEBUG
- **Format**: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

### 2. OCR Processing Log
- **Current File**: `process_ocr.log`
- **Source**: `src/process_ocr.py`
- **Purpose**: Records detailed OCR processing events, pattern matching, and field extraction
- **Level**: DEBUG
- **Format**: `%(asctime)s - %(levelname)s - %(message)s`

## Log Rotation
Both log files are automatically rotated on application startup:

### Archive Location
```
~/Documents/ImageExtractorOutput/
└── logs/
    ├── image_extractor_debug.log  # Current debug log
    ├── process_ocr.log           # Current OCR log
    └── archive/                  # Archived logs
        ├── image_extractor_debug.log.YYYYMMDD_HHMMSS
        ├── image_extractor_debug.log.YYYYMMDD_HHMMSS
        ├── process_ocr.log.YYYYMMDD_HHMMSS
        └── process_ocr.log.YYYYMMDD_HHMMSS
```

### Rotation Details
- Logs are rotated (archived) on application startup
- Maximum of 5 backup files are kept for each log type
- Archived logs are timestamped with format: `YYYYMMDD_HHMMSS`
- Oldest logs are automatically deleted when exceeding the backup limit
- Current logs are always at the root log directory
- Archived logs are stored in the `archive` subdirectory

## Configuration Details

### Debug Log Configuration (launch.py)
```python
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(debug_log_path),
        logging.StreamHandler()
    ]
)
```

### OCR Processing Log Configuration (process_ocr.py)
```python
logging.basicConfig(
    filename=log_file_path,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='a'
)
```

## Notes
- Both logs are configured at DEBUG level for maximum verbosity
- Both logs append to existing files rather than overwriting
- The debug log includes both file and console output
- The OCR log includes file output only
- All logs are stored in a central location under the application's output directory
- Log rotation helps manage disk space and keeps debugging history organized 