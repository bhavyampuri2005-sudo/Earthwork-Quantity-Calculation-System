class RecordMapper:
    """
    Converts validated OCR records into
    database-ready records.
    """

    def __init__(self):
        pass

    def map_record(self, record, project_id):

        gl = record["ground_level"]
        fl = record["formation_level"]
        cf = record["cut_fill"]

        fill = 0.0
        cut = 0.0

        # Formation above ground → Fill
        if fl >= gl:
            fill = abs(cf)

        # Formation below ground → Cut
        else:
            cut = abs(cf)

        db_record = {

            "project_id": project_id,

            "chainage": record["chainage"],

            "gl": gl,

            "fl": fl,

            "fill": fill,

            "cut": cut,

            # Keep for future use
            "rail_level": record["rail_level"],

            "status": record.get("status", "VALID"),

            "remarks": record.get("remarks", "")

        }

        return db_record