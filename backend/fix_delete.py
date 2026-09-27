path = "routes/projects.py"
with open(path) as f:
    content = f.read()

content = content.replace(
    "from fastapi import APIRouter, Depends",
    "from fastapi import APIRouter, Depends, HTTPException"
)

old = '''def delete_project(project_id: int, user: dict = Depends(require_role("admin"))):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Projects WHERE project_id = %s", (project_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Project deleted!"}'''

new = '''def delete_project(project_id: int, user: dict = Depends(require_role("admin"))):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Projects WHERE project_id = %s", (project_id,))
    deleted = cursor.rowcount
    conn.commit()
    cursor.close()
    conn.close()
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Project deleted!"}'''

if old not in content:
    print("OLD BLOCK NOT FOUND - aborting, no changes made")
else:
    content = content.replace(old, new)
    with open(path, "w") as f:
        f.write(content)
    print("Fix applied successfully")
