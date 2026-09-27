p = "/Users/bhavyampuri/Desktop/Earthwork Quantity Calculation System/frontend/app/upload/page.js"
src = open(p).read()

old = '''    const chStart = parseFloat(chainageStart);
    if (Number.isNaN(chStart)) {
      setError(
        "Chainage start is required — read it off the drawing's title block, it can't be reliably auto-detected from the scan."
      );
      return;
    }
    const chStep = parseFloat(chainageStep) || 20;'''

new = '''    // Optional: leave blank for multi-sheet CAD files (e.g. KRC-style)
    // whose chainage is read directly from the PDF text. Required only
    // for scanned drawings, which the backend enforces server-side.
    const chStart = chainageStart.trim() === "" ? undefined : parseFloat(chainageStart);
    if (chainageStart.trim() !== "" && Number.isNaN(chStart)) {
      setError("Chainage start must be a number, or leave it blank.");
      return;
    }
    const chStep = chainageStep.trim() === "" ? undefined : parseFloat(chainageStep);'''

if old not in src:
    print("page.js: PATTERN NOT FOUND - no change made")
else:
    open(p, "w").write(src.replace(old, new))
    print("page.js: patched - validation relaxed, blank is now allowed")
