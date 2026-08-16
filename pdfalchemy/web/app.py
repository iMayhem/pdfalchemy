"""PDFAlchemy Web UI - Full-featured PDF editor in the browser."""
import uuid
import shutil
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from ..core.extractor import StreamingExtractor
from ..core.converter import ConverterFactory
from ..core.editor import PDFEditor

UPLOAD_DIR = Path("/tmp/pdfalchemy/uploads")
OUTPUT_DIR = Path("/tmp/pdfalchemy/outputs")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def create_app() -> FastAPI:
    app = FastAPI(title="PDFAlchemy Web", version="1.0.0")
    static_path = Path(__file__).parent / "static"
    templates_path = Path(__file__).parent / "templates"
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
    templates = Jinja2Templates(directory=str(templates_path))

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        return templates.TemplateResponse("index.html", {"request": request})

    @app.post("/api/upload")
    async def upload_pdf(file: UploadFile = File(...)):
        file_id = str(uuid.uuid4())
        file_path = UPLOAD_DIR / f"{file_id}.pdf"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        doc = StreamingExtractor(str(file_path))
        with doc:
            page_count = len(doc.doc)
            first_page = doc.extract_page(0)
        return {"file_id": file_id, "filename": file.filename, "page_count": page_count,
                "dimensions": {"width": first_page.width, "height": first_page.height}}

    @app.get("/api/preview/{file_id}")
    async def preview_pdf(file_id: str, page: int = 0):
        file_path = UPLOAD_DIR / f"{file_id}.pdf"
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        doc = StreamingExtractor(str(file_path))
        with doc:
            if page >= len(doc.doc):
                raise HTTPException(status_code=404, detail="Page not found")
            page_layout = doc.extract_page(page)
        return {"page": page, "total_pages": len(doc.doc),
                "blocks": [{"text": b.text, "type": b.block_type, "font": b.font, "size": b.size, "bbox": b.bbox} for b in page_layout.blocks],
                "tables": page_layout.tables,
                "images": [{"index": img["index"], "width": img["width"], "height": img["height"], "ext": img["ext"]} for img in page_layout.images]}

    @app.get("/api/thumbnail/{file_id}")
    async def get_thumbnail(file_id: str, page: int = 0, dpi: int = 100):
        import fitz
        file_path = UPLOAD_DIR / f"{file_id}.pdf"
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        doc = fitz.open(str(file_path))
        if page >= len(doc):
            doc.close()
            raise HTTPException(status_code=404, detail="Page not found")
        page_obj = doc[page]
        mat = fitz.Matrix(dpi/72, dpi/72)
        pix = page_obj.get_pixmap(matrix=mat)
        thumb_path = OUTPUT_DIR / f"{file_id}_thumb_{page}.png"
        pix.save(str(thumb_path))
        doc.close()
        return FileResponse(str(thumb_path), media_type="image/png")

    @app.post("/api/convert")
    async def convert_pdf(file_id: str = Form(...), format: str = Form("docx"), page_breaks: bool = Form(True)):
        file_path = UPLOAD_DIR / f"{file_id}.pdf"
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        output_id = str(uuid.uuid4())
        output_path = OUTPUT_DIR / f"{output_id}.{format}"
        with StreamingExtractor(str(file_path)) as extractor:
            converter = ConverterFactory.get_converter(format, extractor)
            converter.convert(str(output_path), page_breaks=page_breaks)
        return {"job_id": output_id, "status": "completed", "download_url": f"/api/download/{output_id}.{format}"}

    @app.post("/api/watermark")
    async def watermark_pdf(file_id: str = Form(...), text: str = Form(...), opacity: float = Form(0.3), fontsize: int = Form(60)):
        file_path = UPLOAD_DIR / f"{file_id}.pdf"
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        output_id = str(uuid.uuid4())
        output_path = OUTPUT_DIR / f"{output_id}.pdf"
        editor = PDFEditor(str(file_path))
        editor.watermark(text, str(output_path), opacity=opacity, fontsize=fontsize)
        return {"job_id": output_id, "status": "completed", "download_url": f"/api/download/{output_id}.pdf"}

    @app.post("/api/compress")
    async def compress_pdf(file_id: str = Form(...)):
        file_path = UPLOAD_DIR / f"{file_id}.pdf"
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        output_id = str(uuid.uuid4())
        output_path = OUTPUT_DIR / f"{output_id}.pdf"
        editor = PDFEditor(str(file_path))
        editor.compress(str(output_path))
        original_size = file_path.stat().st_size
        compressed_size = output_path.stat().st_size
        reduction = ((original_size - compressed_size) / original_size) * 100
        return {"job_id": output_id, "status": "completed", "original_size": original_size,
                "compressed_size": compressed_size, "reduction_percent": round(reduction, 2),
                "download_url": f"/api/download/{output_id}.pdf"}

    @app.post("/api/rotate")
    async def rotate_pdf(file_id: str = Form(...), degrees: int = Form(...)):
        import fitz
        file_path = UPLOAD_DIR / f"{file_id}.pdf"
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        doc = fitz.open(str(file_path))
        total_pages = len(doc)
        doc.close()
        output_id = str(uuid.uuid4())
        output_path = OUTPUT_DIR / f"{output_id}.pdf"
        editor = PDFEditor(str(file_path))
        editor.rotate(list(range(1, total_pages + 1)), degrees, str(output_path))
        return {"job_id": output_id, "status": "completed", "download_url": f"/api/download/{output_id}.pdf"}

    @app.post("/api/split")
    async def split_pdf(file_id: str = Form(...), ranges: str = Form(...)):
        import json
        file_path = UPLOAD_DIR / f"{file_id}.pdf"
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        range_list = json.loads(ranges)
        output_id = str(uuid.uuid4())
        output_prefix = str(OUTPUT_DIR / f"{output_id}")
        editor = PDFEditor(str(file_path))
        output_files = editor.split([tuple(r) for r in range_list], output_prefix)
        return {"job_id": output_id, "status": "completed",
                "files": [{"part": i + 1, "download_url": f"/api/download/{Path(f).name}"} for i, f in enumerate(output_files)]}

    @app.post("/api/extract-images")
    async def extract_images(file_id: str = Form(...)):
        file_path = UPLOAD_DIR / f"{file_id}.pdf"
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        output_id = str(uuid.uuid4())
        output_dir = OUTPUT_DIR / f"{output_id}_images"
        editor = PDFEditor(str(file_path))
        extracted = editor.extract_images(str(output_dir))
        return {"job_id": output_id, "status": "completed", "image_count": len(extracted),
                "images": [{"filename": Path(img).name, "download_url": f"/api/download/images/{output_id}/{Path(img).name}"} for img in extracted]}

    @app.post("/api/redact")
    async def redact_pdf(file_id: str = Form(...), page: int = Form(...), x1: float = Form(...), y1: float = Form(...), x2: float = Form(...), y2: float = Form(...)):
        file_path = UPLOAD_DIR / f"{file_id}.pdf"
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        output_id = str(uuid.uuid4())
        output_path = OUTPUT_DIR / f"{output_id}.pdf"
        editor = PDFEditor(str(file_path))
        editor.redact(page, (x1, y1, x2, y2), str(output_path))
        return {"job_id": output_id, "status": "completed", "download_url": f"/api/download/{output_id}.pdf"}

    @app.get("/api/download/{filename}")
    async def download_file(filename: str):
        file_path = OUTPUT_DIR / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        return FileResponse(str(file_path), filename=filename, media_type="application/octet-stream")

    @app.get("/api/download/images/{job_id}/{filename}")
    async def download_image(job_id: str, filename: str):
        file_path = OUTPUT_DIR / f"{job_id}_images" / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        return FileResponse(str(file_path), filename=filename, media_type="image/*")

    @app.delete("/api/cleanup/{file_id}")
    async def cleanup(file_id: str):
        upload_path = UPLOAD_DIR / f"{file_id}.pdf"
        if upload_path.exists():
            upload_path.unlink()
        for f in OUTPUT_DIR.glob(f"{file_id}*"):
            if f.is_file(): f.unlink()
            elif f.is_dir(): shutil.rmtree(f)
        return {"status": "cleaned"}

    @app.get("/api/health")
    async def health():
        return {"status": "healthy", "service": "pdfalchemy-web"}

    return app

if __name__ == "__main__":
    import uvicorn
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)
