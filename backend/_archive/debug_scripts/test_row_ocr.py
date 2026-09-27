import easyocr
import cv2

reader = easyocr.Reader(['en'], gpu=False)

rows = [
    "row_13.png",   # Prop Formation Level
    "row_14.png",   # Prop Rail Level
    "row_15.png",   # Ground Level
    "row_16.png"    # Field Chainage
]

for row_file in rows:
    print("\n" + "="*50)
    print(row_file)

    img = cv2.imread(row_file)

    result = reader.readtext(
        img,
        detail=0,
        paragraph=False
    )

    print(result[:50])