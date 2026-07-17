import requests
import re


# ─────────────────────────────────────────────────────
# FUNCTION 1 — Check if Text is a Number
# ─────────────────────────────────────────────────────
def is_number(text):
    try:
        float(text.strip().replace(',', '.'))
        return True
    except:
        return False


# ─────────────────────────────────────────────────────
# FUNCTION 2 — Extract Chainage Range From Title Sheet
# 4 patterns to find chainage range
# ─────────────────────────────────────────────────────
def extract_chainage_range(raw_texts):
    print("Looking for chainage range in title sheet...")
    text_joined = " ".join(raw_texts)
    print(f"Searching in text: {text_joined[:300]}")

    # Pattern 1 - FROM CHAINAGE 80000 TO CHAINAGE 85000
    pattern1 = r'FROM\s+CHAINAGE\s+([\d.]+).*?TO\s+CHAINAGE\s+([\d.]+)'
    match1 = re.search(pattern1, text_joined, re.IGNORECASE)
    if match1:
        min_ch = float(match1.group(1))
        max_ch = float(match1.group(2))
        if min_ch > 1000 and max_ch > 1000:
            print(f"Pattern 1 found: {min_ch} to {max_ch}")
            return min_ch, max_ch

    # Pattern 2 - CHAINAGE 80000.0 TO CHAINAGE 85000
    pattern2 = r'CHAINAGE\s+([\d]+\.?[\d]*)\s+TO\s+CHAINAGE\s+([\d]+\.?[\d]*)'
    match2 = re.search(pattern2, text_joined, re.IGNORECASE)
    if match2:
        min_ch = float(match2.group(1))
        max_ch = float(match2.group(2))
        if min_ch > 1000 and max_ch > 1000:
            print(f"Pattern 2 found: {min_ch} to {max_ch}")
            return min_ch, max_ch

    # Pattern 3 - KM range like 80-85km
    pattern3 = r'(\d+)\s*[-–]\s*(\d+)\s*[Kk][Mm]'
    match3 = re.search(pattern3, text_joined, re.IGNORECASE)
    if match3:
        min_km = float(match3.group(1))
        max_km = float(match3.group(2))
        min_ch = min_km * 1000
        max_ch = max_km * 1000
        print(f"Pattern 3 KM: {min_km}km-{max_km}km = {min_ch}m-{max_ch}m")
        return min_ch, max_ch

    # Pattern 4 - Any numbers > 1000 near word CHAINAGE
    pattern4 = r'CHAINAGE\s+([\d.]+)'
    all_matches = re.findall(pattern4, text_joined, re.IGNORECASE)
    large_numbers = [float(m) for m in all_matches if float(m) > 1000]
    if len(large_numbers) >= 2:
        min_ch = min(large_numbers)
        max_ch = max(large_numbers)
        print(f"Pattern 4 found: {min_ch} to {max_ch}")
        return min_ch, max_ch

    print("WARNING: No valid chainage range found")
    return None, None


# ─────────────────────────────────────────────────────
# FUNCTION 3 — Extract GL and FL Values (NEW)
# Specifically looks for GL and FL patterns
# in the OCR text from tables section
# Handles patterns like:
# "GL: 235.557" or "GL 235.557"
# "FL: 234.504" or "FL 234.504"
# or just sequences of decimal numbers
# ─────────────────────────────────────────────────────
def extract_gl_fl_values(raw_texts):
    """
    Extracts GL and FL values from tables section text.
    Tries pattern matching first, then falls back to
    sequential number extraction.
    """
    print("\nExtracting GL and FL values...")
    text_joined = " ".join(raw_texts)

    gl_values = []
    fl_values = []

    # Pattern 1 - GL: 235.557 or GL 235.557
    gl_pattern = r'GL[:\s]+(\d+\.?\d*)'
    gl_matches = re.findall(gl_pattern, text_joined, re.IGNORECASE)
    if gl_matches:
        gl_values = [float(v) for v in gl_matches]
        print(f"Found GL values via pattern: {gl_values[:5]}")

    # Pattern 2 - FL: 234.504 or FL 234.504
    fl_pattern = r'FL[:\s]+(\d+\.?\d*)'
    fl_matches = re.findall(fl_pattern, text_joined, re.IGNORECASE)
    if fl_matches:
        fl_values = [float(v) for v in fl_matches]
        print(f"Found FL values via pattern: {fl_values[:5]}")

    if gl_values and fl_values:
        print(f"GL values found: {len(gl_values)}")
        print(f"FL values found: {len(fl_values)}")
        return gl_values, fl_values

    # Fallback - if no GL/FL labels found
    # extract all decimal numbers with 3 decimal places
    # these are likely elevation values
    decimal_pattern = r'\d{2,3}\.\d{3}'
    all_decimals = re.findall(decimal_pattern, text_joined)
    decimals = [float(d) for d in all_decimals]

    print(f"Fallback decimal values found: {decimals[:10]}")
    return [], []


# ─────────────────────────────────────────────────────
# FUNCTION 4 — Validate a Row
# GL/FL elevation NOT checked — changes per project
# Only chainage range and basic positivity checked
# ─────────────────────────────────────────────────────
def validate_row(chainage, gl, fl, min_chainage=None, max_chainage=None):

    # Check chainage is within project range
    if min_chainage is not None and max_chainage is not None:
        if chainage < min_chainage or chainage > max_chainage:
            return False, f"Chainage {chainage} outside project range {min_chainage} to {max_chainage}"
    else:
        if chainage < 1000 or chainage > 9999999:
            return False, "Chainage not a valid large number"

    # GL must be positive — no elevation range limit
    if gl <= 0:
        return False, "GL must be a positive value"

    # FL must be positive — no elevation range limit
    if fl <= 0:
        return False, "FL must be a positive value"

    # Difference should not be unrealistically large
    if abs(gl - fl) > 50:
        return False, f"GL-FL difference {abs(gl-fl):.3f} is unrealistically large"

    return True, "OK"


# ─────────────────────────────────────────────────────
# FUNCTION 5 — Save Skipped Row
# Saves invalid rows to SkippedRows table
# so engineer can spot check occasionally
# ─────────────────────────────────────────────────────
def save_skipped_row(project_id, chainage, gl, fl, reason):
    try:
        requests.post(
            "http://127.0.0.1:8000/review/skip",
            json={
                "project_id": project_id,
                "raw_chainage": str(chainage),
                "raw_gl": str(gl),
                "raw_fl": str(fl),
                "reason": reason
            }
        )
    except Exception as e:
        print(f"Could not save skipped row: {e}")


# ─────────────────────────────────────────────────────
# FUNCTION 6 — Parse and Save (UPDATED)
# Now has 2 strategies:
# Strategy 1 → GL/FL pattern matching (if labels found)
# Strategy 2 → Sequential number extraction (fallback)
# ─────────────────────────────────────────────────────
def parse_and_save(raw_texts: list, project_id: int, min_chainage=None, max_chainage=None):
    print("\nParsing OCR output...")
    print(f"Using chainage range: {min_chainage} to {max_chainage}")

    # Extract only numbers from raw OCR text
    numbers = []
    for text in raw_texts:
        cleaned = text.strip().replace(',', '.')
        if is_number(cleaned):
            numbers.append(float(cleaned))

    print(f"Total numbers from OCR: {len(numbers)}")
    print(f"Numbers sample: {numbers[:10]}")

    # Try Strategy 1 — GL/FL pattern matching
    gl_values, fl_values = extract_gl_fl_values(raw_texts)

    saved_rows = []
    skipped_rows = []

    # ─────────────────────────────────────────
    # STRATEGY 1 — Use GL/FL labels if found
    # Most accurate — uses explicit GL/FL markers
    # ─────────────────────────────────────────
    if gl_values and fl_values:
        print("\nUsing Strategy 1 — GL/FL pattern matching")

        # Extract chainages — large numbers in correct range
        chainages = []
        for num in numbers:
            if min_chainage is not None and max_chainage is not None:
                if min_chainage <= num <= max_chainage:
                    chainages.append(num)
            else:
                if num > 1000:
                    chainages.append(num)

        print(f"Chainages found: {chainages[:5]}")
        print(f"GL values: {gl_values[:5]}")
        print(f"FL values: {fl_values[:5]}")

        # Match chainage with GL and FL by position
        min_len = min(len(chainages), len(gl_values), len(fl_values))
        for idx in range(min_len):
            chainage = chainages[idx]
            gl = gl_values[idx]
            fl = fl_values[idx]

            # Calculate diff ourselves
            diff = round(gl - fl, 3)
            fill = round(max(0, diff), 3)
            cut = round(abs(min(0, diff)), 3)

            is_valid, reason = validate_row(
                chainage, gl, fl,
                min_chainage, max_chainage
            )

            if is_valid:
                row = {
                    "project_id": project_id,
                    "chainage": chainage,
                    "gl": gl,
                    "fl": fl,
                    "fill": fill,
                    "cut": cut
                }
                try:
                    response = requests.post(
                        "http://127.0.0.1:8000/chainage",
                        json=row
                    )
                    if response.status_code == 200:
                        saved_rows.append(row)
                        print(f"Saved: ch={chainage} gl={gl} fl={fl} fill={fill} cut={cut}")
                    else:
                        print(f"API rejected: {response.text}")
                except Exception as e:
                    print(f"API error: {e}")
            else:
                skipped = {
                    "chainage": chainage,
                    "gl": gl,
                    "fl": fl,
                    "reason": reason
                }
                skipped_rows.append(skipped)
                save_skipped_row(project_id, chainage, gl, fl, reason)
                print(f"Skipped: ch={chainage} reason={reason}")

    # ─────────────────────────────────────────
    # STRATEGY 2 — Sequential number extraction
    # Fallback when no GL/FL labels found
    # Looks for chainage then takes next 2 as GL/FL
    # ─────────────────────────────────────────
    else:
        print("\nUsing Strategy 2 — Sequential number extraction")
        i = 0
        while i < len(numbers):
            current = numbers[i]

            # Identify chainage
            if min_chainage is not None and max_chainage is not None:
                is_chainage = (min_chainage <= current <= max_chainage)
            else:
                is_chainage = current > 1000

            if is_chainage:
                chainage = current

                if i + 2 < len(numbers):
                    gl = numbers[i + 1]
                    fl = numbers[i + 2]

                    # Calculate diff ourselves
                    diff = round(gl - fl, 3)
                    fill = round(max(0, diff), 3)
                    cut = round(abs(min(0, diff)), 3)

                    is_valid, reason = validate_row(
                        chainage, gl, fl,
                        min_chainage, max_chainage
                    )

                    if is_valid:
                        row = {
                            "project_id": project_id,
                            "chainage": chainage,
                            "gl": gl,
                            "fl": fl,
                            "fill": fill,
                            "cut": cut
                        }
                        try:
                            response = requests.post(
                                "http://127.0.0.1:8000/chainage",
                                json=row
                            )
                            if response.status_code == 200:
                                saved_rows.append(row)
                                print(f"Saved: ch={chainage} gl={gl} fl={fl} fill={fill} cut={cut}")
                            else:
                                print(f"API rejected: {response.text}")
                        except Exception as e:
                            print(f"API error: {e}")
                        i += 3
                    else:
                        skipped = {
                            "chainage": chainage,
                            "gl": gl,
                            "fl": fl,
                            "reason": reason
                        }
                        skipped_rows.append(skipped)
                        save_skipped_row(project_id, chainage, gl, fl, reason)
                        print(f"Skipped: ch={chainage} reason={reason}")
                        i += 1
                else:
                    i += 1
            else:
                i += 1

    print(f"\nParsing complete!")
    print(f"Strategy used: {'GL/FL Pattern' if gl_values and fl_values else 'Sequential'}")
    print(f"Saved: {len(saved_rows)} | Skipped: {len(skipped_rows)}")
    return saved_rows, skipped_rows