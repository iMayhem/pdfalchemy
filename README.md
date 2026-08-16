# PDFAlchemy

A unique, memory-efficient PDF conversion and editing library designed for VPS deployment.

## What Makes It Unique

- **Streaming Architecture**: Processes pages one at a time. Handles 1000+ page PDFs on a 1GB RAM VPS.
- **Semantic Layout Analysis**: Understands document structure — headers, footers, headings, body text, captions, tables.
- **Multi-format Output**: DOCX (editable Word), HTML (styled), Markdown (clean), JSON (structured data).
- **Non-destructive Editing**: Merge, split, rotate, watermark, redact, compress, extract images.
- **REST API + WebSockets**: Async conversion with real-time progress tracking.
- **Dockerized**: One-command deployment on any VPS.

## Web UI

PDFAlchemy includes a full browser-based editor. Launch it with:

```bash
pip install -e .
python -m pdfalchemy.web_server
```

Then open `http://your-vps-ip:8000` in your browser.

### Web UI Features
- Drag & drop PDF upload
- Live page preview with thumbnails
- Text content view with semantic highlighting
- Convert to DOCX, HTML, Markdown, or JSON
- Watermark with customizable text, opacity, and size
- Compress with size reduction stats
- Rotate all pages (90°, 180°, 270°)
- Split by page ranges into multiple files
- Extract images from the PDF
- Redact sensitive areas by coordinates

## Quick Start

### Installation

```bash
pip install -e .
```

### CLI Usage

```bash
# Convert to editable Word document
pdfalchemy convert input.pdf -o output.docx

# Convert to Markdown
pdfalchemy convert input.pdf -f markdown -o output.md

# Convert to structured JSON
pdfalchemy convert input.pdf -f json -o output.json

# Add watermark
pdfalchemy edit input.pdf --watermark "CONFIDENTIAL" -o watermarked.pdf

# Compress PDF
pdfalchemy edit input.pdf --compress -o compressed.pdf

# Extract all images
pdfalchemy edit input.pdf --extract-images ./images -o dummy.pdf

# Split PDF
pdfalchemy edit input.pdf --split 1 5 --split 6 10 -o split.pdf
```

### API Server

```bash
# Start the server
uvicorn pdfalchemy.api.server:app --host 0.0.0.0 --port 8000

# Or with Docker
cd docker && docker-compose up -d
```

**Endpoints:**
- `POST /convert` — Upload PDF and convert (returns job ID)
- `GET /jobs/{job_id}` — Check conversion status
- `GET /download/{job_id}` — Download converted file
- `WS /ws/{job_id}` — Real-time progress via WebSocket
- `GET /health` — Health check

### Python API

```python
from pdfalchemy.core.extractor import StreamingExtractor
from pdfalchemy.core.converter import ConverterFactory
from pdfalchemy.core.editor import PDFEditor

# Convert PDF
with StreamingExtractor("input.pdf") as extractor:
    converter = ConverterFactory.get_converter("docx", extractor)
    converter.convert("output.docx")

# Edit PDF
editor = PDFEditor("input.pdf")
editor.watermark("DRAFT", "output.pdf")
editor.compress("compressed.pdf")
```

## Docker Deployment

```bash
cd docker
docker-compose up -d
```

The API will be available at `http://your-vps-ip:8000`.

## Architecture

```
pdfalchemy/
├── core/
│   ├── extractor.py   # Streaming layout analysis
│   ├── converter.py   # Multi-format output
│   └── editor.py      # PDF editing ops
├── api/
│   └── server.py      # FastAPI + WebSockets
└── cli.py             # Command-line tool
```

## License

MIT
