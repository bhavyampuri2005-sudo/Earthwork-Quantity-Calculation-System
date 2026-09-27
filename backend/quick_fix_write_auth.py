import re

files = ["routes/calculation.py", "routes/chainage.py", "routes/projects.py",
          "routes/review.py", "routes/slope.py", "routes/upload.py"]

pattern = re.compile(r',\s*user:\s*dict\s*=\s*Depends\(require_role\([^)]*\)\)')

for path in files:
    with open(path) as f:
        content = f.read()
    new_content, count = pattern.subn("", content)
    if count == 0:
        print(f"{path}: NO CHANGE (unexpected)")
    else:
        with open(path, "w") as f:
            f.write(new_content)
        print(f"{path}: updated ({count} route(s))")
