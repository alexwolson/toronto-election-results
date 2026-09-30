"""Read an Elections Canada validated contest before poll-level exports are available."""

import re
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

import pandas as pd


class _ResultTable(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self.text: list[str] = []
        self.row: list[str] | None = None
        self.cell: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag in {"td", "th"} and self.row is not None:
            self.cell = []

    def handle_data(self, data):
        self.text.append(data)
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def parse_validated_contest(
    path: Path, *, district_id: str, district_name: str, election_date: date
) -> pd.DataFrame:
    """Require validation, complete totals, and a unique winner; never use live counts."""
    parser = _ResultTable()
    parser.feed(path.read_text(encoding="utf-8-sig"))
    text = " ".join(" ".join(parser.text).split())
    date_label = f"{election_date:%B} {election_date.day}, {election_date.year}"
    if (
        "Results Validated by the Returning Officer" not in text
        or f"Voting Results for the electoral district of {district_name}" not in text
        or date_label not in text
    ):
        raise ValueError("federal result must be validated and match the event and district")
    records = []
    totals = {}
    in_results = False
    for row in parser.rows:
        if row[:3] == ["Party", "Candidate", "Votes"]:
            if in_results:
                raise ValueError("multiple federal candidate result tables")
            in_results = True
            continue
        if not in_results or len(row) != 4:
            continue
        votes = int(row[2].replace(",", ""))
        if not row[1]:
            totals[row[0]] = votes
            continue
        records.append(
            {
                "official_district_id": district_id,
                "district_name": district_name,
                "candidate_name_raw": row[1],
                "party_name_raw": row[0],
                "affiliation_status": "party",
                "votes": votes,
                "incumbent_reported": pd.NA,
            }
        )
    valid = totals.get("Total number of valid votes:")
    ballots = totals.get("Total number of votes:")
    rejected = totals.get("Rejected ballots:")
    if not records or valid != sum(row["votes"] for row in records):
        raise ValueError("validated federal candidate votes must reconcile with the valid total")
    if rejected is None or ballots is None or ballots != valid + rejected:
        raise ValueError("validated federal ballot totals must reconcile")
    electors = re.search(r"Number of electors on list:\s*([\d,]+)", text)
    if electors is None:
        raise ValueError("validated federal result is missing the elector count")
    result = pd.DataFrame(records)
    if result["candidate_name_raw"].duplicated().any():
        raise ValueError("validated federal candidate names must be unique")
    winners = result["votes"].eq(result["votes"].max())
    if winners.sum() != 1:
        raise ValueError("validated federal result must have one unique vote winner")
    result["elected"] = winners
    result["eligible_electors"] = int(electors[1].replace(",", ""))
    result["ballots_cast"] = ballots
    return result
