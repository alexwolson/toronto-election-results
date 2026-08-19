"""Parse the 2000 election results from the City's archived results website.

2000 is absent from Open Data and has no certified Clerk's declaration online. The authoritative
source is the City's own final results site (``city.toronto.on.ca/vote2000/live_final/``),
preserved in the Wayback Machine as clean HTML tables — digital text, no OCR. Page ``000`` is the
city-wide Mayor race; pages ``001``–``044`` are the per-ward Councillor races. Names are written
**given-first** (``MEL LASTMAN``); acclamations show the text "Acclamation" instead of a count.

The fetched HTML is cached under ``data/reference/vote2000_html/`` so the parse never depends on
the Wayback Machine staying up. Cross-verification against Wikipedia lives in ``crosscheck_2000``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

CACHE = Path("data/reference/vote2000_html")
_WAYBACK = "https://web.archive.org/web/{ts}id_/http://www.city.toronto.on.ca/vote2000/live_final/{page}.htm"

# Exact Wayback capture timestamps (from preflight; all returned HTTP 200).
WARD_TIMESTAMPS = {
    0: "20010214042440",
    1: "20010211013327",
    2: "20010411010831",
    3: "20010214025248",
    4: "20010214030147",
    5: "20010211013048",
    6: "20010214031532",
    7: "20010411012124",
    8: "20010411011543",
    9: "20010211013647",
    10: "20010214031922",
    11: "20010214032847",
    12: "20010214032636",
    13: "20010211013336",
    14: "20010214033809",
    15: "20010214033202",
    16: "20010214034409",
    17: "20010211013247",
    18: "20010214034820",
    19: "20010214035635",
    20: "20010214021800",
    21: "20010211012414",
    22: "20010214022552",
    23: "20010214023540",
    24: "20010214023732",
    25: "20010211013825",
    26: "20010214024138",
    27: "20010214034915",
    28: "20010411012210",
    29: "20010211012640",
    30: "20010214025608",
    31: "20010214030228",
    32: "20010214031114",
    33: "20010211012901",
    34: "20010214020628",
    35: "20010214021357",
    36: "20010214031150",
    37: "20010211012553",
    38: "20010214031935",
    39: "20010214032200",
    40: "20010214033328",
    41: "20010211013449",
    42: "20010214033348",
    43: "20010214034506",
    44: "20010214034909",
}

COLUMNS = ["ward_number", "ward_name", "office", "candidate_name_raw", "votes"]
_WARD_RE = re.compile(r"Ward\s+(\d+)", re.IGNORECASE)


def fetch_2000_html(
    *, cache: Path = CACHE, session: requests.Session | None = None
) -> dict[int, Path]:
    """Download each archived page into ``cache`` (idempotent). Returns page -> path."""
    getter = session or requests.Session()
    cache.mkdir(parents=True, exist_ok=True)
    paths: dict[int, Path] = {}
    for page, ts in WARD_TIMESTAMPS.items():
        dest = cache / f"{page:03d}.htm"
        if not dest.exists():
            resp = getter.get(_WAYBACK.format(ts=ts, page=f"{page:03d}"), timeout=120)
            resp.raise_for_status()
            dest.write_text(resp.text, encoding="utf-8")
        paths[page] = dest
    return paths


def _clean(cell) -> str:
    return cell.get_text().replace("\xa0", " ").strip()


def parse_2000_page(html: str) -> tuple[str, int | None, list[tuple[str, int]]]:
    """Return (office, ward_number, [(candidate_name_raw, votes), ...]) for one page.

    Acclaimed candidates get 0 votes here; the single-candidate contest is marked acclaimed
    downstream, which nulls the count.
    """
    table = BeautifulSoup(html, "lxml").find("table")
    office: str | None = None
    ward: int | None = None
    records: list[tuple[str, int]] = []

    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) == 1:  # title / "polls reporting" banner (colspan=2)
            text = _clean(cells[0])
            if "mayor" in text.lower():
                office = "mayor"
            elif "councillor" in text.lower():
                office = "councillor"
                match = _WARD_RE.search(text)
                ward = int(match.group(1)) if match else None
            continue
        if len(cells) < 2:
            continue
        name, votes_text = _clean(cells[0]), _clean(cells[1])
        # Skip header ("Name") and trailing summary rows ("Total Votes Counted:Eligible Voters:").
        if not name or name.lower() == "name" or "polls reporting" in name.lower() or ":" in name:
            continue
        votes = 0 if votes_text.lower() == "acclamation" else int(votes_text.replace(",", ""))
        records.append((name, votes))

    return office, ward, records


def parse_2000_results(
    *, cache: Path = CACHE, session: requests.Session | None = None
) -> pd.DataFrame:
    """Parse all archived pages into contest-level rows (mayor city-wide + councillor per ward)."""
    paths = fetch_2000_html(cache=cache, session=session)
    rows = []
    for page in sorted(paths):
        office, ward, records = parse_2000_page(paths[page].read_text(encoding="utf-8"))
        for name, votes in records:
            rows.append((ward, None, office, name, votes))
    return pd.DataFrame(rows, columns=COLUMNS)


if __name__ == "__main__":
    df = parse_2000_results()
    print(f"parsed {len(df)} rows: {df['office'].value_counts().to_dict()}")
    print("councillor wards:", sorted(df[df.office == "councillor"].ward_number.unique()))
