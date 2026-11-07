"""Write the Ontario legislature member terms from the Legislative Assembly's member profiles.

`scripts/ola_members.js`, run in a browser on ola.org, saves every member of the 35th to the
current Parliament with the riding terms on their profile. This script turns that file into
`data/reference/ontario_legislature_members.csv`, one row per riding term from the 36th
Parliament on: the Parliament, the member's profile slug, their names as the Assembly lists them
(without "Hon."), the riding, their party on the term's first day, and the term's dates. It
fails if a term lacks a start or a Parliament, ends before it starts, or falls in a Parliament
whose member list does not name the member.

Usage:
    python -I scripts/build_ontario_members.py OLA_MEMBERS_JSON
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).parents[1]
OUTPUT = REPO_ROOT / "data" / "reference" / "ontario_legislature_members.csv"
PROFILE = "https://www.ola.org/en/members/all/"
# The 36th Parliament began with the 1995 election, the first Ontario election in the release.
# Terms from 1990 would have no winner in the release to tie them to a Person.
FIRST_PARLIAMENT = 36
COLUMNS = [
    "parliament",
    "ola_member_id",
    "first_name",
    "last_name",
    "riding",
    "party",
    "from_date",
    "to_date",
    "source",
]


def _names(list_name: str) -> tuple[str, str]:
    last, _, first = list_name.partition(",")
    first = first.strip().removeprefix("Hon.").strip()
    return first, last.strip()


def _party(parties: list[dict[str, str]], day: str) -> str:
    """The party held on the term's first day, or else the first one the member joined after it.

    A by-election winner's affiliation can begin some days after polling day, once sworn in.
    """

    held = [p["party"] for p in parties if p["start"] <= day and (not p["end"] or day <= p["end"])]
    if len(held) == 1:
        return held[0]
    later = sorted((p["start"], p["party"]) for p in parties if p["start"] > day)
    return later[0][1] if not held and later else ""


def build(path: Path) -> pd.DataFrame:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for slug, member in sorted(data["members"].items()):
        listed = {int(parliament) for parliament, _ in member["parliaments"]}
        first, last = _names(member["list_name"])
        for term in member["ridings"]:
            number = re.match(r"(\d+)", term["parliament"])
            if not number or not term["start"] or not term["riding"]:
                raise SystemExit(f"{slug}: a riding term lacks its Parliament, start or riding")
            parliament = int(number.group(1))
            if parliament < FIRST_PARLIAMENT:
                continue
            if parliament not in listed:
                raise SystemExit(f"{slug}: the {parliament} Parliament's list does not name them")
            if term["end"] and term["end"] < term["start"]:
                raise SystemExit(f"{slug}: a term ends before it starts")
            rows.append(
                {
                    "parliament": parliament,
                    "ola_member_id": slug,
                    "first_name": first,
                    "last_name": last,
                    "riding": term["riding"],
                    "party": _party(member["parties"], term["start"]),
                    "from_date": term["start"],
                    "to_date": term["end"],
                    "source": PROFILE + slug,
                }
            )
    table = pd.DataFrame(rows, columns=COLUMNS)
    table = table.sort_values(["parliament", "last_name", "first_name", "from_date"], kind="stable")
    for parliament in range(FIRST_PARLIAMENT, 45):
        named = {
            slug
            for slug, m in data["members"].items()
            if any(int(p) == parliament for p, _ in m["parliaments"])
        }
        termed = set(table.loc[table["parliament"].eq(parliament), "ola_member_id"])
        if named != termed:
            missing = sorted(named ^ termed)
            raise SystemExit(f"the {parliament} Parliament's list and terms differ: {missing[:3]}")
    return table


def main(argv: list[str]) -> None:
    if len(argv) != 2:
        raise SystemExit(__doc__)
    table = build(Path(argv[1]))
    table.to_csv(OUTPUT, index=False, lineterminator="\n")
    print(f"wrote {len(table)} terms of {table['ola_member_id'].nunique()} members")


if __name__ == "__main__":
    main(sys.argv)
