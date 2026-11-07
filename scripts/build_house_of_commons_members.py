"""Build data/reference/house_of_commons_members.csv, one row per House of Commons member term.

The 36th to 45th Parliaments come from the House of Commons members search export
(https://www.ourcommons.ca/Members/en/search/xml?parliament=N). The 35th Parliament, which that
export does not serve, comes from an export of ParlInfo's Parliamentarians search (Library of
Parliament) filtered to the House of Commons and the 35th Parliament, saved as .xlsx.

Each row is one member's membership in one Parliament, with the riding, province, caucus and the
first and last days of that membership as the source gives them. A member who sat until a
general election has the day before polling as the last day. ParlInfo gives one span per riding
across Parliaments, so its spans are clipped to the 35th Parliament (1993-10-25 to 1997-06-01).

Usage:
    python scripts/build_house_of_commons_members.py XML_DIR PARLINFO_35_XLSX
where XML_DIR holds parl_36.xml ... parl_45.xml downloaded from the export above.
"""

from __future__ import annotations

import csv
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import openpyxl

REPO_ROOT = Path(__file__).parents[1]
OUT = REPO_ROOT / "data" / "reference" / "house_of_commons_members.csv"
COLUMNS = (
    "parliament",
    "house_person_id",
    "first_name",
    "last_name",
    "constituency",
    "province",
    "caucus",
    "from_date",
    "to_date",
    "source",
)
PARLIAMENT_35 = ("1993-10-25", "1997-06-01")
XML_PARLIAMENTS = range(36, 46)
EXPORT_URL = "https://www.ourcommons.ca/Members/en/search/xml?parliament={n}"
PARLINFO_SOURCE = "ParlInfo, Parliamentarians search, House of Commons, 35th Parliament (export)"
_SPAN = re.compile(
    r"^(?P<label>.*?)\s*\((?P<start>\d{4}/\d{2}/\d{2}) - (?P<end>\d{4}/\d{2}/\d{2})?\)$"
)


def _xml_rows(xml_dir: Path) -> list[dict[str, str]]:
    rows = []
    for parliament in XML_PARLIAMENTS:
        root = ET.parse(xml_dir / f"parl_{parliament}.xml").getroot()
        for member in root.findall("MemberOfParliament"):
            rows.append(
                {
                    "parliament": str(parliament),
                    "house_person_id": member.findtext("PersonId", ""),
                    "first_name": member.findtext("PersonOfficialFirstName", ""),
                    "last_name": member.findtext("PersonOfficialLastName", ""),
                    "constituency": member.findtext("ConstituencyName", ""),
                    "province": member.findtext("ConstituencyProvinceTerritoryName", ""),
                    "caucus": member.findtext("CaucusShortName", ""),
                    "from_date": (member.findtext("FromDateTime") or "")[:10],
                    "to_date": (member.findtext("ToDateTime") or "")[:10],
                    "source": EXPORT_URL.format(n=parliament),
                }
            )
    return rows


def _spans(cell: object) -> list[tuple[str, str, str]]:
    spans = []
    for line in str(cell or "").splitlines():
        if not line.strip():
            continue
        match = _SPAN.match(line.strip())
        if match is None:
            raise ValueError(f"unreadable ParlInfo span: {line!r}")
        start = match["start"].replace("/", "-")
        end = (match["end"] or "").replace("/", "-")
        spans.append((match["label"], start, end))
    return spans


def _parlinfo_rows(path: Path) -> list[dict[str, str]]:
    first_day, last_day = PARLIAMENT_35
    sheet = openpyxl.load_workbook(path, read_only=True, data_only=True).worksheets[0]
    rows_in = sheet.iter_rows(values_only=True)
    header = {name: index for index, name in enumerate(next(rows_in))}
    rows = []
    for record in rows_in:
        last_name, _, first_name = str(record[header["Name"]]).partition(", ")
        ridings = _spans(record[header["Riding/Senatorial Division"]])
        provinces = [
            line.strip()
            for line in str(record[header["Province/Territory"]] or "").splitlines()
            if line.strip()
        ]
        parties = _spans(record[header["Political Affiliation"]])
        if len(provinces) != len(ridings):
            raise ValueError(f"ParlInfo riding and province lines differ for {last_name!r}")
        for (riding, start, end), province in zip(ridings, provinces, strict=True):
            if start > last_day or (end and end < first_day):
                continue
            from_date = max(start, first_day)
            to_date = min(end or last_day, last_day)
            caucus = next(
                (
                    party
                    for party, party_start, party_end in parties
                    if party_start <= from_date and (not party_end or party_end >= from_date)
                ),
                "",
            )
            rows.append(
                {
                    "parliament": "35",
                    "house_person_id": "",
                    "first_name": first_name,
                    "last_name": last_name,
                    "constituency": riding.replace("--", "—"),
                    "province": province,
                    "caucus": caucus,
                    "from_date": from_date,
                    "to_date": to_date,
                    "source": PARLINFO_SOURCE,
                }
            )
    return rows


def main(argv: list[str]) -> None:
    if len(argv) != 3:
        raise SystemExit(__doc__)
    rows = _parlinfo_rows(Path(argv[2])) + _xml_rows(Path(argv[1]))
    rows.sort(
        key=lambda row: (
            int(row["parliament"]),
            row["last_name"],
            row["first_name"],
            row["from_date"],
        )
    )
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} member terms to {OUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main(sys.argv)
