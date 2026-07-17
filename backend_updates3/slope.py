from fastapi import APIRouter
from pydantic import BaseModel
from database import get_db

router = APIRouter()

class SlopeData(BaseModel):
    project_id: int
    from_chainage: float
    to_chainage: float
    side_slope_cut: float
    side_slope_fill: float

@router.post("/slope")
def add_slope(data: SlopeData):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO SlopeMaster (project_id, from_chainage, to_chainage, side_slope_cut, side_slope_fill) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (data.project_id, data.from_chainage, data.to_chainage, data.side_slope_cut, data.side_slope_fill)
    )
    new_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
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
            "side_slope_fill": float(row[5])
        })
    return result
