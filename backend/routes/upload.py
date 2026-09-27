from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
import shutil
import os

from ocr.pipeline import OCRPipeline
from ocr.text_native_extractor import is_text_native, extract_text_native_records, extract_format_c_records
from ocr.review_utils import (
    build_review_rows,
    apply_outlier_detection,
    write_review_csv,
    summarize_rows,
)
from routes.auth import get_current_user, require_role
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
    chainage_start: float = Form(None),
    chainage_step: float = Form(20.0),
):
    """
    Detects scanned vs. text-native PDFs (via pdffonts) and routes to
    the calibrated OCRPipeline or the text-native extractor accordingly,
    then runs the same review-flagging logic used by export_review_csv.py.
    Also tracks this upload in ProjectFiles (SRS Section 11 / Module 1's
    "track uploaded files and processing status") and records key events
    in AuditLog.
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

    route_used = "unknown"
    extract_meta = {}
    print("Detecting PDF type and extracting...")
    try:
        route_used = "text_native" if is_text_native(file_path) else "ocr"
        print(f"PDF type detected: {route_used}")

        if route_used == "text_native":
            if chainage_start is not None:
                raw_records, extract_meta = extract_text_native_records(
                    file_path, chainage_start, chainage_step
                )
            else:
                raw_records, extract_meta = [], {}

            expected = extract_meta.get("expected_stations", 0)
            matched = extract_meta.get("lines_matched", 0)
            ab_match_ratio = (matched / expected) if expected else 0
            if not raw_records or ab_match_ratio < 0.5:
                # FORMAT_A/B either did not match, matched too sparsely to
                # trust (a real sheet should match the large majority of its
                # own grid; a false-positive match against annotation text
                # or a wrong chainage grid matches only a small fraction),
                # or chainage_start was not supplied -- try FORMAT_C
                # (multi-sheet, chainage read from the PDF text directly,
                # no chainage_start needed).
                raw_records, extract_meta = extract_format_c_records(file_path)

            records = [
                {
                    "field_chainage": r["field_chainage"],
                    "ground_level": r["ground_level"],
                    "formation_level": r["formation_level"],
                    "rail_level": r.get("rail_level"),
                    "cut_fill": r["cut_fill"],
                }
                for r in raw_records
            ]
        else:
            if chainage_start is None:
                raise HTTPException(
                    status_code=422,
                    detail="chainage_start is required for scanned (OCR) uploads.",
                )
            pipeline = OCRPipeline()
            records = pipeline.process(file_path, project_id)
    except Exception as e:
        update_file_status(file_record_id, "failed", error_message=str(e))
        log_action(
            project_id,
            "ocr_failed",
            {"filename": file.filename, "error": str(e), "route": route_used},
        )
        raise HTTPException(status_code=500, detail=f"PDF extraction failed ({route_used}): {e}")

    if not records:
        update_file_status(file_record_id, "failed", error_message="No rows extracted")
        log_action(
            project_id,
            "ocr_failed",
            {"filename": file.filename, "error": "no rows extracted", "route": route_used},
        )
        raise HTTPException(
            status_code=422,
            detail=(
                f"No rows extracted via the {route_used} path. The PDF may not "
                "match the expected L-section table layout."
            ),
        )

    effective_start = chainage_start if chainage_start is not None else records[0]["field_chainage"]
    rows_out = build_review_rows(
        records, effective_start, chainage_step,
        text_native=(route_used == "text_native"),
    )
    depth_flagged, gl_spikes, fl_spikes = apply_outlier_detection(rows_out)

    out_path = _review_csv_path(project_id)
    write_review_csv(rows_out, out_path)

    summary = summarize_rows(rows_out, depth_flagged, gl_spikes, fl_spikes)
    summary["project_id"] = project_id
    summary["review_csv_path"] = out_path
    is_format_c = extract_meta.get("format_detected") == "C"
    summary["chainage_start"] = effective_start
    summary["chainage_step"] = chainage_step
    summary["chainage_end"] = (
        records[-1]["field_chainage"] if is_format_c
        else effective_start + chainage_step * (len(records) - 1)
    )
    summary["route_used"] = route_used
    if extract_meta:
        summary["extract_meta"] = extract_meta

    update_file_status(file_record_id, "completed", rows_extracted=summary["total_stations"])
    log_action(project_id, "ocr_completed", summary)

    print(f"\nWrote {summary['total_stations']} rows to {out_path}")
    print(f"Pre-filled (clean) : {summary['clean_prefilled']}")
    print(f"Needs manual review: {summary['needs_manual_review']}")

    return summary
