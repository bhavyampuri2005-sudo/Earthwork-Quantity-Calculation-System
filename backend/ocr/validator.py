class Validator:

    def __init__(self):
        pass

     
    # Check for missing values
    

    def check_missing(self, record):

        required_fields = [
            "chainage",
            "ground_level",
            "formation_level",
            "rail_level",
            "cut_fill"
        ]

        for field in required_fields:

            if record.get(field) is None:

                return False, f"Missing {field}"

        return True, ""

            # -----------------------------------------
    # Check chainage increments
    # -----------------------------------------

    def check_chainage(self, records):

        errors = []

        for i in range(1, len(records)):

            previous = records[i - 1]["chainage"]
            current = records[i]["chainage"]

            if previous is None or current is None:
                continue

            if current - previous != 20:

                errors.append(
                    f"Chainage jump from {previous} to {current}"
                )

        return errors

            # -----------------------------------------
    # Check Cut/Fill calculation
    # -----------------------------------------

    def check_cut_fill(self, record, tolerance=0.05):

        gl = record.get("ground_level")
        fl = record.get("formation_level")
        cf = record.get("cut_fill")

        if gl is None or fl is None or cf is None:
            return False, "Missing values for Cut/Fill validation"

        expected = round(fl - gl, 3)

        if abs(expected - cf) <= tolerance:
            return True, ""

        return (
            False,
            f"Expected {expected}, OCR read {cf}"
        )

            # -----------------------------------------
    # Validate all records
    # -----------------------------------------

    def validate(self, records):

        validated = []

        chainage_errors = self.check_chainage(records)

        for index, record in enumerate(records):

            remarks = []

            ok, msg = self.check_missing(record)

            if not ok:
                remarks.append(msg)

            ok, msg = self.check_cut_fill(record)

            if not ok:
                remarks.append(msg)

            if index > 0:

                previous = records[index - 1]["chainage"]
                current = record["chainage"]

                if previous is not None and current is not None:

                    if current - previous != 20:
                        remarks.append(
                            "Invalid chainage interval"
                        )

            new_record = record.copy()

            if remarks:
                new_record["status"] = "REVIEW"
                new_record["remarks"] = "; ".join(remarks)
            else:
                new_record["status"] = "VALID"
                new_record["remarks"] = ""

            validated.append(new_record)

        return validated
