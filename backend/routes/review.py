from fastapi import APIRouter, Depends
from pydantic import BaseModel
from database import get_db
from routes.auth import get_current_user, require_role
from services.row_review_service import RowReviewService
router = APIRouter()
class SkippedRow(BaseModel):
    project_id: int
    raw_chainage: str
    raw_gl: str
    raw_fl: str
    reason: str
class BulkApproveRequest(BaseModel):
    project_id: int
    reviewed_by: str = None
@router.post("/review/skip")
def save_skip(data: SkippedRow):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO SkippedRows (project_id, raw_chainage, raw_gl, raw_fl, reason) VALUES (%s, %s, %s, %s, %s)",
        (data.project_id, data.raw_chainage, data.raw_gl, data.raw_fl, data.reason)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Skipped row saved"}
@router.get("/review/{project_id}")
def review_extraction(project_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM ChainageProfile WHERE project_id = %s ORDER BY chainage ASC",
        (project_id,)
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    result = []
    for row in rows:
        result.append({
            "id": row[0],
            "chainage": float(row[2]),
            "gl": float(row[3]) if row[3] is not None else None,
            "fl": float(row[4]) if row[4] is not None else None,
            "fill": float(row[5]),
            "cut": float(row[6])
        })
    return {
        "project_id": project_id,
        "total_rows": len(result),
        "data": result
    }
@router.get("/review/skipped/{project_id}")
def get_skipped(project_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM SkippedRows WHERE project_id = %s",
        (project_id,)
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    result = []
    for row in rows:
        result.append({
            "id": row[0],
            "chainage": row[2],
            "gl": row[3],
            "fl": row[4],
            "reason": row[5]
        })
    return {
        "project_id": project_id,
        "total_skipped": len(result),
        "skipped": result
    }
@router.post("/review/auto-validate/{project_id}")
def auto_validate(project_id: int):
    service = RowReviewService()
    result = service.auto_validate(project_id)
    return {
        "project_id": project_id,
        "pending": result["pending"],
        "flagged": result["flagged"]
    }
@router.post("/review/bulk-approve")
def bulk_approve(data: BulkApproveRequest):
    service = RowReviewService()
    approved_count = service.bulk_approve(data.project_id, data.reviewed_by)
    return {
        "project_id": data.project_id,
        "approved": approved_count
    }
@router.get("/review/status/{project_id}")
def get_row_review_status(project_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM RowReview WHERE project_id = %s ORDER BY chainage ASC",
        (project_id,)
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    result = []
    for row in rows:
        result.append({
            "id": row[0],
            "chainage": float(row[2]),
            "status": row[3],
            "reason": row[4],
            "reviewed_by": row[5],
            "reviewed_at": row[6]
        })
    return {
        "project_id": project_id,
        "total_rows": len(result),
        "rows": result
    }
