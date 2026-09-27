from ocr.batch_ocr import BatchOCR

batch = BatchOCR()

results = batch.process(
    limit=None,
    save_json=True
)

print("\n================================")
print("Total OCR Results:", len(results))
print("================================")