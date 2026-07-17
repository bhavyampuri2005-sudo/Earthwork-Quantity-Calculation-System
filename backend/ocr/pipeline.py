from ocr.grid_detector import GridDetector
from ocr.cell_extractor import CellExtractor
from ocr.batch_ocr import BatchOCR
from ocr.parser import OCRParser
from ocr.validator import Validator
from ocr.record_mapper import RecordMapper
from services.chainage_service import ChainageService


class OCRPipeline:

    def __init__(self):

        self.parser = OCRParser()
        self.validator = Validator()
        self.mapper = RecordMapper()
        self.service = ChainageService()

    def process(self, pdf_path, project_id):

        print("\n========== OCR PIPELINE ==========\n")

        # ----------------------------------------
        # Step 1 - Grid Detection
        # ----------------------------------------

        print("Step 1 : Grid Detection")

        detector = GridDetector(pdf_path, dpi=300)

        detector.load_pdf()
        detector.crop_lsection()

        rows = detector.detect_horizontal_lines()
        columns = detector.detect_vertical_lines()

        print("Grid Detection Completed")

        # ----------------------------------------
        # Step 2 - Cell Extraction
        # ----------------------------------------

        print("\nStep 2 : Cell Extraction")

        extractor = CellExtractor()

        total_cells = extractor.extract_cells(
            detector.lsection,
            rows,
            columns
        )

        print(f"Cell Extraction Completed ({total_cells} cells)")

        # ----------------------------------------
        # Step 3 - Batch OCR
        # ----------------------------------------

        print("\nStep 3 : Batch OCR")

        batch = BatchOCR()

        # Final run (all cells)
        ocr_results = batch.process()

        print(f"OCR Completed ({len(ocr_results)} cells processed)")

        # ----------------------------------------
        # Step 4 - Parser
        # ----------------------------------------

        print("\nStep 4 : Parser")

        grouped_rows = self.parser.group_by_row(
            ocr_results
        )

        print("Detected OCR Rows:", sorted(grouped_rows.keys()))
        print(f"Grouped Rows : {len(grouped_rows)}")

        mapping = self.parser.assign_engineering_rows(
            grouped_rows
        )

        print("\nEngineering Row Mapping")

        for key, value in mapping.items():
            print(f"{key} -> Row {value}")

        records = self.parser.build_records(
            grouped_rows,
            mapping
        )

        print(f"\nEngineering Records Built : {len(records)}")

        for record in records[:5]:
            print(record)

        print("\n========== PIPELINE COMPLETE ==========\n")

        return records