from fastapi import APIRouter, Depends
from database import get_db
from routes.auth import get_current_user

router = APIRouter()


@router.get("/audit-log/{project_id}")
def get_audit_log(project_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, action, details, actor, created_at FROM AuditLog "
        "WHERE project_id = %s ORDER BY created_at DESC",
        (project_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [
        {
            "id": r[0],
            "action": r[1],
            "details": r[2],
            "actor": r[3],
            "created_at": r[4].isoformat() if r[4] else None,
        }
        for r in rows
    ]


@router.get("/project-files/{project_id}")
def get_project_files(project_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, filename, file_path, uploaded_at, status, chainage_start, "
        "chainage_step, rows_extracted, error_message "
        "FROM ProjectFiles WHERE project_id = %s ORDER BY uploaded_at DESC",
        (project_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [
        {
            "id": r[0],
            "filename": r[1],
            "file_path": r[2],
            "uploaded_at": r[3].isoformat() if r[3] else None,
            "status": r[4],
            "chainage_start": float(r[5]) if r[5] is not None else None,
            "chainage_step": float(r[6]) if r[6] is not None else None,
            "rows_extracted": r[7],
            "error_message": r[8],
        }
        for r in rows
    ]
