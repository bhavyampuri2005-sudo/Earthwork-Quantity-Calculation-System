from pdf2image import convert_from_path
import easyocr
import cv2
import numpy as np
from ocr.data_parser import parse_and_save, extract_chainage_range


# ─────────────────────────────────────────────────────
# FUNCTION 1 — Standardize Image Size
# Makes sure every PDF page is same width
# for consistent OCR results
# ─────────────────────────────────────────────────────
def standardize_image(img):
    target_width = 2480
    height, width = img.shape[:2]
    if width != target_width:
        scale = target_width / width
        new_height = int(height * scale)
        img = cv2.resize(img, (target_width, new_height))
        print(f"Standardized to: {target_width} x {new_height}")
    else:
        print(f"Image already standard width: {width}")
    return img


# ─────────────────────────────────────────────────────
# FUNCTION 2 — Fix Rotation
# Detects if image is tilted and corrects it
# so OCR reads text properly
# ─────────────────────────────────────────────────────
def fix_rotation(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
    coords = np.column_stack(np.where(binary > 0))

    if len(coords) == 0:
        print("No content found for rotation detection")
        return img

    angle = cv2.minAreaRect(coords)[-1]

    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    print(f"Detected rotation angle: {angle:.2f} degrees")

    if abs(angle) > 0.5:
        (h, w) = img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        img = cv2.warpAffine(
            img, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )
        print(f"Image rotated by {angle:.2f} degrees")
    else:
        print("No significant rotation — image is already upright")

    return img


# ─────────────────────────────────────────────────────
# FUNCTION 3 — Split PDF Into Sections (NEW)
# Splits the page into 5 parts:
# Notes, Legend, Tables → TEXT sections (EasyOCR)
# L-Section Drawing, Map Drawing → DRAWING sections (model later)
# ─────────────────────────────────────────────────────
def split_into_sections(img, page_num):
    height, width = img.shape[:2]
    print(f"Splitting {width}x{height} into sections...")

    sections = {
        # TEXT SECTIONS — EasyOCR reads these
        "notes":    img[0:int(height*0.35), 0:int(width*0.45)],
        "legend":   img[int(height*0.65):height, 0:int(width*0.45)],
        "tables":   img[0:int(height*0.5), int(width*0.55):width],

        # DRAWING SECTIONS — model to be decided by mentor
        "lsection_drawing": img[int(height*0.5):height, int(width*0.55):width],
        "map_drawing":      img[int(height*0.35):int(height*0.65), 0:int(width*0.55)]
    }

    # Save debug images for every section
    for name, section_img in sections.items():
        path = f"uploads/debug_{name}_page{page_num+1}.png"
        cv2.imwrite(path, section_img)
        print(f"Debug saved: {path}")

    return sections


# ─────────────────────────────────────────────────────
# FUNCTION 4 — Preprocess Image (NEW)
# Cleans image before OCR:
# grayscale → contrast → noise removal → thresholding
# ─────────────────────────────────────────────────────
def preprocess(img):
    # Convert to black and white
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Increase contrast — makes text stand out
    gray = cv2.convertScaleAbs(gray, alpha=1.5, beta=0)

    # Remove noise — smooths out scan artifacts
    gray = cv2.GaussianBlur(gray, (1, 1), 0)

    # Threshold — makes text pure black, background pure white
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

    return thresh


# ─────────────────────────────────────────────────────
# FUNCTION 5 — Read Text Section (NEW)
# Runs lightweight EasyOCR on a single section
# exactly as mentor asked — simple text OCR
# ─────────────────────────────────────────────────────
def read_text_section(reader, img, section_name, conf_threshold=0.6):
    print(f"\nReading {section_name} with EasyOCR...")

    # Preprocess image first
    thresh = preprocess(img)

    # Run EasyOCR
    results = reader.readtext(thresh)

    # Filter by confidence score
    texts = [text for (_, text, conf) in results if conf > conf_threshold]

    print(f"{section_name}: {len(texts)} texts found")
    print(f"Sample: {texts[:5]}")

    return texts


# ─────────────────────────────────────────────────────
# MAIN FUNCTION — Extract Chainage From PDF
# Full OCR pipeline:
# PDF → image → standardize → rotate → split sections
# → OCR text sections → find chainage range
# → extract GL/FL → save to database
# ─────────────────────────────────────────────────────
def extract_chainage_from_pdf(pdf_path: str, project_id: int):
    print(f"\nStarting OCR Pipeline: {pdf_path}")
    print(f"Project ID: {project_id}")

    # Step 1 - Convert PDF pages to high quality images
    print("\nStep 1: Converting PDF to 300 DPI images...")
    images = convert_from_path(pdf_path, dpi=300)
    print(f"Total pages found: {len(images)}")

    # Step 2 - Initialize EasyOCR once for all pages
    print("\nStep 2: Initializing EasyOCR...")
    reader = easyocr.Reader(['en'], gpu=False)
    print("EasyOCR ready!")

    all_saved = []
    all_skipped = []
    final_min_chainage = None
    final_max_chainage = None

    for page_num, image in enumerate(images):
        print(f"\n{'='*50}")
        print(f"PROCESSING PAGE {page_num + 1} of {len(images)}")
        print(f"{'='*50}")

        # Convert PIL image to OpenCV format
        img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        height, width = img.shape[:2]
        print(f"Original size: {width} x {height}")

        # Step 3 - Standardize image size
        print("\nStep 3: Standardizing image size...")
        img = standardize_image(img)

        # Step 4 - Fix rotation if needed
        print("\nStep 4: Checking and fixing rotation...")
        img = fix_rotation(img)

        # Step 5 - Split page into sections
        print("\nStep 5: Splitting into sections...")
        sections = split_into_sections(img, page_num)
        print(f"Sections created: {list(sections.keys())}")

        # ─────────────────────────────────────────
        # TEXT SECTIONS — Simple lightweight EasyOCR
        # As mentor instructed
        # ─────────────────────────────────────────

        # Read Notes section
        print("\n--- TEXT SECTION 1: NOTES ---")
        notes_texts = read_text_section(
            reader,
            sections["notes"],
            "NOTES",
            conf_threshold=0.5
        )

        # Read Legend section
        print("\n--- TEXT SECTION 2: LEGEND ---")
        legend_texts = read_text_section(
            reader,
            sections["legend"],
            "LEGEND",
            conf_threshold=0.5
        )

        # Read Tables section (most important — has chainage/GL/FL)
        print("\n--- TEXT SECTION 3: TABLES ---")
        tables_texts = read_text_section(
            reader,
            sections["tables"],
            "TABLES",
            conf_threshold=0.6
        )

        # ─────────────────────────────────────────
        # DRAWING SECTIONS — Skip for now
        
        # ─────────────────────────────────────────
        print("\n--- DRAWING SECTIONS ---")
        print("L-Section Drawing → SKIPPED (mentor will guide model)")
        print("Map Drawing → SKIPPED (mentor will guide model)")

        # Step 6 - Extract chainage range from Notes + Tables
        print("\nStep 6: Finding chainage range from title sheet...")
        all_header_texts = notes_texts + tables_texts
        min_chainage, max_chainage = extract_chainage_range(all_header_texts)
        final_min_chainage = min_chainage
        final_max_chainage = max_chainage

        if min_chainage and max_chainage:
            print(f"Chainage range found: {min_chainage} to {max_chainage}")
        else:
            print("WARNING: Chainage range not found in this page!")
            print("Will use fallback validation (any number > 1000)")

        # Step 7 - Extract chainage/GL/FL from Tables section
        print("\nStep 7: Extracting chainage/GL/FL from Tables...")
        saved, skipped = parse_and_save(
            tables_texts,
            project_id,
            min_chainage,
            max_chainage
        )
        all_saved.extend(saved)
        all_skipped.extend(skipped)

        print(f"\nPage {page_num+1} complete!")
        print(f"Rows saved so far: {len(all_saved)}")
        print(f"Rows skipped so far: {len(all_skipped)}")

    # Final summary
    print(f"\n{'='*50}")
    print(f"OCR PIPELINE COMPLETE!")
    print(f"Total pages processed: {len(images)}")
    print(f"Total rows saved: {len(all_saved)}")
    print(f"Total rows skipped: {len(all_skipped)}")
    print(f"{'='*50}")

    return {
        "message": "OCR complete!",
        "project_id": project_id,
        "total_pages": len(images),
        "sections_processed": {
            "text_sections": [
                "Notes",
                "Legend",
                "Tables"
            ],
            "drawing_sections": [
                "L-Section Drawing",
                "Map Drawing"
            ],
            "drawing_status": "Pending "
        },
        "chainage_range_detected": {
            "min": final_min_chainage,
            "max": final_max_chainage
        },
        "rows_saved": len(all_saved),
        "rows_skipped": len(all_skipped),
        "skipped_details": all_skipped
    }
