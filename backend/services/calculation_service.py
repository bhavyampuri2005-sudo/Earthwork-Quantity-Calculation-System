from database import get_db


class CalculationService:
    """
    Persists Average End Area calc engine output to EarthworkCalculation.

    One row per interval from calc_engine.compute()["intervals"]:
      - chainage = interval's starting chainage (table has no `to`/`d`
        column, so the interval's end point is implicit - it's the next
        row's chainage, except at cut/fill crossover points, which are
        computed midpoints and don't correspond to a stored station).
      - area     = average of the two bounding stations' areas (A1+A2)/2,
        i.e. the same figure the volume formula itself used. Left NULL
        for pending_review intervals and crossover sub-intervals, where
        no single station-pair average applies.
      - volume   = interval volume (NULL for pending_review).
      - type     = 'cut' / 'fill' / 'pending_review'.
    """

    def __init__(self):
        pass

    def save_intervals(self, project_id, intervals):
        conn = get_db()
        cursor = conn.cursor()
        inserted = 0
        try:
            for interval in intervals:
                cursor.execute(
                    """
                    INSERT INTO EarthworkCalculation
                    (project_id, chainage, area, volume, type)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        project_id,
                        interval["from"],
                        interval.get("area"),
                        interval.get("volume"),
                        interval["type"],
                    ),
                )
                new_id = cursor.fetchone()[0]
                inserted += 1
            conn.commit()
            print(f"\nEarthworkCalculation: inserted {inserted} interval rows.")
        except Exception as e:
            conn.rollback()
            print("\nDatabase Error (EarthworkCalculation):")
            print(e)
            raise
        finally:
            cursor.close()
            conn.close()
        return inserted
