files = ["routes/audit.py", "routes/calculation.py", "routes/chainage.py",
         "routes/projects.py", "routes/review.py", "routes/slope.py"]

for path in files:
    with open(path) as f:
        content = f.read()
    before = content
    content = content.replace(", user: dict = Depends(get_current_user)", "")
    content = content.replace("user: dict = Depends(get_current_user)", "")
    if content == before:
        print(f"{path}: NO CHANGE (unexpected)")
    else:
        with open(path, "w") as f:
            f.write(content)
        print(f"{path}: updated")
