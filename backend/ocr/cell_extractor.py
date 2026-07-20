import cv2
import os


class CellExtractor:
    """
    Extracts every grid cell using the detected
    horizontal rows and vertical columns.
    """

    # Extra horizontal margin saved beyond the normal inset, so batch_ocr.py
    # can search a small range of x-offsets per cell before OCR. Per-column
    # crop position is empirically noisy, not a fixed constant. Must match
    # the OFFSETS range used in batch_ocr.py.
    SEARCH_MARGIN = 18

    def __init__(self, output_dir="cells"):
        self.output_dir = output_dir
        os.makedirs(
            self.output_dir,
            exist_ok=True
        )

    def extract_cells(self, image, rows, columns, vertical_inset=0.15, horizontal_inset=0.05):
        print("\nExtracting Cells...")
        count = 0

        if len(rows) < 2:
            raise Exception("Not enough horizontal lines detected.")
        if len(columns) < 2:
            raise Exception("Not enough vertical lines detected.")

        img_h, img_w = image.shape[:2]

        for r in range(len(rows) - 1):
            y1 = rows[r]
            y2 = rows[r + 1]
            if y2 <= y1:
                continue

            for c in range(len(columns) - 1):
                x1 = columns[c]
                x2 = columns[c + 1]
                if x2 <= x1:
                    continue

                width = x2 - x1
                height = y2 - y1

                y_cut = int(height * vertical_inset)
                x_cut = int(width * horizontal_inset)

                cy1 = y1 + y_cut
                cy2 = y2 - y_cut
                cx1 = x1 + x_cut - self.SEARCH_MARGIN
                cx2 = x2 - x_cut + self.SEARCH_MARGIN

                cx1 = max(0, cx1)
                cx2 = min(img_w, cx2)

                if cx2 <= cx1 or cy2 <= cy1:
                    cx1, cx2, cy1, cy2 = x1, x2, y1, y2

                cell = image[cy1:cy2, cx1:cx2]
                if cell.size == 0:
                    continue

                filename = os.path.join(
                    self.output_dir,
                    f"r{r}_c{c}.png"
                )
                cv2.imwrite(
                    filename,
                    cell
                )
                count += 1

        print(f"Cells Saved: {count}")
        return count
