import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database import get_db
from earthwork.calc_engine import compute
from services.chainage_service import ChainageService
from services.calculation_service import CalculationService

router = APIRouter()


def _sync_slope_master_file(project_id: int, slope_master_path: str):
    """
    Pulls SlopeMaster ranges for this project from the DB and writes them
    to the JSON file calc_engine.py's SlopeMaster class reads from. This
    makes the DB table (populated via POST /slope) the real source of
    truth, without changing calc_engine.py's file-reading interface.

    Each range now carries separate side_slope_cut / side_slope_fill
    values (confirmed by reviewer), matching the updated SlopeMaster
    class and the one-line calc_engine.py change that passes station
    type through to the slope lookup.
    """
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT from_chainage, to_chainage, side_slope_cut, side_slope_fill FROM SlopeMaster "
            "WHERE project_id = %s ORDER BY from_chainage",
            (project_id,),
        )
        rows = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    if not rows:
        raise HTTPException(
            status_code=400,
            detail=(
                f"No slope_master ranges found for project_id={project_id}. "
                "Add at least one range via POST /slope before running the calculation."
            ),
        )

    ranges = [
        {
            "from_chainage": float(r[0]),
            "to_chainage": float(r[1]),
            "side_slope_cut": float(r[2]),
            "side_slope_fill": float(r[3]),
        }
        for r in rows
    ]

    with open(slope_master_path, "w") as f:
        json.dump(ranges, f, indent=2)


class RunCalculationRequest(BaseModel):
    project_id: int
    review_csv_path: str = "review.csv"
    slope_master_path: str = "data/slope_master.json"


def _clear_previous_run(project_id: int):
    """
    Deletes any existing ChainageProfile / EarthworkCalculation rows for
    this project before inserting fresh ones, so re-running /calculation/run
    (e.g. after fixing an OCR value or a slope entry) REPLACES the previous
    result instead of appending duplicate rows alongside it.
    """
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM ChainageProfile WHERE project_id = %s", (project_id,))
        cursor.execute("DELETE FROM EarthworkCalculation WHERE project_id = %s", (project_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


@router.post("/calculation/run")
def run_calculation(data: RunCalculationRequest):
    """
    Runs the Average End Area calc engine against a reviewed CSV and
    persists results to:
      - ChainageProfile     : one row per station (gl, fl, cut/fill DEPTH)
      - EarthworkCalculation: one row per interval (area, volume, type)

    Idempotent per project_id: any existing rows for this project are
    cleared before the new results are inserted, so calling this again
    (e.g. after a CSV or slope_master correction) replaces the prior run
    instead of duplicating rows alongside it.

    Pulls side-slope values (separate cut/fill) from the SlopeMaster DB
    table - see _sync_slope_master_file for how that's bridged in.

    Assumes calc_engine.py lives at earthwork/calc_engine.py alongside
    earthwork/slope_master.py (per the SlopeMaster import inside it).
    Adjust the import above if your package layout differs.
    """
    _sync_slope_master_file(data.project_id, data.slope_master_path)

    try:
        result = compute(data.review_csv_path, data.slope_master_path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"CSV not found: {data.review_csv_path}"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Clear any prior run for this project so we replace, not duplicate.
    _clear_previous_run(data.project_id)

    # --- ChainageProfile: per-station gl/fl/cut-depth/fill-depth ---
    station_records = []
    for s in result["stations"]:
        if s["complete"]:
            cut = s["h"] if s["type"] == "cut" else 0.0
            fill = s["h"] if s["type"] == "fill" else 0.0
            gl, fl = s["gl"], s["fl"]
        else:
            cut, fill, gl, fl = 0.0, 0.0, None, None
        station_records.append(
            {
                "project_id": data.project_id,
                "chainage": s["chainage"],
                "gl": gl,
                "fl": fl,
                "fill": fill,
                "cut": cut,
            }
        )

    chainage_service = ChainageService()
    stations_saved = chainage_service.save_records(station_records)

    # --- EarthworkCalculation: per-interval area/volume/type ---
    station_area_by_chainage = {
        s["chainage"]: s["area"] for s in result["stations"] if s["complete"]
    }

    interval_rows = []
    for iv in result["intervals"]:
        area = None
        if iv["from"] in station_area_by_chainage and iv["to"] in station_area_by_chainage:
            area = (
                station_area_by_chainage[iv["from"]] + station_area_by_chainage[iv["to"]]
            ) / 2
        interval_rows.append(
            {
                "from": iv["from"],
                "to": iv["to"],
                "type": iv["type"],
                "volume": iv["volume"],
                "area": area,
            }
        )

    calculation_service = CalculationService()
    intervals_saved = calculation_service.save_intervals(data.project_id, interval_rows)

    return {
        "message": "Calculation run and persisted.",
        "project_id": data.project_id,
        "stations_saved": stations_saved,
        "intervals_saved": intervals_saved,
        "total_cut_volume": round(result["total_cut_volume"], 3),
        "total_fill_volume": round(result["total_fill_volume"], 3),
        "stations_reviewed": result["complete_stations"],
        "stations_pending": result["pending_stations"],
    }


@router.get("/calculation/{project_id}")
def get_calculation(project_id: int):
    """
    Read back the stored intervals for a project plus cut/fill totals,
    computed by summing the persisted interval volumes. Powers the
    frontend dashboard.
    """
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id, chainage, area, volume, type FROM EarthworkCalculation "
            "WHERE project_id = %s ORDER BY chainage ASC, id ASC",
            (project_id,),
        )
        rows = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    intervals = []
    total_cut = 0.0
    total_fill = 0.0
    pending = 0
    for r in rows:
        volume = float(r[3]) if r[3] is not None else None
        itype = r[4]
        if itype == "cut" and volume is not None:
            total_cut += volume
        elif itype == "fill" and volume is not None:
            total_fill += volume
        elif itype == "pending_review":
            pending += 1
        intervals.append(
            {
                "id": r[0],
                "chainage": float(r[1]),
                "area": float(r[2]) if r[2] is not None else None,
                "volume": volume,
                "type": itype,
            }
        )

    return {
        "project_id": project_id,
        "intervals": intervals,
        "total_cut_volume": round(total_cut, 3),
        "total_fill_volume": round(total_fill, 3),
        "pending_intervals": pending,
    }
