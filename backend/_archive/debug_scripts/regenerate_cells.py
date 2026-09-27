from ocr.grid_detector import GridDetector
from ocr.cell_extractor import CellExtractor

PDF_PATH = "uploads/80-85km (1).pdf"

print("Step 1: Grid Detection")
detector = GridDetector(PDF_PATH)
detector.load_pdf()
detector.crop_lsection()
rows = detector.detect_horizontal_lines()
columns = detector.detect_vertical_lines()
print(f"Rows detected: {len(rows)}, Columns detected: {len(columns)}")

print("\nStep 2: Cell Extraction (with fixed inset crop)")
extractor = CellExtractor()
total = extractor.extract_cells(detector.lsection, rows, columns)
print(f"Cells extracted: {total}")
