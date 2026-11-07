"""Derive the 2000 trustee ward crosswalks from the poll counts on the City's 2000 results pages.

The City's archived 2000 results pages give, for every Council ward and every trustee ward, the
number of polls reporting out of the ward's total. The 2000 Council wards are the 44 wards used
until 2014, and the 2003 trustee crosswalks in `data/reference/trustee_ward_crosswalks.csv` say
which of them each trustee ward of 2003 took in. For each board, the script takes a 2000 trustee
ward to be the 2003 ward of the same number when every 2000 ward's poll total equals the sum of
the poll totals of that 2003 ward's Council wards. Where the same-number mapping does not fit, it
takes the one mapping that fits and fails if there is none or more than one. It then writes the
2000 crosswalk rows.

- TCDSB, Viamonde and MonAvenir: only one mapping fits the poll totals. For TCDSB and Viamonde it
  keeps the ward numbers; MonAvenir's two wards match with their numbers swapped.
- TDSB: the same-number mapping fits all 22 poll totals, but several 2003 wards have equal totals,
  so the totals alone allow other mappings. The release takes the same-number mapping, which the
  candidates also support: each of the ten trustees elected in 2000 who ran in 2003 ran in the ward
  of the same number.

The poll totals test the grouping of Council wards, not the boundaries of the 2000 Council wards
themselves, which the release takes from the 2014 subdivision file like every 44-ward district.

Usage:
    python -I scripts/derive_trustee_wards_2000.py [--write]
"""

from __future__ import annotations

import csv
import html
import io
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
REFERENCE = REPO_ROOT / "data" / "reference"
PAGES = REFERENCE / "vote2000_html"
TRUSTEE_PAGES = REFERENCE / "vote2000_trustee_pages.csv"
CROSSWALKS = REFERENCE / "trustee_ward_crosswalks.csv"
PAGE_URL = "https://web.archive.org/web/{timestamp}/http://www.city.toronto.on.ca/vote2000/live_final/{page}.htm"
COUNCIL_POLLS = re.compile(r"COUNCILLOR, Ward (\d+) (\d+) of (\d+) Polls Reporting")


def council_poll_totals() -> dict[int, int]:
    totals: dict[int, int] = {}
    for path in sorted(PAGES.glob("*.htm")):
        text = html.unescape(re.sub(r"<[^>]+>", " ", path.read_text(encoding="latin-1")))
        match = COUNCIL_POLLS.search(re.sub(r"\s+", " ", text))
        if match:
            totals[int(match.group(1))] = int(match.group(3))
    if sorted(totals) != list(range(1, 45)):
        raise SystemExit(f"expected Council wards 1-44 in {PAGES}, found {sorted(totals)}")
    return totals


def trustee_pages() -> dict[tuple[str, int], dict[str, str]]:
    pages: dict[tuple[str, int], dict[str, str]] = {}
    with TRUSTEE_PAGES.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            pages.setdefault((row["represented_body"], int(row["ward"])), row)
    return pages


def derive() -> tuple[list[str], list[dict[str, str]]]:
    council = council_poll_totals()
    pages = trustee_pages()
    with CROSSWALKS.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        columns = list(reader.fieldnames or [])
        rows = list(reader)
    if any(row["boundary_regime"].endswith("-2000") for row in rows):
        raise SystemExit("the crosswalk file already has 2000 rows")
    derived: list[dict[str, str]] = []
    for body in sorted({body for body, _ in pages}):
        wards_2003 = [
            row
            for row in rows
            if row["represented_body"] == body and row["boundary_regime"].endswith("-2003")
        ]
        sums = {
            row["ward_id"]: sum(council[int(ward)] for ward in row["city_wards"].split(";"))
            for row in wards_2003
        }
        totals = {
            str(ward): int(page["polls_total"])
            for (page_body, ward), page in pages.items()
            if page_body == body
        }
        if all(sums.get(ward) == total for ward, total in totals.items()):
            mapping = {ward: ward for ward in totals}
        else:
            mapping = {}
            for ward, total in totals.items():
                matches = [ward_id for ward_id, value in sums.items() if value == total]
                if len(matches) != 1:
                    raise SystemExit(f"{body} Ward {ward} (2000) matches 2003 wards {matches}")
                mapping[ward] = matches[0]
        used = set(mapping.values())
        if len(used) != len(mapping):
            raise SystemExit(f"{body}: two 2000 wards match one 2003 ward")
        for ward, ward_2003 in sorted(mapping.items(), key=lambda item: int(item[0])):
            page = pages[(body, int(ward))]
            source = next(row for row in wards_2003 if row["ward_id"] == ward_2003)
            derived.append(
                {
                    **source,
                    "boundary_regime": source["boundary_regime"].replace("-2003", "-2000"),
                    "ward_id": ward,
                    "official_geographic_name": "",
                    "source_authority": "City of Toronto",
                    "source_url": PAGE_URL.format(
                        timestamp=page["capture_timestamp"], page=page["page"]
                    ),
                    "source_date": "2000-11-13",
                }
            )
        if used != set(sums):
            raise SystemExit(f"{body}: 2003 wards {sorted(set(sums) - used)} match no 2000 ward")
    return columns, derived


def main(argv: list[str]) -> None:
    columns, derived = derive()
    for row in derived:
        print(row["represented_body"], row["ward_id"], row["city_wards"])
    if "--write" in argv:
        # Append, keeping the file's own line endings and order.
        raw = CROSSWALKS.read_bytes()
        ending = "\r\n" if b"\r\n" in raw else "\n"
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator=ending)
        writer.writerows(derived)
        separator = "" if raw.endswith(ending.encode()) else ending
        with CROSSWALKS.open("a", newline="", encoding="utf-8") as handle:
            handle.write(separator + buffer.getvalue())
        print(f"wrote {len(derived)} rows to {CROSSWALKS.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main(sys.argv)
