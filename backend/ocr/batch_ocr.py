import os
import re
import cv2
import json

from ocr.ocr_engine import OCREngine
from ocr.cell_extractor import CellExtractor


class BatchOCR:

    OFFSETS = [0, -3, 3, -6, 6, -9, 9, -12, 12, -15]
    STRICT = re.compile(r"^(\d{3}\.\d{3}|\d{5})-?$")

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
        match = re.match(r"r(\\d+)_c(\\d+)", filename)
        if not match:
            return (float("inf"), float("inf"))
        row, col = match.groups()
        return (int(row), int(col))

    def read_with_offset_search(self, img):
        """
        Cells are saved wider than needed (CellExtractor.SEARCH_MARGIN extra
        px each side) specifically so we can try a small set of x-offsets
        here and keep the first one that reads as a clean value, instead of
        trusting one fixed crop position (empirically noisy, not constant).
        """
        h, w = img.shape[:2]
        margin = CellExtractor.SEARCH_MARGIN
        narrow_w = w - 2 * margin

        if narrow_w <= 0:
            return self.engine.read_cell(img)

        fallback = None
        for off in self.OFFSETS:
            cx1 = margin + off
            cx2 = cx1 + narrow_w
            if cx1 < 0 or cx2 > w:
                continue
            sub = img[:, cx1:cx2]
            text = self.engine.read_cell(sub)
            if fallback is None:
                fallback = text
            if text and self.STRICT.match(text.strip()):
                return text

        return fallback

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

            text = self.read_with_offset_search(img)

            results[filename] = text

            processed += 1

            if text and self.STRICT.match(text.strip()):
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
