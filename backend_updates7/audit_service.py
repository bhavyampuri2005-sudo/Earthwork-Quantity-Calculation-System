import json
from database import get_db


def log_action(project_id, action, details=None, actor=None):
    """
    Records an entry in AuditLog. `details` can be a dict (JSON-
    serialized automatically) or a plain string. `actor` defaults to a
    placeholder since there is no auth system yet - once one exists,
    pass the real username/user_id through here instead.

    Failures to write a log entry are swallowed (printed, not raised)
    so a logging problem can never block the actual operation it's
    describing - audit logging should observe the system, not gate it.
    """
    if isinstance(details, dict):
        details = json.dumps(details, default=str)

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO AuditLog (project_id, action, details, actor) VALUES (%s, %s, %s, %s)",
            (project_id, action, details, actor or "unknown (no auth system yet)"),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"AuditLog write failed (non-fatal): {e}")
    finally:
        cursor.close()
        conn.close()
