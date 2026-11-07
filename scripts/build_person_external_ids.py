"""Build `data/reference/person_external_ids.csv`: outside identifiers for elected MPs and MPPs.

Each House of Commons Office tenure in the release is the term of a Toronto seat's winner, and its
evidence names the Parliament, the constituency as the House records it and the House's person ID.
A Wikidata item is matched to the Person when it holds "member of the House of Commons of Canada"
(Q15964890) for that constituency in that Parliament and its label contains the member's surname.
The item's Library of Parliament person ID (P6616, ParlInfo) is taken with it. A Person must match
one item, and an item one Person.

The Wikidata statements are the result, saved as CSV, of this query at https://query.wikidata.org:

    SELECT ?person ?personLabel ?parlinfo ?riding ?ridingLabel ?term ?termLabel ?start ?end WHERE {
      ?person p:P39 ?st . ?st ps:P39 wd:Q15964890 .
      OPTIONAL { ?st pq:P768 ?riding . } OPTIONAL { ?st pq:P2937 ?term . }
      OPTIONAL { ?st pq:P580 ?start . } OPTIONAL { ?st pq:P582 ?end . }
      OPTIONAL { ?person wdt:P6616 ?parlinfo . }
      FILTER(!BOUND(?start) || ?start >= "1993-01-01"^^xsd:dateTime
             || (BOUND(?end) && ?end >= "1993-01-01"^^xsd:dateTime))
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
    }

Each Ontario legislature Office tenure is likewise the term of a Toronto seat's winner, and its
evidence names the member's Legislative Assembly profile, whose slug is the Assembly's member ID.
A Wikidata item is matched to that Person when its Ontario MPP ID (P3054) is the same slug. A
Person matched to items by both routes must be matched to the same item. The MPP statements are
the result, saved as CSV, of this query:

    SELECT ?person ?personLabel ?ola WHERE {
      ?person wdt:P3054 ?ola .
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
    }

Usage:
    python -I scripts/build_person_external_ids.py WIKIDATA_MP_CSV WIKIDATA_MPP_CSV RETRIEVED_ON
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).parents[1]
TENURES = REPO_ROOT / "data" / "out" / "office_tenures.csv"
OUTPUT = REPO_ROOT / "data" / "reference" / "person_external_ids.csv"
HOUSE_EXPORT = "https://www.ourcommons.ca/Members/en/search/xml?parliament={parliament}"
PARLINFO = "https://lop.parl.ca/sites/ParlInfo/default/en_CA/People/Profile?personId={value}"
WIKIDATA = "https://www.wikidata.org/wiki/{value}"
OLA_PROFILE = "https://www.ola.org/en/members/all/{value}"


def _fold(text: object) -> str:
    folded = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z]+", "", folded.casefold())


def _ordinal(number: int) -> str:
    suffix = (
        "th" if 10 <= number % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    )
    return f"{number}{suffix}"


def _house_terms() -> pd.DataFrame:
    tenures = pd.read_csv(TENURES, dtype=str, keep_default_na=False)
    tenures = tenures.loc[tenures["represented_body"].eq("canada_house_of_commons")]
    rows = []
    for tenure in tenures.itertuples(index=False):
        member = json.loads(tenure.source_detail)["house_member"]
        rows.append(
            {
                "person_id": tenure.person_id,
                "parliament": int(member["parliament"]),
                "constituency": member["constituency"],
                "name": member["name"],
                "house_person_id": member.get("house_person_id") or "",
            }
        )
    return pd.DataFrame(rows)


def _wikidata(path: Path) -> pd.DataFrame:
    statements = pd.read_csv(path, dtype=str, keep_default_na=False)
    statements["qid"] = statements["person"].str.rsplit("/", n=1).str[-1]
    parliament = statements["termLabel"].str.extract(r"^(\d+)(?:st|nd|rd|th) Canadian Parliament$")
    statements["parliament"] = pd.to_numeric(parliament[0], errors="coerce")
    statements["riding_key"] = statements["ridingLabel"].map(_fold)
    return statements.loc[statements["parliament"].notna()]


def _ontario_members() -> pd.DataFrame:
    tenures = pd.read_csv(TENURES, dtype=str, keep_default_na=False)
    tenures = tenures.loc[tenures["represented_body"].eq("ontario_legislative_assembly")]
    rows = []
    for tenure in tenures.itertuples(index=False):
        member = json.loads(tenure.source_detail).get("ontario_member")
        if member is None:
            continue
        rows.append(
            {
                "person_id": tenure.person_id,
                "ola_member_id": member["ola_member_id"],
                "name": member["name"],
            }
        )
    return pd.DataFrame(rows).drop_duplicates()


def build(wikidata_path: Path, wikidata_mpp_path: Path, retrieved_on: str) -> pd.DataFrame:
    terms = _house_terms()
    statements = _wikidata(wikidata_path)
    matches: dict[str, dict[str, str]] = {}
    for term in terms.itertuples(index=False):
        surname = _fold(term.name.split()[-1])
        found = statements.loc[
            statements["riding_key"].eq(_fold(term.constituency))
            & statements["parliament"].eq(term.parliament)
            & statements["personLabel"].map(_fold).str.contains(surname, regex=False)
        ]
        qids = set(found["qid"])
        if len(qids) > 1:
            raise ValueError(f"{term.name} matches several Wikidata items: {sorted(qids)}")
        record = matches.setdefault(term.person_id, {})
        if term.house_person_id:
            if record.get("house_of_commons", term.house_person_id) != term.house_person_id:
                raise ValueError(f"{term.name} has two House person IDs")
            record["house_of_commons"] = term.house_person_id
            record.setdefault("house_parliament", str(term.parliament))
        if qids:
            qid = qids.pop()
            if record.get("wikidata", qid) != qid:
                raise ValueError(f"{term.name} matches two Wikidata items")
            record["wikidata"] = qid
            record.setdefault(
                "wikidata_basis",
                f"Wikidata item holding member of the House of Commons of Canada for "
                f"{term.constituency} in the {_ordinal(term.parliament)} Parliament",
            )
            parlinfo = set(found["parlinfo"]) - {""}
            if len(parlinfo) > 1:
                raise ValueError(f"{term.name} has several ParlInfo IDs: {sorted(parlinfo)}")
            if parlinfo:
                record["parlinfo"] = parlinfo.pop()
    mpps = _ontario_members()
    if mpps["person_id"].duplicated().any():
        raise ValueError("a Person has two Legislative Assembly member IDs")
    if mpps["ola_member_id"].duplicated().any():
        raise ValueError("a Legislative Assembly member ID belongs to two Persons")
    by_slug = pd.read_csv(wikidata_mpp_path, dtype=str, keep_default_na=False)
    by_slug["qid"] = by_slug["person"].str.rsplit("/", n=1).str[-1]
    by_slug = by_slug.groupby("ola")["qid"].agg(lambda qids: sorted(set(qids)))
    for member in mpps.itertuples(index=False):
        record = matches.setdefault(member.person_id, {})
        record["ontario_legislature"] = member.ola_member_id
        qids = by_slug.get(member.ola_member_id, [])
        if len(qids) > 1:
            raise ValueError(f"{member.name} matches several Wikidata items: {qids}")
        if qids:
            if record.get("wikidata", qids[0]) != qids[0]:
                raise ValueError(f"{member.name} matches different items as an MP and an MPP")
            record.setdefault("wikidata", qids[0])
            record.setdefault(
                "wikidata_basis",
                f"Wikidata item whose Ontario MPP ID (P3054) is {member.ola_member_id}",
            )
    rows = []
    for person_id, record in sorted(matches.items()):
        if "ontario_legislature" in record:
            rows.append(
                {
                    "person_id": person_id,
                    "scheme": "ontario_legislature",
                    "external_id": record["ontario_legislature"],
                    "basis": "Legislative Assembly member profile, as the release's tenures cite",
                    "source_url": OLA_PROFILE.format(value=record["ontario_legislature"]),
                    "retrieved_on": retrieved_on,
                }
            )
        if "house_of_commons" in record:
            rows.append(
                {
                    "person_id": person_id,
                    "scheme": "house_of_commons",
                    "external_id": record["house_of_commons"],
                    "basis": "House of Commons member export, as the release's House tenures cite",
                    "source_url": HOUSE_EXPORT.format(parliament=record["house_parliament"]),
                    "retrieved_on": retrieved_on,
                }
            )
        if "wikidata" in record:
            rows.append(
                {
                    "person_id": person_id,
                    "scheme": "wikidata",
                    "external_id": record["wikidata"],
                    "basis": record["wikidata_basis"],
                    "source_url": WIKIDATA.format(value=record["wikidata"]),
                    "retrieved_on": retrieved_on,
                }
            )
        if "parlinfo" in record:
            rows.append(
                {
                    "person_id": person_id,
                    "scheme": "parlinfo",
                    "external_id": record["parlinfo"],
                    "basis": "Library of Parliament person ID (P6616) of the matched Wikidata item",
                    "source_url": PARLINFO.format(value=record["parlinfo"]),
                    "retrieved_on": retrieved_on,
                }
            )
    out = pd.DataFrame(rows)
    for scheme, group in out.groupby("scheme"):
        if group["external_id"].duplicated().any():
            duplicated = group.loc[group["external_id"].duplicated(keep=False), "external_id"]
            raise ValueError(f"{scheme} IDs shared by two Persons: {sorted(set(duplicated))}")
    elected = pd.concat([terms[["person_id", "name"]], mpps[["person_id", "name"]]])
    missing = sorted(
        set(elected["person_id"]) - set(out.loc[out["scheme"].eq("wikidata"), "person_id"])
    )
    names = elected.drop_duplicates("person_id").set_index("person_id")["name"]
    print(f"{elected['person_id'].nunique()} Persons with House or Assembly terms; no Wikidata:")
    for person_id in missing:
        print(f"  {names[person_id]} ({person_id})")
    return out


def main(argv: list[str]) -> None:
    if len(argv) != 4:
        raise SystemExit(__doc__)
    out = build(Path(argv[1]), Path(argv[2]), argv[3])
    OUTPUT.write_text(out.to_csv(index=False, lineterminator="\n"), encoding="utf-8")
    print(out.groupby("scheme").size().to_string())


if __name__ == "__main__":
    main(sys.argv)
