import re
import cv2
import numpy as np
import pytesseract
import os


class OCREngine:
    """
    Production OCR Engine
    Responsibilities:
    1. Preprocess cell
    2. Rotate image
    3. OCR
    4. Return cleaned text
    It DOES NOT:
    - Know about rows
    - Know about GL
    - Know about FL
    - Save to database
    """

    NUMBER_PATTERN = re.compile(r'^[+-]?\d{1,4}(\.\d{1,4})?$')

    def __init__(self, debug_dir="ocr_debug"):
        self.debug_dir = debug_dir
        os.makedirs(
            self.debug_dir,
            exist_ok=True
        )
        self.config = (
            "--psm 7 "
            "-c tessedit_char_whitelist=0123456789.-+"
        )

    def preprocess(self, cell):
        if cell is None:
            return None
        if cell.size == 0:
            return None
        if len(cell.shape) == 3:
            gray = cv2.cvtColor(
                cell,
                cv2.COLOR_BGR2GRAY
            )
        else:
            gray = cell.copy()
        gray = cv2.resize(
            gray,
            None,
            fx=3,
            fy=3,
            interpolation=cv2.INTER_CUBIC
        )
        gray = cv2.GaussianBlur(
            gray,
            (3, 3),
            0
        )
        return gray

    def rotate_clockwise(self, img):
        return cv2.rotate(
            img,
            cv2.ROTATE_90_CLOCKWISE
        )

    def rotate_counter_clockwise(self, img):
        return cv2.rotate(
            img,
            cv2.ROTATE_90_COUNTERCLOCKWISE
        )

    def remove_ruling_lines(self, binary_img):
        """
        Ticks/rules in these cells are long, thin, near-solid vertical
        strokes - unlike digits, which are short and blobby. A vertical
        morphological opening isolates only shapes that are almost the
        full height of the image, so it grabs the ruling line/tick
        without touching digit strokes, which are much shorter.
        binary_img: white background (255), black text/lines (0).
        """
        h = binary_img.shape[0]
        inverted = cv2.bitwise_not(binary_img)  # text/lines -> white
        kernel_len = max(5, int(h * 0.75))
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, kernel_len))
        lines_only = cv2.morphologyEx(inverted, cv2.MORPH_OPEN, vertical_kernel, iterations=1)
        cleaned_inverted = cv2.subtract(inverted, lines_only)
        cleaned = cv2.bitwise_not(cleaned_inverted)
        return cleaned

    def score_candidate(self, text):
        if not text:
            return -1
        stripped = text.strip()
        digit_count = sum(ch.isdigit() for ch in stripped)
        if digit_count == 0:
            return -1
        if digit_count < 4:
            return digit_count - 10
        junk_count = len(stripped) - digit_count - stripped.count('.')
        length_penalty = max(0, len(stripped) - 9) * 5
        score = digit_count - (junk_count * 3) - length_penalty
        if self.NUMBER_PATTERN.match(stripped):
            score += 50
        return score

    def read_text(self, img):
        candidates = []

        _, otsu = cv2.threshold(
            img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        candidates.append(otsu)

        adaptive = cv2.adaptiveThreshold(
            img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 21, 8
        )
        candidates.append(adaptive)

        _, inv = cv2.threshold(
            img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )
        candidates.append(inv)

        best = ""
        best_score = -1
        for candidate in candidates:
            cleaned = self.remove_ruling_lines(candidate)
            text = pytesseract.image_to_string(
                cleaned, config=self.config
            ).strip()
            score = self.score_candidate(text)
            if score > best_score:
                best = text
                best_score = score

        return best

    def read_cell(self, cell):
        processed = self.preprocess(cell)
        if processed is None:
            return ""

        cw = self.rotate_clockwise(processed)
        cw_text = self.read_text(cw)

        ccw = self.rotate_counter_clockwise(processed)
        ccw_text = self.read_text(ccw)

        if self.score_candidate(cw_text) >= self.score_candidate(ccw_text):
            return cw_text
        return ccw_text
