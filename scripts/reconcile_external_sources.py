"""Compare the release's results with two independent datasets, Contest by Contest.

- Sevi, "Who Runs? Canadian Federal and Ontario Provincial Candidates since 1867", Harvard
  Dataverse, doi:10.7910/DVN/ABFNSQ, version 9 (CC0): the federal file
  federal-candidates-2023-12-11rev.csv (datafile 10100743) and the Ontario file
  "ontario candidates.csv" (datafile 4311750). The release's Toronto ridings are compared from
  1993 to the last election in each file.
- Merrill et al., Canadian Municipal Elections Database, Borealis, doi:10.5683/SP2/4MZJPQ,
  version 6 (CC0): elec.dta (datafile 463496), the Toronto rows from 1994: the former City of
  Toronto's mayor, council and Metro Council races in 1994, then the amalgamated City's mayor and
  council.

Each file is the repository's original-format download, for example
https://dataverse.harvard.edu/api/access/datafile/10100743?format=original.

Each external Contest is matched to the release's Contest at the same election and the same
riding or ward, and the Candidacies within it are paired by vote total, or by surname where the
totals differ. The script writes one row per Contest and one row per Candidacy difference.

Usage:
    python -I scripts/reconcile_external_sources.py FEDERAL_CSV ONTARIO_CSV CMED_DTA OUT_DIR
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).parents[1]
RESULTS = REPO_ROOT / "data" / "out" / "election_results.csv"
# The release keeps one District name within a Boundary regime, so federal district 35008 is
# Broadview—Greenwood in 2000; Elections Canada ran that election under its new name.
FEDERAL_DISTRICT_ALIASES = {("2000-11-27", "broadviewgreenwood"): "torontodanforth"}
# CMED numbers the eight 1994 Metro wards in the former City of Toronto; the release names them.
# Each number is mapped to the Metro ward that its elected candidate represented.
CMED_METRO_WARDS_1994 = {
    "19": "High Park",
    "20": "Trinity Niagara",
    "21": "Davenport",
    "22": "North Toronto",
    "23": "Midtown",
    "24": "Downtown",
    "25": "Don River",
    "26": "East Toronto",
}
# In CMED's 1997 Ward 26 and 27 rows these candidates carry another candidate's total, or a
# total the City's results do not give.
CMED_1997_MISALIGNED = frozenset(
    {"Steve Ellis", "Tom Jakobek", "Sandra Bussin", "Stan Kumorek", "Paul Jewett", "Randy Leach"}
)


def _words(text: object) -> list[str]:
    folded = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z]+", " ", folded.casefold()).split()


def _key(text: object) -> str:
    return "".join(_words(text))


def _surname_key(name: object) -> str:
    words = _words(name)
    return words[-1] if words else ""


def _votes(value: object) -> int | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _release() -> pd.DataFrame:
    results = pd.read_csv(RESULTS, dtype=str, keep_default_na=False)
    results["votes_int"] = results["votes"].map(_votes)
    results["surname_key"] = results["candidate_name"].map(_surname_key)
    return results


def _sevi_federal(path: Path, first: str, last: str) -> pd.DataFrame:
    table = pd.read_csv(path, dtype=str, keep_default_na=False, encoding_errors="replace")
    table = table.loc[table["province"].eq("Ontario") & table["edate"].between(first, last)].copy()
    # Names are printed SURNAME, Given names.
    surname = table["candidate_name"].str.split(",").str[0]
    given = table["candidate_name"].str.split(",").str[1:].str.join(",")
    return pd.DataFrame(
        {
            "election_date": table["edate"],
            "district_key": table["riding"].map(_key),
            "district": table["riding"],
            "name": (given.str.strip() + " " + surname.str.strip()).str.strip(),
            "surname_key": surname.map(_surname_key),
            "votes_int": table["votes"].map(_votes),
            "elected": table["elected"].eq("Elected"),
        }
    )


def _sevi_ontario(path: Path, first: str) -> pd.DataFrame:
    table = pd.read_csv(
        path, dtype=str, keep_default_na=False, encoding="utf-8-sig", encoding_errors="replace"
    )
    table = table.loc[table["election_date"].ge(first)].copy()
    out = pd.DataFrame(
        {
            "election_date": table["election_date"],
            "district_key": table["riding"].map(_key),
            "district": table["riding"],
            "name": (table["name_first"].str.strip() + " " + table["name_last"].str.strip()),
            "surname_key": table["name_last"].map(_surname_key),
            "votes_int": table["ballots"].map(_votes),
        }
    )
    # The Ontario file marks no winner; the top vote total in each riding won.
    top = out.groupby(["election_date", "district_key"])["votes_int"].transform("max")
    out["elected"] = out["votes_int"].eq(top)
    return out


def _cmed(path: Path) -> pd.DataFrame:
    table = pd.read_stata(path)
    table = table.loc[table["municipality"].astype(str).eq("Toronto")].copy()
    position = table["position"].astype(str).str.casefold()
    office = position.map(lambda value: "mayor" if value == "mayor" else "councillor")
    metro = position.eq("metro council")
    ward_number = table["ward"].astype(str).str.extract(r"(\d+)")[0].fillna("")
    ward = ward_number.where(~metro, ward_number.map(CMED_METRO_WARDS_1994).fillna(""))
    return pd.DataFrame(
        {
            "election_year": table["election_year"].astype(int).astype(str),
            "body": metro.map({True: "metro", False: "council"}),
            "office_type": office,
            "ward_number": ward.where(office.eq("councillor"), ""),
            "district": table["ward"].astype(str),
            "name": (
                table["first_name"].astype(str).str.strip()
                + " "
                + table["last_name"].astype(str).str.strip()
            ),
            "surname_key": table["last_name"].map(_surname_key),
            "votes_int": table["votes_received"].map(_votes),
            "elected": table["elected"].astype(float).eq(1.0),
        }
    )


def _pair(release: pd.DataFrame, external: pd.DataFrame) -> list[dict[str, object]]:
    """Pair two Contests' Candidacies by votes, then by surname; report every difference."""

    notes: list[dict[str, object]] = []
    left = release.copy()
    right = external.copy()
    used_left: set[int] = set()
    used_right: set[int] = set()
    for index, row in right.iterrows():
        both_null = left["votes_int"].isna() & pd.isna(row["votes_int"])
        same = left.loc[
            (left["votes_int"].eq(row["votes_int"]) | both_null)
            & left["surname_key"].eq(row["surname_key"])
            & ~left.index.isin(used_left)
        ]
        if len(same):
            used_left.add(same.index[0])
            used_right.add(index)
    for index, row in right.loc[~right.index.isin(used_right)].iterrows():
        by_votes = left.loc[left["votes_int"].eq(row["votes_int"]) & ~left.index.isin(used_left)]
        by_name = left.loc[left["surname_key"].eq(row["surname_key"]) & ~left.index.isin(used_left)]
        if len(by_votes) == 1 and row["votes_int"] is not None:
            match = by_votes.iloc[0]
            used_left.add(by_votes.index[0])
            notes.append(
                {
                    "difference": "name",
                    "release_name": match["candidate_name"],
                    "release_name_raw": match["candidate_name_raw"],
                    "release_votes": match["votes_int"],
                    "external_name": row["name"],
                    "external_votes": row["votes_int"],
                }
            )
        elif len(by_name) == 1:
            match = by_name.iloc[0]
            used_left.add(by_name.index[0])
            notes.append(
                {
                    "difference": "votes",
                    "release_name": match["candidate_name"],
                    "release_name_raw": match["candidate_name_raw"],
                    "release_votes": match["votes_int"],
                    "external_name": row["name"],
                    "external_votes": row["votes_int"],
                }
            )
        else:
            notes.append(
                {
                    "difference": "missing_from_release",
                    "release_name": "",
                    "release_name_raw": "",
                    "release_votes": None,
                    "external_name": row["name"],
                    "external_votes": row["votes_int"],
                }
            )
    for _, match in left.loc[~left.index.isin(used_left)].iterrows():
        notes.append(
            {
                "difference": "missing_from_external",
                "release_name": match["candidate_name"],
                "release_name_raw": match["candidate_name_raw"],
                "release_votes": match["votes_int"],
                "external_name": "",
                "external_votes": None,
            }
        )
    return notes


def _winner_note(release: pd.DataFrame, external: pd.DataFrame) -> list[dict[str, object]]:
    ours = set(release.loc[release["elected"].eq("True"), "surname_key"])
    theirs = set(external.loc[external["elected"], "surname_key"])
    if ours == theirs or not theirs:
        return []
    return [
        {
            "difference": "winner",
            "release_name": "; ".join(release.loc[release["elected"].eq("True"), "candidate_name"]),
            "release_name_raw": "",
            "release_votes": None,
            "external_name": "; ".join(external.loc[external["elected"], "name"]),
            "external_votes": None,
        }
    ]


def _finding(row: pd.Series) -> str:
    """Why a difference arises, from the checks recorded in the reconciliation report."""

    source, difference = row["source"], row["difference"]
    release_votes, external_votes = row["release_votes"], row["external_votes"]
    if source == "cmed" and row["external_name"] == "Cynthia Lai":
        return (
            "Cynthia Lai died on 21 October 2022; the City did not count votes cast for her and "
            "its results omit her"
        )
    if (
        source == "cmed"
        and row["election_date"] == "1997-11-10"
        and {row["release_name"], row["external_name"]} & CMED_1997_MISALIGNED
    ):
        return (
            "CMED's rows for 1997 Wards 26 and 27 pair names with the wrong totals; the City's "
            "results give the release's figures"
        )
    if difference == "winner":
        return "Same winners, printed differently"
    if difference == "name":
        authority = {"cmed": "the City's", "sevi_federal": "Elections Canada's"}.get(
            source, "the authority's"
        )
        external, ours, printed = (
            _words(row[column]) for column in ("external_name", "release_name", "release_name_raw")
        )
        if "".join(external) == "".join(ours):
            return "Same name, spaced or capitalized differently"
        if "".join(external) == "".join(printed):
            return (
                "Same printed name; the release's candidate_name puts the given name first and "
                "candidate_name_raw keeps the print"
            )
        if sorted(external) == sorted(ours):
            return f"Same name in the other order; the release keeps {authority} printed name"
        return f"Name printed differently; the release keeps {authority} printed name"
    if difference == "not_in_external":
        return "The external file has no rows for this election"
    if (
        source == "cmed"
        and pd.isna(release_votes)
        and not pd.isna(external_votes)
        and external_votes == 0
    ):
        return "Acclamation: the release keeps votes null, CMED records 0"
    if (
        source == "cmed"
        and row["election_date"] == "1994-11-14"
        and row["district_name"] == "Ward 3"
    ):
        return (
            "The release carries the final judicial recount (Globe and Mail, 16 December 1995); "
            "CMED has the election-night count"
        )
    if source == "cmed":
        return "The City's results give the release's figure; CMED's differs"
    if source == "sevi_federal":
        return (
            "The release's total is Elections Canada's in its Official Voting Results (table 12); "
            "Sevi's differs"
        )
    return (
        "The release follows Elections Ontario's official results, whose candidate totals sum to "
        "its count of valid ballots; Sevi's differs"
    )


def _compare(
    label: str,
    release: pd.DataFrame,
    external: pd.DataFrame,
    release_key: list[str],
    external_key: list[str],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    contests: list[dict[str, object]] = []
    differences: list[dict[str, object]] = []
    external_groups = {key: group for key, group in external.groupby(external_key)}
    seen: set[tuple[object, ...]] = set()
    for key, ours in release.groupby(release_key):
        theirs = external_groups.get(key)
        record = {
            "source": label,
            "contest_id": ours["contest_id"].iloc[0],
            "election_date": ours["election_date"].iloc[0],
            "district_name": ours["district_name"].iloc[0],
            "release_candidacies": len(ours),
        }
        if theirs is None:
            contests.append({**record, "external_candidacies": 0, "status": "not_in_external"})
            continue
        seen.add(key)
        notes = _pair(ours, theirs) + _winner_note(ours, theirs)
        contests.append(
            {
                **record,
                "external_candidacies": len(theirs),
                "status": "agrees" if not notes else "differs",
            }
        )
        for note in notes:
            differences.append({"source": label, **record, **note})
    for key, theirs in external_groups.items():
        if key not in seen:
            contests.append(
                {
                    "source": label,
                    "contest_id": "",
                    "election_date": str(key[0]),
                    "district_name": str(theirs["district"].iloc[0]),
                    "release_candidacies": 0,
                    "external_candidacies": len(theirs),
                    "status": "not_in_release",
                }
            )
    return contests, differences


def main(argv: list[str]) -> None:
    if len(argv) != 5:
        raise SystemExit(__doc__)
    federal_path, ontario_path, cmed_path, out_dir = (Path(value) for value in argv[1:])
    out_dir.mkdir(parents=True, exist_ok=True)
    results = _release()
    contests: list[dict[str, object]] = []
    differences: list[dict[str, object]] = []

    federal = _sevi_federal(federal_path, "1993-10-25", "2021-09-20")
    ours = results.loc[results["office_type"].eq("mp")].copy()
    ours = ours.loc[ours["election_date"].le(federal["election_date"].max())]
    ours["district_key"] = [
        FEDERAL_DISTRICT_ALIASES.get((day, _key(name)), _key(name))
        for day, name in zip(ours["election_date"], ours["district_name"], strict=True)
    ]
    toronto = set(zip(ours["election_date"], ours["district_key"], strict=True))
    federal = federal.loc[
        [
            (day, key) in toronto
            for day, key in zip(federal["election_date"], federal["district_key"], strict=True)
        ]
    ]
    found = _compare(
        "sevi_federal",
        ours,
        federal,
        ["election_date", "district_key"],
        ["election_date", "district_key"],
    )
    contests += found[0]
    differences += found[1]

    ontario = _sevi_ontario(ontario_path, "1995-06-08")
    ours = results.loc[results["office_type"].eq("mpp")].copy()
    ours = ours.loc[ours["election_date"].le(ontario["election_date"].max())]
    ours["district_key"] = ours["district_name"].map(_key)
    toronto = set(zip(ours["election_date"], ours["district_key"], strict=True))
    ontario = ontario.loc[
        [
            (day, key) in toronto
            for day, key in zip(ontario["election_date"], ontario["district_key"], strict=True)
        ]
    ]
    found = _compare(
        "sevi_ontario",
        ours,
        ontario,
        ["election_date", "district_key"],
        ["election_date", "district_key"],
    )
    contests += found[0]
    differences += found[1]

    # CMED's 1994 Toronto rows are the former City of Toronto's mayor and council and the eight
    # Metro wards within the former City.
    cmed = _cmed(cmed_path)
    cmed = cmed.loc[cmed["election_year"].astype(int).ge(1994)]
    year_1994 = results["election_year"].eq("1994")
    metro = (
        results["represented_body"].eq("metro_toronto_council")
        & year_1994
        & results["district_name"].isin(set(CMED_METRO_WARDS_1994.values()))
    )
    body = (
        results["represented_body"].eq("toronto_city_council")
        | (results["represented_body"].eq("former_toronto_city_council") & year_1994)
        | metro
    )
    ours = results.loc[
        body
        & results["election_type"].eq("general")
        & results["election_year"].isin(set(cmed["election_year"]))
    ].copy()
    ours["body"] = metro.loc[ours.index].map({True: "metro", False: "council"})
    ward_number = ours["district_name"].str.extract(r"(\d+)")[0].fillna("")
    ours["ward_number"] = ward_number.where(
        ours["body"].eq("council"), ours["district_name"]
    ).where(ours["office_type"].eq("councillor"), "")
    key = ["election_year", "body", "office_type", "ward_number"]
    found = _compare("cmed", ours, cmed, key, key)
    contests += found[0]
    differences += found[1]

    contest_table = pd.DataFrame(contests)
    difference_table = pd.DataFrame(differences)
    for column in ("release_votes", "external_votes"):
        difference_table[column] = difference_table[column].astype("Int64")
    difference_table["finding"] = difference_table.apply(_finding, axis=1)
    for status in ("not_in_external", "not_in_release"):
        missing = contest_table.loc[contest_table["status"].eq(status)]
        for _, row in missing.iterrows():
            difference_table.loc[len(difference_table)] = {
                **{column: "" for column in difference_table.columns},
                **{column: row[column] for column in contest_table.columns if column != "status"},
                "difference": status,
                "finding": _finding(
                    pd.Series(
                        {
                            **row,
                            "difference": status,
                            "release_votes": None,
                            "external_votes": None,
                            "external_name": "",
                        }
                    )
                ),
            }
    contest_table.to_csv(out_dir / "contests.csv", index=False)
    difference_table.to_csv(out_dir / "differences.csv", index=False)
    print(contest_table.groupby(["source", "status"]).size().to_string())
    if not difference_table.empty:
        print(difference_table.groupby(["source", "difference"]).size().to_string())


if __name__ == "__main__":
    main(sys.argv)
