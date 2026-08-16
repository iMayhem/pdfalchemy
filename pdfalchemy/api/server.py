"""
FastAPI server with WebSocket progress tracking and background job processing.
"""
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile, WebSocket, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import asyncio

from ..core.extractor import StreamingExtractor
from ..core.converter import ConverterFactory

app = FastAPI(title="PDFAlchemy API", version="1.0.0")

UPLOAD_DIR = Path("/tmp/pdfalchemy/uploads")
OUTPUT_DIR = Path("/tmp/pdfalchemy/outputs")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

jobs = {}


class JobStatus(BaseModel):
    id: str
    status: str
    progress: int
    message: str
    output_file: Optional[str] = None


@app.post("/convert", response_model=JobStatus)
async def convert_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    format: str = "docx"
):
    """Upload and convert PDF asynchronously."""
    job_id = str(uuid.uuid4())
    input_path = UPLOAD_DIR / f"{job_id}.pdf"

    with open(input_path, "wb") as f:
        f.write(await file.read())

    jobs[job_id] = {
        "id": job_id,
        "status": "pending",
        "progress": 0,
        "message": "Upload complete, waiting to process",
        "output_file": None
    }

    background_tasks.add_task(process_conversion, job_id, input_path, format)
    return JobStatus(**jobs[job_id])


async def process_conversion(job_id: str, input_path: Path, format_type: str):
    jobs[job_id]["status"] = "processing"
    jobs[job_id]["message"] = "Starting extraction"

    try:
        output_path = OUTPUT_DIR / f"{job_id}.{format_type}"

        with StreamingExtractor(str(input_path)) as extractor:
            converter = ConverterFactory.get_converter(format_type, extractor)
            jobs[job_id]["progress"] = 50
            jobs[job_id]["message"] = f"Converting to {format_type}"
            converter.convert(str(output_path))

            jobs[job_id]["progress"] = 100
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["message"] = "Conversion complete"
            jobs[job_id]["output_file"] = str(output_path)

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["message"] = str(e)


@app.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatus(**jobs[job_id])


@app.get("/download/{job_id}")
async def download_result(job_id: str):
    if job_id not in jobs or jobs[job_id]["status"] != "completed":
        raise HTTPException(status_code=404, detail="Result not available")

    output_file = jobs[job_id]["output_file"]
    if not output_file or not Path(output_file).exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        output_file,
        filename=f"converted.{Path(output_file).suffix}",
        media_type="application/octet-stream"
    )


@app.websocket("/ws/{job_id}")
async def websocket_progress(websocket: WebSocket, job_id: str):
    """WebSocket for real-time progress updates."""
    await websocket.accept()

    if job_id not in jobs:
        await websocket.send_json({"error": "Job not found"})
        await websocket.close()
        return

    last_status = None
    while True:
        current = jobs[job_id].copy()
        if current != last_status:
            await websocket.send_json(current)
            last_status = current.copy()

        if current["status"] in ("completed", "failed"):
            await websocket.close()
            break

        await asyncio.sleep(0.5)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "pdfalchemy"}
