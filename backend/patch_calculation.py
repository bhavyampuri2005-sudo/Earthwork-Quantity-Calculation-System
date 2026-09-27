import pathlib

path = pathlib.Path("routes/calculation.py")
text = path.read_text()

old_model = '''class RunCalculationRequest(BaseModel):
    project_id: int
    review_csv_path: str = "review.csv"
    slope_master_path: str = "data/slope_master.json"'''

new_model = '''class RunCalculationRequest(BaseModel):
    project_id: int
    slope_master_path: str = "data/slope_master.json"


def _review_csv_path(project_id: int) -> str:
    if project_id == 1:
        return "review.csv"
    return f"review_{project_id}.csv"'''

assert text.count(old_model) == 1, "RunCalculationRequest block not found or not unique"
text = text.replace(old_model, new_model)

old_call = '''    _sync_slope_master_file(data.project_id, data.slope_master_path)

    try:
        result = compute(data.review_csv_path, data.slope_master_path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"CSV not found: {data.review_csv_path}"
        )'''

new_call = '''    review_csv_path = _review_csv_path(data.project_id)
    _sync_slope_master_file(data.project_id, data.slope_master_path)

    try:
        result = compute(review_csv_path, data.slope_master_path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"CSV not found: {review_csv_path}"
        )'''

assert text.count(old_call) == 1, "run_calculation body not found or not unique"
text = text.replace(old_call, new_call)

path.write_text(text)
print("Patched routes/calculation.py")
