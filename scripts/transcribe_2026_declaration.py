"""Transcribe the City Clerk's 2026 Declaration of Results into a pinned reference table.

Input (committed under ``data/reference``): ``results_2026/declaration_of_results_2026.pdf``,
the Clerk's Declaration of Results under s. 55(4) of the Municipal Elections Act, 1996, dated
29 October 2026, as published at ``DECLARATION_URL``. It lists every candidate's vote total for
Mayor, the 25 Councillor wards and the four school boards, marks each winner with an "X" and
prints "Acclaimed" in place of votes for the four acclaimed trustees.

Output: ``data/reference/results_2026_declaration.csv``, one row per Candidacy in the order the
declaration prints them. ``marked_elected`` records the declaration's "X" (or "Acclaimed") as
printed. The declaration omits the "X" for Conseil scolaire Viamonde Ward 3, where it prints the
top vote-getter in bold like every other winner; the loader therefore derives ``elected`` from
the vote totals and checks it against every printed mark. Requires ``pdftotext``.

Run: ``python scripts/transcribe_2026_declaration.py``
"""

from __future__ import annotations

import csv
import hashlib
import re
import subprocess
from pathlib import Path

REFERENCE = Path("data/reference")
PDF = REFERENCE / "results_2026" / "declaration_of_results_2026.pdf"
OUTPUT = REFERENCE / "results_2026_declaration.csv"
DECLARATION_URL = (
    "https://www.toronto.ca/wp-content/uploads/2026/10/"
    "8966-Declaration-of-Results-2026-Toronto-Municipal-Election-Oct-29-Final.pdf"
)
PDF_SHA256 = "e6be04483216f7ed32c6fcfb5327ecc23641cf49531cb53d6629842fb4b95aee"

_OFFICES = {
    "Office of Mayor": ("city", "mayor"),
    "Office of Councillor": ("city", "councillor"),
    "Office of Trustee, Toronto District School Board": ("tdsb", "trustee"),
    "Office of Trustee, Toronto Catholic District School Board": ("tcdsb", "trustee"),
    "Office of Trustee, Conseil scolaire Viamonde": ("viamonde", "trustee"),
    "Office of Trustee, Conseil scolaire catholique MonAvenir": ("monavenir", "trustee"),
}
_WARD = re.compile(r"^Ward (\d+)\b")
_VOTE_ROW = re.compile(r"^(\S.*?\S)\s{2,}(\d+)(?:\s+(X))?$")
_ACCLAIMED_ROW = re.compile(r"^(\S.*?\S)\s{2,}Acclaimed$")
_PAGE_NUMBER = re.compile(r"^\d+$")

FIELDS = [
    "board_id",
    "office_type",
    "official_district_id",
    "candidate_name",
    "votes",
    "marked_elected",
    "acclaimed",
    "page",
    "source_url",
]


def transcribe(text: str) -> list[dict[str, object]]:
    """Parse ``pdftotext -layout`` output into one row per printed Candidacy."""

    rows: list[dict[str, object]] = []
    office: tuple[str, str] | None = None
    district: str | None = None
    page = 1
    for raw in text.split("\n"):
        if "\f" in raw:
            page += raw.count("\f")
        line = raw.replace("\f", "").strip()
        if not line or line.startswith("Candidate Name") or _PAGE_NUMBER.fullmatch(line):
            continue
        if line in _OFFICES:
            office = _OFFICES[line]
            district = "city" if office[1] == "mayor" else None
            continue
        if office is None:
            continue  # the declaration's cover page
        ward = _WARD.match(line)
        if ward:
            number = int(ward.group(1))
            district = f"ward-{number}" if office[1] == "councillor" else str(number)
            continue
        if district is None:
            raise ValueError(f"candidate line before any ward on page {page}: {line!r}")
        if match := _ACCLAIMED_ROW.match(line):
            name, votes, elected, acclaimed = match.group(1), "", True, True
        elif match := _VOTE_ROW.match(line):
            name, votes = match.group(1), int(match.group(2))
            elected, acclaimed = match.group(3) == "X", False
        else:
            raise ValueError(f"unparsed declaration line on page {page}: {line!r}")
        rows.append(
            {
                "board_id": office[0],
                "office_type": office[1],
                "official_district_id": district,
                "candidate_name": name,
                "votes": votes,
                "marked_elected": "true" if elected else "false",
                "acclaimed": "true" if acclaimed else "false",
                "page": page,
                "source_url": DECLARATION_URL,
            }
        )
    return rows


def main() -> None:
    digest = hashlib.sha256(PDF.read_bytes()).hexdigest()
    if digest != PDF_SHA256:
        raise SystemExit(f"{PDF} does not match the pinned declaration ({digest})")
    text = subprocess.run(
        ["pdftotext", "-layout", str(PDF), "-"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    rows = transcribe(text)
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {OUTPUT}")


if __name__ == "__main__":
    main()
