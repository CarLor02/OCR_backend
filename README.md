# OCR Backend

A Flask-based OCR backend service that supports multiple document formats including PDF, Excel, Images, and HTML.

## Features

- **PDF Processing**: Advanced PDF processing using Docling with layout detection, table extraction, and OCR
- **Image OCR**: Image text extraction using AI-powered vision models
- **Excel Processing**: Excel file content extraction and conversion
- **HTML Processing**: HTML content extraction and cleaning
- **Multi-format Support**: Unified API for different document types
- **Local Model Support**: Automatic configuration for offline model usage

## Supported File Types

- **PDF**: `.pdf`
- **Images**: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.bmp`, `.tiff`, `.tif`
- **Excel**: `.xls`, `.xlsx`
- **HTML**: `.html`, `.htm`

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/CarLor02/OCR_backend.git
cd OCR_backend
```

### 2. Setup Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Setup Models

Download and configure the required AI models (approximately 1.1GB):

```bash
python setup_models.py
```

This will automatically:
- Download docling models for PDF processing
- Configure local model cache
- Verify the setup

Copy the example environment file and configure:

```bash
cp .env.example .env
```

Edit `.env` file with your settings:
- Set `YUNWU_API_KEY` for image and scanned PDF processing
- Configure other settings as needed

### 5. Run the Service

```bash
python app.py
```

The service will be available at `http://localhost:5050`

## API Usage

### Upload and Process Document

```bash
curl -X POST -F "file=@document.pdf" http://localhost:5050/process
```

### Response Format

```json
{
  "success": true,
  "content": "Extracted text content...",
  "metadata": {
    "file_type": "pdf",
    "pages_count": 5,
    "processing_time": 2.34
  }
}
```

## Configuration

Key environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `5050` |
| `YUNWU_API_KEY` | API key for image processing | - |
| `LOG_LEVEL` | Logging level | `INFO` |

## Model Management

The service uses AI models for document processing:

### Initial Setup
```bash
python setup_models.py
```

This downloads and configures:
- **Layout Detection Model**: For PDF structure analysis (~505MB)
- **Table Recognition Model**: For table extraction (~501MB)
- **OCR Model**: For text recognition (~108MB)
- **Figure Classification Model**: For image analysis (~16MB)
- **Total size**: Approximately 1.1GB

### Model Storage
- Models are stored in `docling_models/` directory
- Cache is created in `docling_cache/` for runtime use
- **Offline operation**: Once downloaded, no internet required

### Troubleshooting
If models are missing or corrupted:
```bash
# Re-download models
rm -rf docling_models/ docling_cache/
python setup_models.py
```

## Development

### Project Structure

```
OCR_backend/
├── app.py              # Main Flask application
├── config.py           # Configuration management
├── requirements.txt    # Python dependencies
├── processors/         # Document processors
│   ├── pdf_processor.py
│   ├── image_processor.py
│   ├── excel_processor.py
│   └── html_processor.py
└── utils/             # Utility functions
    ├── file_utils.py
    └── response_utils.py
```

### Adding New Processors

1. Create a new processor in `processors/`
2. Inherit from `BaseProcessor`
3. Implement required methods
4. Register in `processors/__init__.py`

## License

This project is licensed under the MIT License.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request
