"""Transcribe the City's archived 1994, 1997 and 2000 results pages into a pinned reference table.

Inputs (committed under ``data/reference``):

- ``municipal_archive/results_1994.pdf`` and ``results_1997.pdf``: print-outs of the City's
  archived "Previous election results" pages, captured by the Wayback Machine on 2004-02-05;
- ``vote2000_html/000.htm``-``044.htm``: the City's 2000 final results pages (mayor and the 44
  council wards), cached from the Wayback Machine when the 2000 parser was first built.

Output: ``data/reference/municipal_archive_results.csv``, one row per Candidacy, plus one
``source_missing`` row per in-scope Contest the archive does not report. Requires ``pdftotext``.
Only Mayor, Councillor and Metro Councillor contests are transcribed; school boards, hydro and
utility commissions and plebiscites are skipped (ADR 0010).

The archive omits seat counts and, in a few places, ward labels. Seat counts come from the
council composition recorded on Wikipedia's 1994 and 1997 election pages: two councillors per
ward for the 1997 City Council and 1994 East York, one elsewhere. Lost labels are restored from
the same pages and cited in ``district_label_source``; vote counts always come from the archive.

Run: ``python scripts/transcribe_municipal_archive.py``
"""

from __future__ import annotations

import csv
import re
import subprocess
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "data" / "reference"
OUTPUT = REFERENCE / "municipal_archive_results.csv"

URL_1994 = (
    "https://web.archive.org/web/20040205224919/"
    "http://www.toronto.ca/elections/results/results_1994.htm"
)
URL_1997 = (
    "https://web.archive.org/web/20040205225908/"
    "http://www.toronto.ca/elections/results/results_1997.htm"
)
URL_2000 = "https://web.archive.org/web/{ts}/http://www.city.toronto.on.ca/vote2000/live_final/{page:03d}.htm"
WIKI_1994 = "https://en.wikipedia.org/wiki/1994_Toronto_municipal_election"
WIKI_1997 = "https://en.wikipedia.org/wiki/1997_Toronto_municipal_election"

TIMESTAMPS_2000 = {
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

COLUMNS = [
    "election_date",
    "election_authority",
    "represented_body",
    "office_type",
    "boundary_regime",
    "official_district_id",
    "district_name",
    "seats_available",
    "candidate_name_raw",
    "votes",
    "acclaimed",
    "marked_elected",
    "coverage_status",
    "source_detail",
    "source_locator",
    "district_label_source",
]

MUNICIPALITIES_1994 = {
    "East York": ("east_york", "Borough of East York", 2),
    "Etobicoke": ("etobicoke", "City of Etobicoke", 1),
    "North York": ("north_york", "City of North York", 1),
    "Scarborough": ("scarborough", "City of Scarborough", 1),
    "Toronto": ("former_toronto", "City of Toronto (former)", 1),
    "York": ("york", "City of York", 1),
}
BODY_1994 = {
    "east_york": "east_york_borough_council",
    "etobicoke": "etobicoke_city_council",
    "north_york": "north_york_city_council",
    "scarborough": "scarborough_city_council",
    "former_toronto": "former_toronto_city_council",
    "york": "york_city_council",
}
AUTHORITY_1994 = {
    "east_york": "east_york_borough_clerk",
    "etobicoke": "etobicoke_city_clerk",
    "north_york": "north_york_city_clerk",
    "scarborough": "scarborough_city_clerk",
    "former_toronto": "former_toronto_city_clerk",
    "york": "york_city_clerk",
}
# Archive Metro-ward labels -> Metro ward names (Wikipedia's 1994 page; the Toronto page's Metro
# ward numbers 19-26 match these names).
METRO_LABELS = {
    ("east_york", None): "East York",
    ("etobicoke", "Lakeshore/ Queensway"): "Lakeshore Queensway",
    ("etobicoke", "Rexdale/ Thistletown"): "Rexdale Thistletown",
    ("former_toronto", "Ward 19 (City Ward 01 02)"): "High Park",
    ("former_toronto", "Ward 20 (City Ward 03 04)"): "Trinity Niagara",
    ("former_toronto", "Ward 21 (City Ward 11 12)"): "Davenport",
    ("former_toronto", "Ward 22 (City Ward 15 16)"): "North Toronto",
    ("former_toronto", "Ward 23 (City Ward 13 14 )"): "Midtown",
    ("former_toronto", "Ward 24 (City Ward 05 06)"): "Downtown",
    ("former_toronto", "Ward 25 (City Ward 07 08)"): "Don River",
    ("former_toronto", "Ward 26 (City Ward 09 10)"): "East Toronto",
    ("york", "Wards 1 to 4"): "York Eglinton",
    ("york", "Wards 5 to 8"): "York Humber",
}
# North York's Metro candidates are listed without ward labels; Wikipedia's 1994 page groups them.
NORTH_YORK_METRO = {
    "Augimeri": "Black Creek",
    "Tiqui": "Black Creek",
    "Azzarello": "Don Parkway",
    "Ball": "Don Parkway",
    "Chong": "Don Parkway",
    "Lagopoulos": "Don Parkway",
    "Scott": "Don Parkway",
    "Floro": "Seneca Heights",
    "King": "Seneca Heights",
    "Michael": "Seneca Heights",
    "Sgro": "North York Humber",
}
# In-scope 1994 Metro contests the archive omits entirely (Wikipedia lists them as acclamations).
MISSING_METRO_1994 = {
    "etobicoke": ("Kingsway Humber", "Markland Centennial"),
    "north_york": ("North York Spadina", "North York Centre South", "North York Centre"),
}

_ROW = re.compile(
    r"^\s*(?P<name>\S.*?)\s{3,}(?P<votes>[\d,]+|Acclaimed|Acclamation|acclamation)\s*$"
)
_SKIP = (
    "hydro",
    "school board",
    "public school",
    "metropolitan",
    "metro toronto french",
    "french",
    "scarborough board",
    "scarborough public",
    "toronto board",
    "separate school",
    "ward 12 liquor",
    "q1",
    "q2",
    "metro question",
    "trustee",
    "metro french",
    "english language",
    "englich",
)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _pdf_lines(path: Path) -> list[tuple[int, str]]:
    text = subprocess.run(
        ["pdftotext", "-layout", str(path), "-"], check=True, capture_output=True, text=True
    ).stdout
    lines = []
    for number, line in enumerate(text.splitlines(), start=1):
        if "web.archive.org" in line or re.search(r"Page \d+ of \d+", line):
            continue
        if "Toronto maps" in line:
            break
        if line.strip() not in ("", ":"):
            lines.append((number, line))
    return lines


def _office(text: str) -> str | None:
    lowered = text.lower()
    if lowered == "mayor":
        return "mayor"
    if lowered in ("councillor", "councillors") or lowered.startswith("councillor - ward"):
        return "councillor"
    if lowered.startswith("metro councillor"):
        return "metro"
    return None


def _parse_pdf(path: Path, year: int) -> list[dict]:
    rows, muni, office, label, skip, pending = (
        [],
        None if year == 1994 else "city",
        None,
        None,
        False,
        None,
    )
    for number, line in _pdf_lines(path):
        text = line.strip()
        if year == 1994 and text.startswith("Former Municipality of"):
            muni = next(v[0] for k, v in MUNICIPALITIES_1994.items() if text.endswith(" " + k))
            office, label, skip = None, None, False
            continue
        if muni is None:
            continue
        match = _ROW.match(line)
        if match:
            if not skip and office:
                votes = match["votes"]
                rows.append(
                    {
                        "muni": muni,
                        "office": office,
                        "label": label,
                        "name": match["name"].strip().lstrip("*"),
                        "marked": match["name"].lstrip().startswith("*"),
                        "votes": int(votes.replace(",", "")) if votes[0].isdigit() else None,
                        "acclaimed": not votes[0].isdigit(),
                        "line": number,
                    }
                )
            continue
        lowered = text.lower()
        if lowered == "acclamation" and pending:
            rows.append(
                {
                    "muni": muni,
                    "office": office,
                    "label": label,
                    "name": pending,
                    "marked": False,
                    "votes": None,
                    "acclaimed": True,
                    "line": number,
                }
            )
            pending = None
            continue
        found = _office(text)
        if found:
            office, skip, label = found, False, None
            if lowered.startswith("councillor - ward"):
                label = text.split("-", 1)[1].strip()
            continue
        if lowered.startswith(_SKIP):
            skip, office = True, None
            continue
        if office and not skip:
            if lowered == "results not available":
                rows.append(
                    {
                        "muni": muni,
                        "office": office,
                        "label": label,
                        "missing": True,
                        "line": number,
                    }
                )
            elif year == 1994 and office == "metro" and re.match(r"^[A-Z][^,]+, [A-Z]", text):
                pending = text
            else:
                label = text
    return rows


def _ward(label: str) -> int:
    return int(re.search(r"(\d+)\s*$", label).group(1))


def _rows_1994() -> list[dict]:
    out = []
    names = {v[0]: v[1] for v in MUNICIPALITIES_1994.values()}
    seats = {v[0]: v[2] for v in MUNICIPALITIES_1994.values()}
    for row in _parse_pdf(REFERENCE / "municipal_archive" / "results_1994.pdf", 1994):
        muni = row["muni"]
        base = {
            "election_date": "1994-11-14",
            "election_authority": AUTHORITY_1994[muni],
            "source_detail": URL_1994,
            "source_locator": f"results_1994.pdf line {row['line']}",
        }
        if row["office"] == "metro":
            if muni == "north_york":
                district = NORTH_YORK_METRO[row["name"].split(",")[0]]
                label_source = WIKI_1994
            elif muni == "scarborough":
                district = row["label"]
                label_source = "archive"
            else:
                district = METRO_LABELS[(muni, row["label"])]
                label_source = "archive" if muni == "etobicoke" else WIKI_1994
            base.update(
                represented_body="metro_toronto_council",
                office_type="councillor",
                boundary_regime="metro_toronto_wards_1994",
                official_district_id=_slug(district),
                district_name=district,
                seats_available=1,
                district_label_source=label_source,
            )
        elif row["office"] == "mayor":
            base.update(
                represented_body=BODY_1994[muni],
                office_type="mayor",
                boundary_regime=f"{muni}_wards_1994",
                official_district_id="city",
                district_name=names[muni],
                seats_available=1,
                district_label_source="archive",
            )
        else:
            ward = _ward(row["label"])
            base.update(
                represented_body=BODY_1994[muni],
                office_type="councillor",
                boundary_regime=f"{muni}_wards_1994",
                official_district_id=f"ward-{ward}",
                district_name=f"Ward {ward}",
                seats_available=seats[muni],
                district_label_source="archive",
            )
        if row.get("missing"):
            base.update(
                candidate_name_raw="",
                votes="",
                acclaimed="",
                marked_elected="",
                coverage_status="source_missing",
            )
        else:
            base.update(
                candidate_name_raw=row["name"],
                votes="" if row["votes"] is None else row["votes"],
                acclaimed=str(row["acclaimed"]).lower(),
                marked_elected="true" if row["marked"] else "",
                coverage_status="complete",
            )
        out.append(base)
    for muni, districts in MISSING_METRO_1994.items():
        for district in districts:
            out.append(
                {
                    "election_date": "1994-11-14",
                    "election_authority": AUTHORITY_1994[muni],
                    "represented_body": "metro_toronto_council",
                    "office_type": "councillor",
                    "boundary_regime": "metro_toronto_wards_1994",
                    "official_district_id": _slug(district),
                    "district_name": district,
                    "seats_available": 1,
                    "candidate_name_raw": "",
                    "votes": "",
                    "acclaimed": "",
                    "marked_elected": "",
                    "coverage_status": "source_missing",
                    "source_detail": URL_1994,
                    "source_locator": "results_1994.pdf (contest not listed)",
                    "district_label_source": WIKI_1994,
                }
            )
    return out


def _rows_1997() -> list[dict]:
    out = []
    for row in _parse_pdf(REFERENCE / "municipal_archive" / "results_1997.pdf", 1997):
        mayor = row["office"] == "mayor"
        ward = None if mayor else _ward(row["label"])
        out.append(
            {
                "election_date": "1997-11-10",
                "election_authority": "toronto_city_clerk",
                "represented_body": "toronto_city_council",
                "office_type": "mayor" if mayor else "councillor",
                "boundary_regime": "toronto_council_28_wards",
                "official_district_id": "city" if mayor else f"ward-{ward}",
                "district_name": "City of Toronto" if mayor else f"Ward {ward}",
                "seats_available": 1 if mayor else 2,
                "candidate_name_raw": row["name"],
                "votes": "" if row["votes"] is None else row["votes"],
                "acclaimed": str(row["acclaimed"]).lower(),
                "marked_elected": "",
                "coverage_status": "complete",
                "source_detail": URL_1997,
                "source_locator": f"results_1997.pdf line {row['line']}",
                "district_label_source": "archive",
            }
        )
    return out


class _Table(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: str | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = ""

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None:
            self._row.append(self._cell.replace("\xa0", " ").strip())
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell += data


def _rows_2000() -> list[dict]:
    out = []
    for page, ts in TIMESTAMPS_2000.items():
        table = _Table()
        table.feed((REFERENCE / "vote2000_html" / f"{page:03d}.htm").read_text(encoding="utf-8"))
        office, ward = None, None
        for cells in table.rows:
            cells = [c.replace("\xa0", " ").strip() for c in cells]
            if len(cells) == 1 or all(c == "" for c in cells[1:]):
                title = cells[0].lower()
                if "mayor" in title:
                    office = "mayor"
                elif "councillor" in title:
                    office = "councillor"
                    ward = int(re.search(r"ward\s+(\d+)", title).group(1))
                continue
            name, votes = cells[0], cells[1]
            if (
                not name
                or name.lower() == "name"
                or "polls reporting" in name.lower()
                or ":" in name
            ):
                continue
            acclaimed = votes.lower().startswith("acclam")
            mayor = office == "mayor"
            out.append(
                {
                    "election_date": "2000-11-13",
                    "election_authority": "toronto_city_clerk",
                    "represented_body": "toronto_city_council",
                    "office_type": office,
                    "boundary_regime": "toronto_council_44_wards",
                    "official_district_id": "city" if mayor else f"ward-{ward}",
                    "district_name": "City of Toronto" if mayor else f"Ward {ward}",
                    "seats_available": 1,
                    "candidate_name_raw": name,
                    "votes": "" if acclaimed else int(votes.replace(",", "")),
                    "acclaimed": str(acclaimed).lower(),
                    "marked_elected": "",
                    "coverage_status": "complete",
                    "source_detail": URL_2000.format(ts=ts, page=page),
                    "source_locator": f"vote2000_html/{page:03d}.htm",
                    "district_label_source": "archive",
                }
            )
    return out


def main() -> None:
    rows = _rows_1994() + _rows_1997() + _rows_2000()
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
