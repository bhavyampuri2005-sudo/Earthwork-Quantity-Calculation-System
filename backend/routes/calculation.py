import csv
import io
import json
import os
import tempfile

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Font
from pydantic import BaseModel

from database import get_db
from earthwork.calc_engine import compute
from routes.auth import get_current_user, require_role
from routes.upload import _review_csv_path
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
    review_csv_path: Optional[str] = None
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

    review_csv_path is optional now - if not passed, it's derived from
    project_id via upload.py's _review_csv_path(), the same helper the
    upload endpoint uses to WRITE the file in the first place, so read
    and write finally agree on where a project's CSV lives.
    """
    _sync_slope_master_file(data.project_id, data.slope_master_path)

    csv_path = data.review_csv_path or _review_csv_path(data.project_id)

    try:
        result = compute(csv_path, data.slope_master_path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"CSV not found: {csv_path}"
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


def _merge_slope_ranges(ranges_by_project, ids):
    """
    Merges SlopeMaster ranges from multiple projects into one
    non-overlapping list, using the same "later project in the list
    wins" rule as the station merge below - so a chainage's slope
    always comes from the same project as its station data at any
    overlap. SlopeMaster.get_slope() itself can't be trusted to do
    this correctly: it returns the FIRST range (in from_chainage
    order) that covers a chainage, which favors whichever project
    happens to have the smaller from_chainage, not necessarily the
    "later" one.

    Implemented as interval clipping: each new project's ranges are
    added in full, and any earlier-added range they overlap is
    trimmed down to only its non-overlapping remainder (or dropped
    entirely if fully contained).

    ranges_by_project: {project_id: [(from, to, cut_slope, fill_slope), ...]}
    ids: ordered list of project_ids, later = higher priority
    Returns: [(from, to, cut_slope, fill_slope, source_project_id), ...]
    sorted by from_chainage.
    """
    merged = []
    for pid in ids:
        for (nf, nt, ncut, nfill) in ranges_by_project.get(pid, []):
            clipped = []
            for (ef, et, ecut, efill, esrc) in merged:
                if et <= nf or ef >= nt:
                    clipped.append((ef, et, ecut, efill, esrc))
                else:
                    if ef < nf:
                        clipped.append((ef, nf, ecut, efill, esrc))
                    if et > nt:
                        clipped.append((nt, et, ecut, efill, esrc))
            merged = clipped
            merged.append((nf, nt, ncut, nfill, pid))
    merged.sort(key=lambda r: r[0])
    return merged


@router.get("/calculation/combined/export")
def export_combined(project_ids: str):
    """
    Combines data from multiple projects into one .xlsx - meant for
    one physical alignment split across several Project records (e.g.
    separate uploaded sheets), not for genuinely unrelated projects.

    project_ids: comma-separated, in the order LATER overrides EARLIER
    at any overlapping chainage - e.g. "5,6,7" means project 7's data
    wins over project 6's at any chainage present in both, for both
    stations and slope ranges.

    Sheet 1 "Stations": merged ChainageProfile rows, Source Project
    column shows provenance per row.

    Sheet 2 "Volumes": SlopeMaster ranges are merged with the same
    later-wins rule (see _merge_slope_ranges), then the merged
    stations + merged ranges are written to temp files and run
    through the existing, unmodified compute() - reusing the real
    calc engine rather than re-deriving volume math here, so results
    stay consistent with every other calculation in the system. If
    slope coverage is missing or incomplete for the combined range,
    the Volumes sheet explains why instead of failing the whole
    export - the Stations sheet doesn't depend on slope data at all.
    """
    try:
        ids = [int(x.strip()) for x in project_ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="project_ids must be comma-separated integers, e.g. 5,6,7",
        )

    if not ids:
        raise HTTPException(
            status_code=400,
            detail="project_ids is required, e.g. ?project_ids=5,6,7",
        )

    merged_stations = {}
    contributed = {}
    for pid in ids:
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT chainage, gl, fl, fill, cut FROM ChainageProfile "
                "WHERE project_id = %s ORDER BY chainage ASC",
                (pid,),
            )
            rows = cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

        contributed[pid] = len(rows)
        for r in rows:
            merged_stations[float(r[0])] = (pid, r[0], r[1], r[2], r[3], r[4])

    if not merged_stations:
        raise HTTPException(
            status_code=404,
            detail=f"No ChainageProfile data found for any of project_ids={ids}.",
        )

    wb = Workbook()
    header_font = Font(bold=True)

    ws = wb.active
    ws.title = "Stations"
    ws.append(["Chainage", "Ground Level", "Formation Level", "Fill (m)", "Cut (m)", "Source Project"])
    for cell in ws[1]:
        cell.font = header_font
    for chainage in sorted(merged_stations.keys()):
        pid, ch, gl, fl, fill, cut = merged_stations[chainage]
        ws.append(
            [
                float(ch),
                float(gl) if gl is not None else None,
                float(fl) if fl is not None else None,
                float(fill) if fill is not None else None,
                float(cut) if cut is not None else None,
                pid,
            ]
        )

    ws.append([])
    row = ws.max_row + 1
    ws.cell(row=row, column=1, value="Per-project station count").font = header_font
    for i, pid in enumerate(ids):
        ws.cell(row=row, column=2 + i, value=f"project {pid}: {contributed[pid]}")

    # --- Volumes: merge SlopeMaster ranges, then reuse the real compute() ---
    slope_ranges_by_project = {}
    for pid in ids:
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT from_chainage, to_chainage, side_slope_cut, side_slope_fill "
                "FROM SlopeMaster WHERE project_id = %s ORDER BY from_chainage",
                (pid,),
            )
            rows = cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
        slope_ranges_by_project[pid] = [
            (float(r[0]), float(r[1]), float(r[2]), float(r[3])) for r in rows
        ]

    merged_ranges = _merge_slope_ranges(slope_ranges_by_project, ids)

    volumes_error = None
    calc_result = None
    if not merged_ranges:
        volumes_error = f"No SlopeMaster ranges found for any of project_ids={ids}."
    else:
        csv_fd, csv_path = tempfile.mkstemp(suffix=".csv")
        json_fd, json_path = tempfile.mkstemp(suffix=".json")
        try:
            with os.fdopen(csv_fd, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["index", "chainage", "ground_level", "formation_level"])
                for i, chainage in enumerate(sorted(merged_stations.keys())):
                    _, ch, gl, fl, _fill, _cut = merged_stations[chainage]
                    w.writerow([i, ch, gl if gl is not None else "", fl if fl is not None else ""])

            with os.fdopen(json_fd, "w") as f:
                json.dump(
                    [
                        {
                            "from_chainage": r[0],
                            "to_chainage": r[1],
                            "side_slope_cut": r[2],
                            "side_slope_fill": r[3],
                        }
                        for r in merged_ranges
                    ],
                    f,
                )

            calc_result = compute(csv_path, json_path)
        except ValueError as e:
            volumes_error = str(e)
        finally:
            os.unlink(csv_path)
            os.unlink(json_path)

    volumes_ws = wb.create_sheet("Volumes")
    if volumes_error:
        volumes_ws.append(["Volumes could not be computed"])
        volumes_ws["A1"].font = header_font
        volumes_ws.append([volumes_error])
        volumes_ws.append(["Stations sheet is unaffected - it doesn't depend on slope data."])
    else:
        volumes_ws.append(["From Chainage", "To Chainage", "Type", "Volume (m3)"])
        for cell in volumes_ws[1]:
            cell.font = header_font
        for iv in calc_result["intervals"]:
            volumes_ws.append([iv["from"], iv["to"], iv["type"], iv["volume"]])

        volumes_ws.append([])
        net_volume = round(calc_result["total_fill_volume"] - calc_result["total_cut_volume"], 3)
        summary_rows = [
            ("Total Cut Volume (m3)", round(calc_result["total_cut_volume"], 3)),
            ("Total Fill Volume (m3)", round(calc_result["total_fill_volume"], 3)),
            ("Net (Fill - Cut) (m3)", net_volume),
        ]
        for label, value in summary_rows:
            r = volumes_ws.max_row + 1
            volumes_ws.cell(row=r, column=1, value=label).font = header_font
            volumes_ws.cell(row=r, column=2, value=value)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    filename = f"combined_{'_'.join(str(i) for i in ids)}.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def _get_calculation_data(project_id: int) -> dict:
    """
    The actual read-back-intervals-plus-totals logic, with no auth
    dependency of its own. Split out from get_calculation() so
    export_calculation() can call it directly - calling a route
    function that has Depends(...) in its signature bypasses FastAPI's
    dependency injection entirely, leaving that parameter as an
    unresolved Depends object instead of a real value.
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


@router.get("/calculation/{project_id}")
def get_calculation(project_id: int):
    """
    Read back the stored intervals for a project plus cut/fill totals,
    computed by summing the persisted interval volumes. Powers the
    frontend dashboard.
    """
    return _get_calculation_data(project_id)


@router.get("/calculation/{project_id}/export")
def export_calculation(project_id: int):
    """
    Exports a project's review data and calculation results as an
    .xlsx workbook (SRS FR-09).

    Sheet 1 "Stations": chainage/gl/fl/fill/cut per station, read
    directly from ChainageProfile - the same source Station Review
    displays.

    Sheet 2 "Volumes": per-interval area/volume/type, built by calling
    _get_calculation_data() directly rather than re-querying, so the
    exported numbers can never drift from the on-screen dashboard.
    Cut/fill/net totals and the pending-interval count are appended
    below the rows.

    Reflects whatever /calculation/run last persisted - does not
    re-run the calc engine.
    """
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT chainage, gl, fl, fill, cut FROM ChainageProfile "
            "WHERE project_id = %s ORDER BY chainage ASC",
            (project_id,),
        )
        station_rows = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    if not station_rows:
        raise HTTPException(
            status_code=404,
            detail=f"No ChainageProfile data found for project_id={project_id}. Run the calculation first.",
        )

    calc = _get_calculation_data(project_id)

    wb = Workbook()
    header_font = Font(bold=True)

    stations_ws = wb.active
    stations_ws.title = "Stations"
    stations_ws.append(["Chainage", "Ground Level", "Formation Level", "Fill (m)", "Cut (m)"])
    for cell in stations_ws[1]:
        cell.font = header_font
    for r in station_rows:
        stations_ws.append(
            [
                float(r[0]),
                float(r[1]) if r[1] is not None else None,
                float(r[2]) if r[2] is not None else None,
                float(r[3]) if r[3] is not None else None,
                float(r[4]) if r[4] is not None else None,
            ]
        )

    volumes_ws = wb.create_sheet("Volumes")
    volumes_ws.append(["Chainage", "Type", "Area", "Volume (m3)"])
    for cell in volumes_ws[1]:
        cell.font = header_font
    for iv in calc["intervals"]:
        volumes_ws.append([iv["chainage"], iv["type"], iv["area"], iv["volume"]])

    volumes_ws.append([])
    net_volume = round(calc["total_fill_volume"] - calc["total_cut_volume"], 3)
    summary_rows = [
        ("Total Cut Volume (m3)", calc["total_cut_volume"]),
        ("Total Fill Volume (m3)", calc["total_fill_volume"]),
        ("Net (Fill - Cut) (m3)", net_volume),
        ("Pending Intervals", calc["pending_intervals"]),
    ]
    for label, value in summary_rows:
        row = volumes_ws.max_row + 1
        volumes_ws.cell(row=row, column=1, value=label).font = header_font
        volumes_ws.cell(row=row, column=2, value=value)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    filename = f"project_{project_id}_earthwork_export.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
