"""Authoritative-winners cross-check against the council composition."""

import pandas as pd

from toronto_election_results.crosscheck_winners import crosscheck_winners, unexplained_winners


def _composition(year, names):
    return pd.DataFrame(
        {
            "election_year": year,
            "member_name": names,
            "match_key": [" ".join(sorted(n.lower().split())) for n in names],
            "incumbent_source": "test",
            "confidence": 0.9,
        }
    )


def _winner(year, ward, name):
    return {
        "election_year": year,
        "office": "councillor",
        "ward_number": ward,
        "candidate_name": name,
        "elected": True,
    }


def test_winner_present_in_next_council_is_not_flagged():
    df = pd.DataFrame([_winner(2003, 1, "Suzan Hall")])
    comp = _composition(2006, ["Suzan Hall", "David Miller"])
    assert crosscheck_winners(df, comp) == []


def test_name_variant_is_suppressed_by_fuzzy_match():
    df = pd.DataFrame([_winner(2003, 25, "Clifford Jenkins")])
    comp = _composition(2006, ["Cliff Jenkins"])
    assert crosscheck_winners(df, comp) == []


def test_missing_winner_is_flagged():
    df = pd.DataFrame([_winner(2003, 99, "Departed Person")])
    comp = _composition(2006, ["Someone Else"])
    flagged = crosscheck_winners(df, comp)
    assert (2003, 99, "Departed Person") in flagged


def test_unexplained_excludes_known_departures():
    # ward 20 2003 (Olivia Chow) is a KNOWN_ACCOUNTED departure -> not unexplained
    df = pd.DataFrame([_winner(2003, 20, "Olivia Chow")])
    comp = _composition(2006, ["Martin Silva"])
    assert crosscheck_winners(df, comp)  # raw check flags it
    assert unexplained_winners(df, comp) == []  # but it is accounted for
