"""Parse City of Toronto Open Data poll-by-poll result workbooks into ward-level records.

The workbooks are wide and multi-sheet: one worksheet per ward, candidates as rows and voting
subdivisions as columns, with a trailing ``Total`` column and (sometimes) a ward ``Totals`` row.
Layout drifts across years — header-row position, the ward identifier's location, and the
candidate-name format all vary — so parsing detects structure rather than assuming fixed offsets.

Output is one row per candidate per ward sheet with columns:
``ward_number, ward_name, office, candidate_name_raw, votes``.

For **councillor** each ward sheet is its own contest. For **mayor** the same candidates recur on
every ward sheet (mayor is city-wide), so a downstream step sums each candidate across wards.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

# Row 0 of a modern sheet, e.g. "City Ward 1 Etobicoke North".
# Modern sheets (2018/2022) label the ward with its name, e.g. "City Ward 1 Etobicoke North".
_WARD_HEADER_RE = re.compile(r"City Ward\s+(\d+)\s*(.*)", re.IGNORECASE)
# Otherwise the ward number appears as "Ward: 1" (2006–2014 title row) or "Ward 2"/"Ward1"
# (sheet name), with no ward name.
_WARD_NUM_RE = re.compile(r"Ward:?\s*(\d+)", re.IGNORECASE)

# Col-0 labels that mark the header row above the candidate rows.
_HEADER_LABELS = {"subdivision", "name"}

COLUMNS = ["ward_number", "ward_name", "office", "candidate_name_raw", "votes"]


def _engine_for(path: Path) -> str:
    return "xlrd" if path.suffix.lower() == ".xls" else "openpyxl"


def _cell_text(value: object) -> str:
    return "" if pd.isna(value) else str(value).strip()


def _find_header_row(raw: pd.DataFrame) -> int | None:
    """Row index whose first cell is a header label ('Subdivision'/'Name')."""
    for idx in range(min(len(raw), 10)):
        if _cell_text(raw.iat[idx, 0]).lower() in _HEADER_LABELS:
            return idx
    return None


def _subdivision_columns(header_row: pd.Series) -> list:
    """Columns whose header is numeric (a subdivision, incl. special codes 97/98/99).

    Excludes the name column (col 0) and the trailing 'Total' column, which are non-numeric.
    Header values may be floats (xlsx) or numeric strings (legacy xls), so coerce.
    """
    numeric = pd.to_numeric(header_row, errors="coerce")
    return [col for col in header_row.index if col != 0 and pd.notna(numeric[col])]


def _ward_identity(
    raw: pd.DataFrame, header_idx: int, sheet_name: str
) -> tuple[int | None, str | None]:
    """Ward number + name from the sheet's header rows, falling back to the sheet name.

    The modern "City Ward N <Name>" title yields both number and name; the "Ward: N" title and
    the sheet name yield only a number (no ward name is published in those years).
    """
    for idx in range(header_idx):
        text = _cell_text(raw.iat[idx, 0])
        named = _WARD_HEADER_RE.match(text)
        if named:
            name = named.group(2).strip()
            return int(named.group(1)), (name or None)
        numbered = _WARD_NUM_RE.search(text)
        if numbered:
            return int(numbered.group(1)), None
    from_sheet = _WARD_NUM_RE.search(sheet_name)
    if from_sheet:
        return int(from_sheet.group(1)), None
    return None, None


def _parse_ward_sheet(raw: pd.DataFrame, *, sheet_name: str, office: str) -> pd.DataFrame | None:
    header_idx = _find_header_row(raw)
    if header_idx is None:  # e.g. a "Notice" sheet — no candidate table
        return None

    subdiv_cols = _subdivision_columns(raw.iloc[header_idx])
    ward_number, ward_name = _ward_identity(raw, header_idx, sheet_name)

    records = []
    for idx in range(header_idx + 1, len(raw)):
        name = _cell_text(raw.iat[idx, 0])
        low = name.lower()
        if not name or low == office.lower() or "total" in low:
            continue
        votes = int(pd.to_numeric(raw.loc[idx, subdiv_cols], errors="coerce").fillna(0).sum())
        records.append((ward_number, ward_name, office, name, votes))

    return pd.DataFrame(records, columns=COLUMNS)


def parse_open_data_file(path: str | Path, *, office: str) -> pd.DataFrame:
    """Parse a poll-by-poll workbook into ward-level candidate vote records.

    ``office`` is ``"councillor"`` or ``"mayor"`` (it also names the label row to skip).
    """
    path = Path(path)
    workbook = pd.ExcelFile(path, engine=_engine_for(path))
    frames = [
        parsed
        for sheet in workbook.sheet_names
        if (
            parsed := _parse_ward_sheet(
                workbook.parse(sheet, header=None), sheet_name=sheet, office=office
            )
        )
        is not None
    ]
    result = pd.concat(frames, ignore_index=True)
    result["votes"] = result["votes"].astype("int64")
    return result


def to_contest_level(df: pd.DataFrame, *, office: str) -> pd.DataFrame:
    """Collapse ward-sheet rows to contest-level rows.

    Councillor ward sheets are already contests and pass through unchanged. Mayor is city-wide
    but published per ward, so each mayor candidate is summed across all wards into one row with
    a null ward.
    """
    if office != "mayor":
        return df.reset_index(drop=True)

    summed = df.groupby("candidate_name_raw", as_index=False, sort=False)["votes"].sum()
    summed["ward_number"] = pd.NA
    summed["ward_name"] = pd.NA
    summed["office"] = "mayor"
    return summed[COLUMNS]
