from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from database import get_db
from routes.auth import get_current_user, require_role
from services.audit_service import log_action

router = APIRouter()

class SlopeData(BaseModel):
    project_id: int
    from_chainage: float
    to_chainage: float
    side_slope_cut: float
    side_slope_fill: float
    remarks: Optional[str] = None

@router.post("/slope")
def add_slope(data: SlopeData):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO SlopeMaster (project_id, from_chainage, to_chainage, side_slope_cut, side_slope_fill, remarks) "
        "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
        (data.project_id, data.from_chainage, data.to_chainage, data.side_slope_cut, data.side_slope_fill, data.remarks)
    )
    new_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
    log_action(data.project_id, "slope_range_added", {
        "from_chainage": data.from_chainage,
        "to_chainage": data.to_chainage,
        "side_slope_cut": data.side_slope_cut,
        "side_slope_fill": data.side_slope_fill,
        "remarks": data.remarks,
    })
    return {"message": "Slope data added!", "id": new_id}

@router.get("/slope/{project_id}")
def get_slope(project_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM SlopeMaster WHERE project_id = %s ORDER BY from_chainage ASC",
        (project_id,)
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    result = []
    for row in rows:
        result.append({
            "id": row[0],
            "project_id": row[1],
            "from_chainage": float(row[2]),
            "to_chainage": float(row[3]),
            "side_slope_cut": float(row[4]),
            "side_slope_fill": float(row[5]),
            "remarks": row[6]
        })
    return result
