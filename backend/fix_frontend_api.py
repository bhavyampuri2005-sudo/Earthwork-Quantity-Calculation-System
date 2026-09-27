p = "/Users/bhavyampuri/Desktop/Earthwork Quantity Calculation System/frontend/lib/api.js"
src = open(p).read()

old = '''  uploadPdf: async (projectId, file, chainageStart, chainageStep = 20) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("chainage_start", String(chainageStart));
    formData.append("chainage_step", String(chainageStep));'''

new = '''  uploadPdf: async (projectId, file, chainageStart, chainageStep) => {
    const formData = new FormData();
    formData.append("file", file);
    // chainage_start/step are optional: leave them out entirely for
    // multi-sheet CAD files (e.g. KRC-style) whose chainage is read
    // directly from the PDF text. Sending "undefined"/"NaN" as a string
    // is worse than omitting the field.
    if (chainageStart !== undefined && chainageStart !== null && !Number.isNaN(chainageStart)) {
      formData.append("chainage_start", String(chainageStart));
    }
    if (chainageStep !== undefined && chainageStep !== null && !Number.isNaN(chainageStep)) {
      formData.append("chainage_step", String(chainageStep));
    }'''

if old not in src:
    print("api.js: PATTERN NOT FOUND - no change made")
else:
    open(p, "w").write(src.replace(old, new))
    print("api.js: patched - chainage_start/step now optional")
