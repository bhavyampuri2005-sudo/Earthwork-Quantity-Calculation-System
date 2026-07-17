from database import get_db


class RowReviewService:
    """
    Manages per-station review status for bulk review (SRS Module 3).

    ChainageProfile is wiped and reinserted on every /calculation/run, so
    review decisions can't live as a column on it - RowReview is a
    separate table keyed on (project_id, chainage), independent of
    ChainageProfile's row lifecycle.

    NOTE on flag granularity: by the time a station reaches ChainageProfile,
    calc_engine.py has already collapsed every failure mode - blank OCR
    cell, out-of-range value (ELEV_MIN/MAX), and neighbor-spike outlier
    (review_utils.flag_spikes) - into a single signal: gl IS NULL OR
    fl IS NULL. The per-cause distinction (blank vs range vs spike) is
    lost upstream in review_utils.py, which nulls the value before it
    ever reaches the CSV calc_engine reads. So auto-validate below can
    only flag "incomplete" vs "complete" - not WHY, beyond that generic
    reason.
    """

    def __init__(self):
        pass

    def auto_validate(self, project_id):
        conn = get_db()
        cursor = conn.cursor()
        pending_count = 0
        flagged_count = 0
        try:
            cursor.execute(
                "SELECT chainage, gl, fl FROM ChainageProfile WHERE project_id = %s",
                (project_id,),
            )
            rows = cursor.fetchall()

            for chainage, gl, fl in rows:
                complete = gl is not None and fl is not None
                status = "pending" if complete else "flagged"
                reason = None if complete else (
                    "Missing or invalid GL/FL (blank, out-of-range, "
                    "or OCR spike-flagged upstream)"
                )

                if complete:
                    pending_count += 1
                else:
                    flagged_count += 1

                cursor.execute(
                    """
                    INSERT INTO RowReview (project_id, chainage, status, reason)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (project_id, chainage)
                    DO UPDATE SET status = EXCLUDED.status, reason = EXCLUDED.reason
                    WHERE RowReview.status = 'pending'
                    """,
                    (project_id, chainage, status, reason),
                )

            conn.commit()
            print(f"\nRowReview auto-validate: {pending_count} pending, {flagged_count} flagged.")

        except Exception as e:
            conn.rollback()
            print("\nDatabase Error (RowReview auto_validate):")
            print(e)
            raise
        finally:
            cursor.close()
            conn.close()

        return {"pending": pending_count, "flagged": flagged_count}

    def bulk_approve(self, project_id, reviewed_by=None):
        conn = get_db()
        cursor = conn.cursor()
        approved_ids = []
        try:
            cursor.execute(
                """
                UPDATE RowReview
                SET status = 'approved', reviewed_by = %s, reviewed_at = now()
                WHERE project_id = %s AND status = 'pending'
                RETURNING id
                """,
                (reviewed_by, project_id),
            )
            approved_ids = cursor.fetchall()
            conn.commit()
            print(f"\nRowReview bulk_approve: {len(approved_ids)} rows approved.")

        except Exception as e:
            conn.rollback()
            print("\nDatabase Error (RowReview bulk_approve):")
            print(e)
            raise
        finally:
            cursor.close()
            conn.close()

        return len(approved_ids)
