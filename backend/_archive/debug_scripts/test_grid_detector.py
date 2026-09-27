from ocr.grid_detector import GridDetector

detector = GridDetector(
    pdf_path="uploads/80-85km (1).pdf",
    dpi=100
)

detector.load_pdf()
detector.crop_lsection()

detector.detect_horizontal_lines()
detector.detect_vertical_lines()