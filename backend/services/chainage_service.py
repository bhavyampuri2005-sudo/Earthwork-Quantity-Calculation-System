from database import get_db


class ChainageService:

    def __init__(self):
        pass

    def save_records(self, records):

        conn = get_db()
        cursor = conn.cursor()

        inserted = 0

        try:

            for record in records:

                print(f"Inserting: {record}")

                cursor.execute(
                    """
                    INSERT INTO ChainageProfile
                    (
                        project_id,
                        chainage,
                        gl,
                        fl,
                        fill,
                        cut
                    )
                    VALUES
                    (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        record["project_id"],
                        record["chainage"],
                        record["gl"],
                        record["fl"],
                        record["fill"],
                        record["cut"]
                    )
                )

                new_id = cursor.fetchone()[0]

                print(f"Inserted Row ID: {new_id}")

                inserted += 1

            conn.commit()

            print("\nDatabase Commit Successful")

        except Exception as e:

            conn.rollback()

            print("\nDatabase Error:")
            print(e)

        finally:

            cursor.close()
            conn.close()

        return inserted
