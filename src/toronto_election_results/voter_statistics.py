"""Parse the City's voter-statistics files into per-ward electorate + turnout numerator.

The City publishes eligible electors and ballots cast per (ward, subdivision). We sum the
subdivision rows to ward level and expose:

  - ``eligible_electors`` = **Total Eligible Electors** (list electors + election-day additions,
    the City's own turnout denominator);
  - ``ballots_cast`` = **Number Voted** (electors who cast a ballot).

Format drift is handled per file: 2003/2006 are xlsx mislabeled ``.xls`` (openpyxl); 2010/2014 are
true BIFF ``.xls`` (xlrd); 2018 is a zip; 2022/2023 are xlsx with a readme sheet to skip. Columns
are located by (whitespace-normalized) header name, not position. There is **no 2000 file** — the
electorate for 2000 does not exist in any source.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pandas as pd
from openpyxl.utils.exceptions import InvalidFileException

RAW = Path("data/raw/voter_stats")
BY_ELECTION_RAW = Path("data/raw/byelection_voter_stats")

# General-election voter statistics: year -> filename under RAW.
VOTER_STATS_FILES = {
    2003: "2003-voter-statistics.xls",
    2006: "2006-voter-statistics.xls",
    2010: "2010-voter-statistics.xls",
    2014: "2014-voter-statistics.xls",
    2018: "2018-voter-statistics.zip",
    2022: "2022_voter_turnout_statistics_final.xlsx",
}

# Council by-election voter statistics (single ward each): year -> (ward, filename under BY_ELECTION_RAW).
BY_ELECTION_COUNCIL_FILES = {
    2016: (2, "2016-councillor-ward-2-by-election-voter-statistics.xlsx"),
    2017: (42, "2017-councillor-ward-42-by-election-voter-statistics.xlsx"),
    2021: (22, "2021_voter_turnout_statistics_ward_22_by-election.xlsx"),
    2023: (20, "2023-councillor-ward-20-by-election-voter-statistics.xlsx"),
    2024: (15, "2024-councillor-ward-15-by-election-voter-statistics.xlsx"),
    2025: (25, "2025-ward-25-by-election-voter-statistics.xlsx"),
}
# The 2023 mayoral by-election (city-wide) lives under RAW.
MAYORAL_BY_ELECTION_FILE = "2023-mayoral-by-election-voter-statistics-1.xlsx"

COLUMNS = ["election_year", "ward_number", "eligible_electors", "ballots_cast"]


def _norm(value: object) -> str:
    return " ".join(str(value).split()).lower()


def _open_workbook(path: Path) -> pd.ExcelFile:
    """Open a voter-stats workbook, handling zips and the .xls/.xlsx mislabelling."""
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            member = next(
                n
                for n in archive.namelist()
                if "voter" in n.lower()
                and n.lower().endswith(".xlsx")
                and "readme" not in n.lower()
            )
            return pd.ExcelFile(io.BytesIO(archive.read(member)), engine="openpyxl")
    try:  # 2003/2006 are xlsx despite the .xls name; 2010/2014 are true BIFF
        return pd.ExcelFile(path, engine="openpyxl")
    except InvalidFileException, zipfile.BadZipFile:
        return pd.ExcelFile(path, engine="xlrd")


def parse_voter_statistics_file(path: str | Path, *, year: int) -> pd.DataFrame:
    """Parse one file into per-ward ``eligible_electors`` and ``ballots_cast``."""
    workbook = _open_workbook(Path(path))
    sheet = next(s for s in workbook.sheet_names if "voter turnout" in s.lower())
    raw = workbook.parse(sheet, header=None)

    header_idx = next(i for i in range(min(8, len(raw))) if _norm(raw.iat[i, 0]) == "ward")
    header = [_norm(cell) for cell in raw.iloc[header_idx]]

    def find(predicate) -> int:
        return next(i for i, name in enumerate(header) if predicate(name))

    ward_col = find(lambda h: h == "ward")
    sub_col = find(lambda h: h == "sub")
    eligible_col = find(lambda h: h.startswith("total eligible"))
    voted_col = find(lambda h: h == "number voted")

    body = raw.iloc[header_idx + 1 :]
    ward = pd.to_numeric(body[ward_col], errors="coerce")
    sub = pd.to_numeric(body[sub_col], errors="coerce")
    subdivisions = body[ward.notna() & sub.notna()]  # excludes "Ward N Total" / "Grand Total" rows

    per_subdivision = pd.DataFrame(
        {
            "ward_number": pd.to_numeric(subdivisions[ward_col]).astype("int64"),
            "eligible_electors": pd.to_numeric(subdivisions[eligible_col], errors="coerce"),
            "ballots_cast": pd.to_numeric(subdivisions[voted_col], errors="coerce"),
        }
    )
    per_ward = per_subdivision.groupby("ward_number", as_index=False).sum()
    per_ward["election_year"] = year
    per_ward["eligible_electors"] = per_ward["eligible_electors"].astype("int64")
    per_ward["ballots_cast"] = per_ward["ballots_cast"].astype("int64")
    return per_ward[COLUMNS]


def voter_statistics(*, raw: Path = RAW) -> pd.DataFrame:
    """Per-ward general-election eligible electors + ballots cast (2003–2022)."""
    frames = [
        parse_voter_statistics_file(raw / filename, year=year)
        for year, filename in VOTER_STATS_FILES.items()
    ]
    return pd.concat(frames, ignore_index=True)


BY_ELECTION_COLUMNS = [
    "election_year",
    "office",
    "ward_number",
    "eligible_electors",
    "ballots_cast",
]


def by_election_voter_statistics(
    *, raw: Path = RAW, by_election_raw: Path = BY_ELECTION_RAW
) -> pd.DataFrame:
    """Per-contest electorate for by-elections: one row per council ward, one for the 2023 mayor.

    Council by-elections are a single ward; the 2023 mayoral by-election is city-wide (summed).
    """
    rows = []
    for year, (ward, filename) in BY_ELECTION_COUNCIL_FILES.items():
        parsed = parse_voter_statistics_file(by_election_raw / filename, year=year)
        row = parsed[parsed["ward_number"] == ward].iloc[0]
        rows.append(
            (year, "councillor", ward, int(row["eligible_electors"]), int(row["ballots_cast"]))
        )
    mayoral = parse_voter_statistics_file(raw / MAYORAL_BY_ELECTION_FILE, year=2023)
    rows.append(
        (
            2023,
            "mayor",
            pd.NA,
            int(mayoral["eligible_electors"].sum()),
            int(mayoral["ballots_cast"].sum()),
        )
    )
    return pd.DataFrame(rows, columns=BY_ELECTION_COLUMNS)


def attach_electorate(
    results: pd.DataFrame, general: pd.DataFrame, by_election: pd.DataFrame
) -> pd.DataFrame:
    """Add ``eligible_electors`` / ``ballots_cast`` / ``turnout``, routed per contest.

    A councillor contest takes its ward's electorate; a mayor contest takes the city-wide total.
    By-election contests draw from the by-election statistics (a council by-election has a
    different, and much lower, turnout than the general in the same ward). ``(year, office, ward)``
    is unique across generals and by-elections — they never share a year — so routing is by
    ``election_type`` + ``office``.
    """
    gen_ward = {
        (int(r.election_year), int(r.ward_number)): (r.eligible_electors, r.ballots_cast)
        for r in general.itertuples(index=False)
    }
    gen_city = general.groupby("election_year")[["eligible_electors", "ballots_cast"]].sum()
    gen_city = {int(y): (row.eligible_electors, row.ballots_cast) for y, row in gen_city.iterrows()}
    be = by_election
    be_council = {
        (int(r.election_year), int(r.ward_number)): (r.eligible_electors, r.ballots_cast)
        for r in be[be.office == "councillor"].itertuples(index=False)
    }
    be_mayor = {
        int(r.election_year): (r.eligible_electors, r.ballots_cast)
        for r in be[be.office == "mayor"].itertuples(index=False)
    }

    eligible, ballots = [], []
    for r in results.itertuples(index=False):
        year = int(r.election_year)
        if r.election_type == "by_election" and r.office == "councillor":
            hit = be_council.get((year, int(r.ward_number))) if pd.notna(r.ward_number) else None
        elif r.election_type == "by_election" and r.office == "mayor":
            hit = be_mayor.get(year)
        elif r.office == "mayor":
            hit = gen_city.get(year)
        elif pd.notna(r.ward_number):
            hit = gen_ward.get((year, int(r.ward_number)))
        else:
            hit = None
        eligible.append(hit[0] if hit else pd.NA)
        ballots.append(hit[1] if hit else pd.NA)

    results = results.copy()
    results["eligible_electors"] = pd.array(eligible, dtype="Int64")
    results["ballots_cast"] = pd.array(ballots, dtype="Int64")
    results["turnout"] = results["ballots_cast"] / results["eligible_electors"]
    return results


if __name__ == "__main__":
    stats = voter_statistics()
    city = stats.groupby("election_year")[["eligible_electors", "ballots_cast"]].sum()
    city["turnout"] = city["ballots_cast"] / city["eligible_electors"]
    print(city.to_string())
