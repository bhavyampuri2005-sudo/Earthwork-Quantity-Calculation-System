import cv2
import numpy as np
from pdf2image import convert_from_path


class GridDetector:
    """
    Detects the L-section grid.
    Responsibilities:
    1. Load PDF
    2. Crop L-section
    3. Detect horizontal lines
    4. Detect vertical columns
    """

    def __init__(
        self,
        pdf_path,
        dpi=300,
        debug_dir="uploads"
    ):
        self.pdf_path = pdf_path
        self.dpi = dpi
        self.debug_dir = debug_dir

        self.image = None
        self.lsection = None

        self.rows = []
        self.columns = []
        self.chainages = []

    # -------------------------------------------------
    # Merge nearby detected lines
    # -------------------------------------------------

    @staticmethod
    def merge_close_lines(lines, threshold=30):

        if not lines:
            return []

        lines = sorted(lines)

        merged = [lines[0]]

        for value in lines[1:]:

            if abs(value - merged[-1]) > threshold:
                merged.append(value)

        return merged

    # -------------------------------------------------
    # Load PDF
    # -------------------------------------------------

    def load_pdf(self):

        print("Loading PDF...")

        images = convert_from_path(
            self.pdf_path,
            dpi=self.dpi
        )

        self.image = cv2.cvtColor(
            np.array(images[0]),
            cv2.COLOR_RGB2BGR
        )

        print("Image Shape:", self.image.shape)

  
    # Crop L-section
    # -------------------------------------------------

    def crop_lsection(self):

        if self.image is None:
            raise Exception("Call load_pdf() first")

        height, width = self.image.shape[:2]

        self.lsection = self.image[
            int(height * 0.62):int(height * 0.90),
            300:11700
        ]

        print(
            "L-section Shape:",
            self.lsection.shape
        )

        cv2.imwrite(
            f"{self.debug_dir}/debug_01_band.png",
            self.lsection
        )

        return self.lsection
    # -------------------------------------------------
    # Preprocess
    # -------------------------------------------------

    def preprocess(self):

        gray = cv2.cvtColor(
            self.lsection,
            cv2.COLOR_BGR2GRAY
        )

        binary = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            15,
            10
        )

        cv2.imwrite(
            f"{self.debug_dir}/debug_02_binary.png",
            binary
        )

        return binary

            # -------------------------------------------------
    # Detect horizontal grid lines
    # -------------------------------------------------

    def detect_horizontal_lines(self):

        binary = self.preprocess()

        horizontal_kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (150, 1)
        )

        horizontal = cv2.morphologyEx(
            binary,
            cv2.MORPH_OPEN,
            horizontal_kernel
        )

        cv2.imwrite(
            f"{self.debug_dir}/debug_03_horizontal.png",
            horizontal
        )

        contours, _ = cv2.findContours(
            horizontal,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        rows = []

        debug = self.lsection.copy()

        for cnt in contours:

            x, y, w, h = cv2.boundingRect(cnt)

            if w > 600:

                rows.append(y)

                cv2.rectangle(
                    debug,
                    (x, y),
                    (x + w, y + h),
                    (0, 255, 0),
                    2
                )

        rows = self.merge_close_lines(rows, threshold=30)

        for y in rows:

            cv2.putText(
                debug,
                str(y),
                (20, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 255),
                2
            )

        self.rows = rows

        cv2.imwrite(
            f"{self.debug_dir}/debug_04_rows.png",
            debug
        )

        print("Detected Rows:", rows)

        return rows

            # -------------------------------------------------
    # Detect vertical grid lines (20 m columns)
    # -------------------------------------------------

    def detect_vertical_lines(self):

        height, width = self.lsection.shape[:2]

        debug = self.lsection.copy()

        # Major km positions (already verified)
        major_cols = [
            720,   # 80 km
            2850,  # 81 km
            4980,  # 82 km
            7110,  # 83 km
            9240,  # 84 km
            11370  # 85 km
        ]

        # Build the full set of vertical gridline x-positions first
        # (251 lines = 250 major-span subdivisions + closing 85km line),
        # then take the MIDPOINT of each adjacent pair as the cell centre.
        # Sampling at the boundary lines themselves put column 0 on the
        # 80km axis line and opened a phantom trailing column past the
        # 85km line (both read blank/garbage across all rows) - the
        # r9 boundary bug. Midpoints give exactly 250 data cells, each
        # centred on its 20m station.
        boundaries = []

        for i in range(len(major_cols) - 1):

            start = major_cols[i]
            end = major_cols[i + 1]

            step = (end - start) / 50

            for j in range(50):
                boundaries.append(int(start + j * step))

        boundaries.append(major_cols[-1])

        cols = [
            (boundaries[k] + boundaries[k + 1]) // 2
            for k in range(len(boundaries) - 1)
        ]

        self.columns = cols

        # Draw debug image
        for x in cols:

            color = (0, 255, 0)

            if x in major_cols:
                color = (255, 0, 0)

            cv2.line(
                debug,
                (x, 0),
                (x, height),
                color,
                1
            )

        cv2.imwrite(
            f"{self.debug_dir}/debug_05_columns.png",
            debug
        )

        print("Columns detected:", len(cols))

        return cols