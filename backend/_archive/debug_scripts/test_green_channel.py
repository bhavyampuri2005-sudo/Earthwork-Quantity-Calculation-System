import cv2
import pytesseract

config = "--psm 7 -c tessedit_char_whitelist=0123456789.-+"

for name in ["r6_c7", "r6_c15", "r6_c40", "r6_c17", "r6_c36"]:
    img = cv2.imread(f"cells/{name}.png")
    if img is None:
        print(f"{name}: file missing"); continue

    for label, gray in [
        ("gray ", cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)),
        ("green", img[:, :, 1]),   # green channel: red ink appears darkest here
    ]:
        g = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        g = cv2.GaussianBlur(g, (3, 3), 0)
        rot = cv2.rotate(g, cv2.ROTATE_90_CLOCKWISE)
        _, th = cv2.threshold(rot, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        text = pytesseract.image_to_string(th, config=config).strip()
        print(f"{name} [{label}]: '{text}'")
    print()
