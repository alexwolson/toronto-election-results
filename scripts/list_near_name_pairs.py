"""List every near-name Person pair for the review of missed links.

The audit of Person links (``draw_link_audit_sample.py``) looks for missed links only among
Persons whose first and last names match. This script lists the complementary set: pairs of
distinct Persons whose printed names are close but do not share a first and last name. Two
printed names are close when

* they have the same last name and first names that are a common nickname pair or of which one
  begins with the other (Dan and Daniel, Mike and Michael);
* they have the same last name and the first name of one is a middle name of the other;
* they have the same first name and last names one letter apart (five letters or more); or
* they have the same words in a different order (a surname printed first, a reversed compound
  surname).

Two Persons who ran in the same election cannot be one individual, so such pairs are left out.
The list is small enough to review in full. Run from the repository root.
"""

from __future__ import annotations

import argparse
import itertools
from pathlib import Path

import pandas as pd
from draw_link_audit_sample import _normalise, describe, first_last

DEFAULT_RESULTS = Path("data/out/election_results.csv")
DEFAULT_OUTPUT = Path("docs/verification/same-name-review-2026-11-03/near_name_pairs.csv")

# Common English given-name pairs where neither name begins with the other.
NICKNAMES = [
    ("bob", "robert"),
    ("bobby", "robert"),
    ("bert", "robert"),
    ("bert", "albert"),
    ("bill", "william"),
    ("billy", "william"),
    ("will", "william"),
    ("liam", "william"),
    ("jim", "james"),
    ("jimmy", "james"),
    ("jack", "john"),
    ("johnny", "john"),
    ("mike", "michael"),
    ("mick", "michael"),
    ("joe", "joseph"),
    ("dave", "david"),
    ("andy", "andrew"),
    ("drew", "andrew"),
    ("nick", "nicholas"),
    ("nick", "nicolas"),
    ("tony", "anthony"),
    ("tony", "antonio"),
    ("dick", "richard"),
    ("rick", "richard"),
    ("ted", "edward"),
    ("ned", "edward"),
    ("ted", "theodore"),
    ("chuck", "charles"),
    ("hank", "henry"),
    ("harry", "henry"),
    ("jerry", "gerald"),
    ("gerry", "gerald"),
    ("gerry", "gerard"),
    ("larry", "lawrence"),
    ("larry", "laurence"),
    ("peggy", "margaret"),
    ("maggie", "margaret"),
    ("meg", "margaret"),
    ("liz", "elizabeth"),
    ("beth", "elizabeth"),
    ("betty", "elizabeth"),
    ("lisa", "elizabeth"),
    ("sue", "susan"),
    ("suzanne", "susan"),
    ("kathy", "katherine"),
    ("kathy", "kathleen"),
    ("cathy", "catherine"),
    ("kate", "katherine"),
    ("katie", "katherine"),
    ("sandy", "sandra"),
    ("sandy", "alexander"),
    ("alex", "alexandra"),
    ("steve", "stephen"),
    ("steve", "steven"),
    ("stephen", "steven"),
    ("wally", "walter"),
    ("jeff", "geoffrey"),
    ("peggy", "marguerite"),
    ("bea", "beatrice"),
    ("trish", "patricia"),
    ("patty", "patricia"),
    ("jenny", "jennifer"),
    ("jen", "jennifer"),
    ("becky", "rebecca"),
    ("tom", "thomas"),
    ("rocco", "rocky"),
    ("frank", "francis"),
    ("frank", "francesco"),
    ("joe", "giuseppe"),
    ("sal", "salvatore"),
    ("vince", "vincenzo"),
    ("john", "giovanni"),
    ("john", "juan"),
    ("mary", "maria"),
    ("ann", "anne"),
    ("anna", "anne"),
    ("ann", "anna"),
]
_NICK = {frozenset(pair) for pair in NICKNAMES}


def _close_first(a: str, b: str) -> bool:
    if a == b:
        return True
    if frozenset((a, b)) in _NICK:
        return True
    short, long_ = sorted((a, b), key=len)
    return len(short) >= 3 and long_.startswith(short)


def _one_apart(a: str, b: str) -> bool:
    if a == b or min(len(a), len(b)) < 5 or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    short, long_ = sorted((a, b), key=len)
    return any(long_[:i] + long_[i + 1 :] == short for i in range(len(long_)))


def close_names(a: list[str], b: list[str]) -> bool:
    """Whether two printed names, as word lists without initials, are close but not the same."""

    if len(a) < 2 or len(b) < 2 or (a[0], a[-1]) == (b[0], b[-1]):
        return False
    if a[-1] == b[-1]:
        if _close_first(a[0], b[0]):
            return True
        if a[0] in b[1:-1] or b[0] in a[1:-1]:
            return True
    if a[0] == b[0] and _one_apart(a[-1], b[-1]):
        return True
    return sorted(a) == sorted(b)


def _words(name: str) -> list[str]:
    return [token for token in _normalise(name) if len(token) > 1]


def near_name_frame(results: pd.DataFrame) -> pd.DataFrame:
    people = results.loc[results["person_id"].ne("")]
    names: dict[str, set[tuple[str, ...]]] = {}
    keys: dict[str, set[tuple[str, str]]] = {}
    events: dict[str, set[str]] = {}
    for person_id, name, event_id in zip(
        people["person_id"], people["candidate_name"], people["event_id"]
    ):
        keys.setdefault(person_id, set()).add(first_last(name))
        events.setdefault(person_id, set()).add(event_id)
        words = tuple(_words(name))
        if len(words) > 1:
            names.setdefault(person_id, set()).add(words)
    by_last: dict[str, set[str]] = {}
    by_first: dict[str, set[str]] = {}
    for person_id, variants in sorted(names.items()):
        for words in sorted(variants):
            by_last.setdefault(words[-1], set()).add(person_id)
            by_first.setdefault(words[0], set()).add(person_id)
    candidates: set[tuple[str, str]] = set()
    for bucket in itertools.chain(by_last.values(), by_first.values()):
        candidates.update(itertools.combinations(sorted(bucket), 2))
    rows = []
    for a, b in sorted(candidates):
        if keys[a] & keys[b] or events[a] & events[b]:
            continue  # a same-name pair (covered by the link audit) or two people in one election
        if any(close_names(list(x), list(y)) for x in names[a] for y in names[b]):
            rows.append((a, b))
    return pd.DataFrame(rows, columns=["person_a", "person_b"])


def list_pairs(results_path: Path, output_path: Path) -> None:
    results = pd.read_csv(results_path, dtype="string", keep_default_na=False)
    frame = near_name_frame(results)
    by_id = results.set_index("candidacy_id")
    linked = results.loc[results["person_id"].ne("")]
    rows = []
    for number, pair in enumerate(frame.itertuples(index=False), start=1):
        runs = {}
        for side, person in (("a", pair.person_a), ("b", pair.person_b)):
            own = linked.loc[linked["person_id"].eq(person)].sort_values("election_date")
            runs[side] = "; ".join(describe(by_id.loc[c]) for c in own["candidacy_id"])
        rows.append(
            {
                "pair_id": f"N{number:03d}",
                "person_a": pair.person_a,
                "runs_a": runs["a"],
                "person_b": pair.person_b,
                "runs_b": runs["b"],
            }
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output_path, index=False, lineterminator="\n")
    print(f"near-name pairs: {len(rows)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    list_pairs(args.results, args.output)


if __name__ == "__main__":
    main()
