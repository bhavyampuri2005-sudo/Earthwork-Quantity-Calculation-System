import os
import re
import cv2
import json

from ocr.ocr_engine import OCREngine


class BatchOCR:

    def __init__(self, cells_dir="cells"):

        self.cells_dir = cells_dir
        self.engine = OCREngine()

    @staticmethod
    def cell_key(filename):
        """
        Extracts (row, col) as integers from a filename like 'r9_c12.png'
        so files sort in true grid order (r9_c2 before r9_c10),
        not lexicographic order (r9_c10 before r9_c2).
        """
        match = re.match(r"r(\d+)_c(\d+)", filename)
        if not match:
            # Push anything that doesn't match the pattern to the end
            # instead of crashing, so one bad filename doesn't kill the batch
            return (float("inf"), float("inf"))
        row, col = match.groups()
        return (int(row), int(col))

    def process(self, limit=None, save_json=False):

        results = {}

        files = sorted(
            (f for f in os.listdir(self.cells_dir) if f.endswith(".png")),
            key=self.cell_key
        )

        print(f"\nTotal Cells Found: {len(files)}\n")

        processed = 0
        success = 0
        failed = 0

        for filename in files:

            if limit is not None and processed >= limit:
                break

            path = os.path.join(
                self.cells_dir,
                filename
            )

            img = cv2.imread(path)

            if img is None:
                print(f"Could not read {filename}")
                failed += 1
                continue

            text = self.engine.read_cell(img)

            results[filename] = text

            processed += 1

            if text and any(ch.isdigit() for ch in text):
                success += 1
            else:
                failed += 1

            print(
                f"[{processed}] {filename} -> {text}"
            )

        print("\n==============================")
        print(f"Processed : {processed}")
        print(f"Success   : {success}")
        print(f"Failed    : {failed}")
        print("==============================")

        if save_json:

            with open(
                "ocr_results.json",
                "w"
            ) as f:

                json.dump(
                    results,
                    f,
                    indent=4
                )

            print("\nSaved OCR results to ocr_results.json")

        return results