from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import shutil
import os

from ocr.pipeline import OCRPipeline
from ocr.review_utils import (
    build_review_rows,
    apply_outlier_detection,
    write_review_csv,
    summarize_rows,
)
from services.project_files_service import create_file_record, update_file_status
from services.audit_service import log_action

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _review_csv_path(project_id: int) -> str:
    if project_id == 1:
        return "review.csv"
    return f"review_{project_id}.csv"


@router.post("/upload-pdf/{project_id}")
async def upload_pdf(
    project_id: int,
    file: UploadFile = File(...),
    chainage_start: float = Form(...),
    chainage_step: float = Form(20.0),
):
    """
    Runs the calibrated OCRPipeline plus the same review-flagging logic
    used by export_review_csv.py. Also tracks this upload in
    ProjectFiles (SRS Section 11 / Module 1's "track uploaded files and
    processing status") and records key events in AuditLog.
    """
    print(f"\nReceived file: {file.filename}")
    print(f"Project ID: {project_id}, chainage_start: {chainage_start}, step: {chainage_step}")

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    print(f"PDF saved to: {file_path}")

    file_record_id = create_file_record(
        project_id, file.filename, file_path, chainage_start, chainage_step
    )
    log_action(project_id, "pdf_uploaded", {"filename": file.filename, "file_path": file_path})

    print("Starting OCR pipeline...")
    try:
        pipeline = OCRPipeline()
        records = pipeline.process(file_path, project_id)
    except Exception as e:
        update_file_status(file_record_id, "failed", error_message=str(e))
        log_action(project_id, "ocr_failed", {"filename": file.filename, "error": str(e)})
        raise HTTPException(status_code=500, detail=f"OCR pipeline failed: {e}")

    if not records:
        update_file_status(file_record_id, "failed", error_message="No rows extracted")
        log_action(project_id, "ocr_failed", {"filename": file.filename, "error": "no rows extracted"})
        raise HTTPException(
            status_code=422,
            detail=(
                "OCR pipeline returned no rows. The scan may not match the "
                "expected L-section table layout."
            ),
        )

    rows_out = build_review_rows(records, chainage_start, chainage_step)
    depth_flagged, gl_spikes, fl_spikes = apply_outlier_detection(rows_out)

    out_path = _review_csv_path(project_id)
    write_review_csv(rows_out, out_path)

    summary = summarize_rows(rows_out, depth_flagged, gl_spikes, fl_spikes)
    summary["project_id"] = project_id
    summary["review_csv_path"] = out_path
    summary["chainage_start"] = chainage_start
    summary["chainage_step"] = chainage_step
    summary["chainage_end"] = chainage_start + chainage_step * (len(records) - 1)

    update_file_status(file_record_id, "completed", rows_extracted=summary["total_stations"])
    log_action(project_id, "ocr_completed", summary)

    print(f"\nWrote {summary['total_stations']} rows to {out_path}")
    print(f"Pre-filled (clean) : {summary['clean_prefilled']}")
    print(f"Needs manual review: {summary['needs_manual_review']}")

    return summary
