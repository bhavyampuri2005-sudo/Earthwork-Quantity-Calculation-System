from fastapi import APIRouter, Depends
from pydantic import BaseModel
from database import get_db
from routes.auth import get_current_user, require_role
from services.audit_service import log_action

router = APIRouter()

class ChainageData(BaseModel):
    project_id: int
    chainage: float
    gl: float
    fl: float
    fill: float = 0.0
    cut: float = 0.0

@router.post("/chainage")
def add_chainage(data: ChainageData):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO ChainageProfile (project_id, chainage, gl, fl, fill, cut) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
        (data.project_id, data.chainage, data.gl, data.fl, data.fill, data.cut)
    )
    new_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Chainage data added!", "id": new_id}

@router.get("/chainage/{project_id}")
def get_chainage(project_id: int):
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
            "project_id": row[1],
            "chainage": float(row[2]),
            "gl": float(row[3]) if row[3] is not None else None,
            "fl": float(row[4]) if row[4] is not None else None,
            "fill": float(row[5]),
            "cut": float(row[6])
        })
    return result

@router.put("/chainage/{id}")
def update_chainage(id: int, data: ChainageData):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE ChainageProfile SET chainage=%s, gl=%s, fl=%s, fill=%s, cut=%s WHERE id=%s",
        (data.chainage, data.gl, data.fl, data.fill, data.cut, id)
    )
    conn.commit()
    cursor.close()
    conn.close()
    log_action(data.project_id, "station_edited", {
        "chainage_profile_id": id,
        "chainage": data.chainage,
        "gl": data.gl,
        "fl": data.fl,
        "cut": data.cut,
        "fill": data.fill,
    })
    return {"message": "Chainage data updated!"}

@router.delete("/chainage/{id}")
def delete_chainage(id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ChainageProfile WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Chainage data deleted!"}
