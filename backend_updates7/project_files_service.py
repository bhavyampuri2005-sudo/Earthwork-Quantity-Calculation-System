from database import get_db


def create_file_record(project_id, filename, file_path, chainage_start=None, chainage_step=None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO ProjectFiles (project_id, filename, file_path, status, chainage_start, chainage_step) "
        "VALUES (%s, %s, %s, 'uploaded', %s, %s) RETURNING id",
        (project_id, filename, file_path, chainage_start, chainage_step),
    )
    new_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
    return new_id


def update_file_status(file_id, status, rows_extracted=None, error_message=None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE ProjectFiles SET status = %s, rows_extracted = %s, error_message = %s WHERE id = %s",
        (status, rows_extracted, error_message, file_id),
    )
    conn.commit()
    cursor.close()
    conn.close()
