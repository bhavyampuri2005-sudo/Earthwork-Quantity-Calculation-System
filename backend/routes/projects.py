from fastapi import APIRouter
from database import get_db

router = APIRouter()

@router.post("/projects")
def create_project(project_name: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO Projects (project_name) VALUES (%s) RETURNING project_id",
        (project_name,)
    )
    project_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Project created!", "project_id": project_id}

@router.get("/projects")
def get_projects():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Projects ORDER BY created_at DESC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    projects = []
    for row in rows:
        projects.append({
            "project_id": row[0],
            "project_name": row[1],
            "created_at": str(row[2])
        })
    return projects

@router.delete("/projects/{project_id}")
def delete_project(project_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Projects WHERE project_id = %s", (project_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Project deleted!"}



