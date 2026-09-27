from ocr.pipeline import OCRPipeline

pipeline = OCRPipeline()

records = pipeline.process(
    "uploads/80-85km (1).pdf",
    1
)

print(f"\nTotal Records: {len(records)}")